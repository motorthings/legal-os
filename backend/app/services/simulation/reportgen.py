"""Build the client-facing report for a completed run.

Reuses report.build_report by constructing the `experiments` dict the report expects:
  - the Monte Carlo band (mean / stdev / CI95 over the run's completed seeds),
  - firm-specific sensitivity bands (swept over the run's own governing coefficients),
then injecting it into the primary run's folder. `optimize.set_base_firm` must already be
called (by the runner) so the sensitivity sweep runs the FIRM's numbers.
"""
import math
import statistics
from pathlib import Path

from app.config import settings
from simulation.report import build_report
from simulation.optimize import LEVERS, build_overrides
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
_SENS_SEEDS = 6  # cap the band sweep — the report needs a range, not a full CI


async def _ppp_async(pulled, seeds, sprints: int, matters: int, profile) -> float:
    """Mean final PPP for a lever set under a given elasticity profile. Mirrors
    sensitivity._ppp but AWAITS the orchestrator (that one uses asyncio.run, which
    cannot be called from inside the running runner loop)."""
    import contextlib
    import io
    overrides = build_overrides(pulled)
    overrides["elasticities"] = profile
    vals = []
    for seed in seeds:
        cfg = SimulationConfig(sprints=sprints, matters_per_sprint=matters,
                               llm_provider="mock", seed=seed, output_dir="results/_sens",
                               run_id="SENS", **overrides)
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


async def _sensitivity_bands(cfg, seeds, sprints: int, matters: int) -> dict:
    base_profile = cfg.elasticities or default_profile()
    bands = {}
    for lever in LEVERS:
        cid = _GOVERNING.get(lever)
        if not cid or cid not in DEFAULT_ELASTICITIES:
            continue
        coef = DEFAULT_ELASTICITIES[cid]
        deltas = {}
        for where in ("low", "base", "high"):
            prof = base_profile.with_point(cid, where)
            base = await _ppp_async(set(), seeds, sprints, matters, prof)
            lever_ppp = await _ppp_async({lever}, seeds, sprints, matters, prof)
            deltas[where] = lever_ppp - base
        lo, hi = min(deltas.values()), max(deltas.values())
        bands[lever] = {
            "coefficient": cid, "coefficient_name": coef.name, "source": coef.source,
            "low": deltas["low"], "base": deltas["base"], "high": deltas["high"],
            "band_low": lo, "band_high": hi,
        }
    return bands


async def generate_report(run_id: str, primary_dir: Path, rc: dict, cfg, mc: dict) -> Path:
    band = _mc_band(mc)
    objective = (rc.get("objective") or {}).get("weights") or {"ppp": 1.0}
    primary = next(iter(objective.keys()))

    sprints = cfg.sprints
    matters = cfg.matters_per_sprint
    seeds = [settings.seed_base + i for i in range(6)]

    experiments = {
        "optimize": {
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
        },
        "sensitivity": {"bands": await _sensitivity_bands(cfg, seeds, sprints, matters)},
    }

    report = build_report(primary_dir, experiments)
    (primary_dir / "report.md").write_text(report)
    return primary_dir / "report.md"


def _ci(b: dict) -> float:
    n = b["count"]
    if n == 0:
        return 0.0
    return 1.96 * b["stdev"] / math.sqrt(n)
