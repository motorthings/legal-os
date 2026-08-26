"""Build the client-facing report for a completed run.

Reuses report.build_report by constructing the `experiments` dict the report expects:
  - the Monte Carlo band (mean / stdev / CI95 over the run's completed seeds),
  - firm-specific sensitivity bands (swept over the run's own governing coefficients),
then injecting it into the primary run's folder. `optimize.set_base_firm` must already be
called (by the runner) so the sensitivity sweep runs the FIRM's numbers.
"""
import asyncio
import math
import statistics
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.config import settings
from simulation.report import render_report, render_decision_onepager, load_meta, load_metrics
from simulation.optimize import LEVERS, build_overrides
from simulation.run_config import build_firm
from simulation.src.models.elasticities import DEFAULT_ELASTICITIES, default_profile
from simulation.src.orchestrator import Orchestrator, SimulationConfig

_COLLECT = ("ppp", "matter_profit_margin", "rpl", "realization_rate", "associate_attrition")

# The coefficient whose range most drives each lever's PPP effect (mirrors sensitivity.py).
_GOVERNING = {
    "pricing": "margin_ai_afa_gain",
    "seams": "margin_redline_penalty",
    "comp": "adoption_comp_gain",
    "leverage": "utilization_ai_cut",
}
LEVER_NOTES = {
    "pricing": "AFA pricing",
    "seams": "workflow standardization",
    "comp": "partner comp incentives",
    "leverage": "staffing leverage",
}
_SENS_SEEDS = 2  # band needs a range, not a CI — keep the sweep cheap; 2 seeds cuts 33% of the sims
_SENS_OUT = Path(tempfile.gettempdir()) / "law-firm-sim-sens"  # throwaway artifacts, not repo clutter


def _build_meta(rc: dict, cfg, model_variance=None) -> dict:
    """Rebuild the report's firm context from the PERSISTED config snapshot (not the ephemeral
    run disk). Fly's disk is wiped on deploy/restart, so meta.json can vanish mid-run and leave
    the report with no firm name, no horizon, and no signature. This reconstructs those from the
    stored config so a report never degrades to '? quarters'."""
    run = rc.get("run") or {}
    firm = build_firm(rc.get("firm") or {})
    return {
        # The run's own `name` is a label for the run, not the firm — it must never leak into the
        # report as the firm name. Firm name comes only from an explicit firm_name, else the
        # archetype reference firm.
        "firm_name": rc.get("firm_name") or "Aldrich & Vale LLP",
        "sprints": cfg.sprints or run.get("sprints"),
        "matters_per_sprint": cfg.matters_per_sprint or run.get("matters_per_sprint"),
        "provider": cfg.llm_provider,
        "llm_model": cfg.llm_model,
        "legal_tool": cfg.legal_tool,
        "firm_signature": asdict(firm) if firm else None,
        "calibrated_elasticities": sorted((cfg.elasticities or default_profile()).calibrated),
        "model_variance": model_variance,
    }


async def _ppp_async(pulled, seeds, sprints: int, matters: int, profile,
                     provider: str = "mock", model=None) -> float:
    """Mean final PPP for a lever set under a given elasticity profile. Mirrors
    sensitivity._ppp but AWAITS the orchestrator (that one uses asyncio.run, which
    cannot be called from inside the running runner loop). provider/model match the run's
    model so the sensitivity bands reflect the same (mock or real) model as the search."""
    import contextlib
    import io
    overrides = build_overrides(pulled)
    overrides["elasticities"] = profile
    vals = []
    for seed in seeds:
        cfg = SimulationConfig(sprints=sprints, matters_per_sprint=matters,
                               llm_provider=provider, llm_model=model, seed=seed,
                               output_dir=str(_SENS_OUT), run_id="SENS", **overrides)
        o = Orchestrator(cfg)
        o.initialize()
        with contextlib.redirect_stdout(io.StringIO()):
            r = await o.run()
        h = r.company.metric_history.get("ppp")
        vals.append(h.values[-1].value if h and h.values else 0.0)
    return statistics.mean(vals)


def _mc_band(mc: dict) -> dict:
    out = {}
    for m in _COLLECT:
        vals = mc.get(m) or []
        out[m] = {
            "mean": statistics.mean(vals) if vals else 0.0,
            "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "count": len(vals),
        }
    return out


async def _sensitivity_bands(cfg, seeds, sprints: int, matters: int, progress=None) -> dict:
    base_profile = cfg.elasticities or default_profile()
    provider = cfg.llm_provider
    model = cfg.llm_model
    # The "base" point sets each coefficient to its default, so it's the SAME baseline for
    # every lever. Computing it once (not once per lever) saves 3 full simulations.
    base_base = await _ppp_async(set(), seeds, sprints, matters, base_profile,
                                 provider=provider, model=model)

    async def one(lever: str, cid: str):
        if progress:
            progress(f"testing how {LEVER_NOTES.get(lever, lever)} moves profit — low, base, high")
        coef = DEFAULT_ELASTICITIES[cid]
        deltas = {}
        for where in ("low", "base", "high"):
            prof = base_profile.with_point(cid, where)
            base = base_base if where == "base" else await _ppp_async(
                set(), seeds, sprints, matters, prof, provider=provider, model=model)
            lever_ppp = await _ppp_async({lever}, seeds, sprints, matters, prof,
                                         provider=provider, model=model)
            deltas[where] = lever_ppp - base
        lo, hi = min(deltas.values()), max(deltas.values())
        return lever, {
            "coefficient": cid, "coefficient_name": coef.name, "source": coef.source,
            # The intake question that pins this coefficient down. The report surfaces it
            # for the widest band, so "calibrate the model" becomes one answerable question.
            "calibration_question": coef.calibration_question,
            "low": deltas["low"], "base": deltas["base"], "high": deltas["high"],
            "band_low": lo, "band_high": hi,
        }

    # Levers are independent — run them concurrently. For real (I/O-bound) providers this
    # parallelizes the sweep across the event loop; for mock it interleaves the CPU work.
    tasks = [one(lever, cid) for lever, cid in _GOVERNING.items() if cid in DEFAULT_ELASTICITIES]
    results = await asyncio.gather(*tasks) if tasks else []
    return dict(results)


async def generate_report(run_id: str, primary_dir: Path, rc: dict, cfg, mc: dict, progress=None,
                          optimize_result: dict | None = None, stage: str | None = None,
                          prior: dict | None = None, model_variance: dict | None = None,
                          fallback_metrics: dict | None = None) -> str:
    # fallback_metrics: {metric_id: {sprint: value}} from the persisted runs.metrics, used when
    # the run disk's metrics.csv was wiped by a deploy/restart (see _build_meta).
    # Determinate progress: confidence band (1) + per-lever sensitivity (N) + write (1).
    n_sens = len([l for l in LEVERS if _GOVERNING.get(l) and _GOVERNING.get(l) in DEFAULT_ELASTICITIES])
    total = n_sens + 2
    n = [0]

    def step(message: str) -> None:
        n[0] += 1
        if progress:
            progress(message, n[0], total)

    step("computing the confidence band across your scenarios")
    band = _mc_band(mc)
    objective = (rc.get("objective") or {}).get("weights") or {"ppp": 1.0}
    primary = next(iter(objective.keys()))

    sprints = cfg.sprints
    matters = cfg.matters_per_sprint
    seeds = [settings.seed_base + i for i in range(_SENS_SEEDS)]

    optimize = optimize_result or {
        "objective": primary,
        "objective_label": primary,
        "weights": objective,
        "guardrails": (rc.get("objective") or {}).get("guardrails") or [],
        "baseline_ppp": band["ppp"]["mean"],
        "best_objective": band[primary if primary in band else "ppp"]["mean"],
        "best_delta_objective": 0.0,
        "spread": band["ppp"]["stdev"],
        "ci95": _ci(band["ppp"]),
        "best_combo": [],
    }
    experiments = {
        # Which stage this report is for, so the "At a glance" summary knows whether it's
        # establishing a baseline, confirming levers, or validating a chosen set.
        "stage": stage or ("lever_optimization" if optimize.get("best_combo") else "baseline"),
        "prior": prior,
        # How much simulation stands behind this report — the report quotes these so the
        # reader can size the work rather than take the numbers on faith. Each sensitivity
        # lever costs 3 coefficient points x 2 runs (baseline + lever) x _SENS_SEEDS seeds.
        "run": {
            "baseline_scenarios": band["ppp"]["count"],
            "sensitivity_seeds": _SENS_SEEDS,
            "sensitivity_sims": n_sens * 3 * 2 * _SENS_SEEDS,
        },
        "optimize": optimize,
        "sensitivity": {"bands": await _sensitivity_bands(cfg, seeds, sprints, matters, step)},
        # The model's own uncertainty envelope (measured at the runner for real providers;
        # {"mode":"deterministic"} for mock). The report quotes it so a reader can tell model
        # variance from world variance — the two bands, not one.
        "model_variance": model_variance,
    }

    step("writing the report")
    # Firm context must survive a deploy/restart that wipes the run disk. Build meta from the
    # persisted config snapshot, then let the on-disk meta.json (if it survived) win per key.
    disk_meta = load_meta(primary_dir)
    meta = {**_build_meta(rc, cfg, model_variance), **disk_meta}
    metrics = load_metrics(primary_dir) or fallback_metrics or {}
    markdown = render_report(meta, metrics, experiments, run_label=run_id)
    # The 90-second decision doc — a separate artifact from the full report, rendered from the
    # same meta/experiments (it needs no metrics). Persisted so it regenerates from render_inputs
    # too. Only meaningful once a lever optimization has run; the runner stores it at that stage.
    onepager = render_decision_onepager(meta, experiments)
    # Persist the exact inputs the report was rendered from (incl. the sensitivity bands and
    # model variance), so it can be regenerated from stored data without re-running the sim.
    render_inputs = {"meta": meta, "metrics": metrics, "experiments": experiments}
    return markdown, render_inputs, onepager


def _ci(b: dict) -> float:
    n = b["count"]
    if n == 0:
        return 0.0
    return 1.96 * b["stdev"] / math.sqrt(n)
