"""The Monte-Carlo runner. Executes a run's config across N seeds with:
  - per-seed checkpointing (crash-resume via `runs.seeds_completed`),
  - live per-sprint SSE progress (via the orchestrator's on_progress hook),
  - hard budget enforcement (min of budget / max_cost, minus cumulative spend).
Reuses the engine's build_sim_config + Orchestrator + export_results, and points the
shared report machinery (optimize.set_base_firm) at the run's firm.
"""
import asyncio
import json
import math
from dataclasses import replace
from pathlib import Path

from app.config import settings
from simulation.run_config import build_sim_config
from simulation.src.orchestrator import Orchestrator
from simulation.optimize import set_base_firm, _COLLECT

from . import reportgen

WORK_DIR = Path(settings.work_dir)


def workdir(run_id: str) -> Path:
    d = WORK_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_progress(bus, run_id, idx, seed):
    """Return an on_progress callback bound to this seed (avoids late-binding closure bug)."""
    def cb(sprint: int, metrics: dict) -> None:
        bus.publish(run_id, "sprint", {
            "seed_index": idx, "seed": seed, "sprint": sprint,
            "metrics": {k: round(v, 3) for k, v in metrics.items()},
        })
    return cb


def _seed_finals(run) -> dict:
    out = {}
    for m in _COLLECT:
        h = run.company.metric_history.get(m)
        out[m] = h.values[-1].value if h and h.values else 0.0
    return out


def _mc_path(run_id: str) -> Path:
    return workdir(run_id) / "mc_checkpoint.json"


def _load_mc(run_id: str, start: int) -> dict:
    """Reload the per-seed finals for seeds already completed on a prior (crashed) launch,
    so a resumed run builds the full MC band from all seeds, not just this session's."""
    p = _mc_path(run_id)
    if start > 0 and p.exists():
        data = json.loads(p.read_text())
        if len(data.get("ppp", [])) >= start:
            return {m: list(data.get(m, [])) for m in _COLLECT}
    return {m: [] for m in _COLLECT}


def _save_mc(run_id: str, mc: dict) -> None:
    _mc_path(run_id).write_text(json.dumps(mc))


async def execute_run(run_id: str, db, bus) -> None:
    row = await db.fetch_run(run_id)
    if row is None:
        return
    await db.set_status(run_id, "running")
    bus.publish(run_id, "status", {
        "status": "running", "seeds_completed": row.seeds_completed,
        "total_seeds": row.total_seeds, "spend": row.spend,
    })

    rc = row.config_snapshot
    out_dir = workdir(run_id)
    cfg = build_sim_config(rc, provider=row.provider, output_dir=str(out_dir))

    # Point the shared report machinery (sensitivity bands, report) at THIS firm + its
    # calibrated elasticities, not the archetype. Clears the trial cache.
    set_base_firm(cfg.firm_signature, cfg.elasticities)

    # The MC seed set: index 0 is the primary (the config's own seed, whose run dir becomes
    # the report); indices 1..N-1 give the confidence band.
    seeds = [settings.seed_base + i for i in range(row.total_seeds)]
    seeds[0] = (rc.get("run") or {}).get("seed", 42)

    # RESUME: skip seeds already completed on a prior (crashed) launch, reloading their
    # finals from the on-disk checkpoint so the MC band reflects all seeds.
    start = row.seeds_completed
    mc = _load_mc(run_id, start)
    cumulative = row.spend
    budget = row.budget
    cap = row.max_cost
    primary_dir: Path | None = None

    for i in range(start, row.total_seeds):
        remaining = budget if budget is not None else math.inf
        if cap is not None:
            remaining = min(remaining, cap)
        remaining -= cumulative
        if remaining <= 0:
            await db.set_status(run_id, "budget_exhausted", error="budget exhausted")
            bus.publish(run_id, "status", {"status": "budget_exhausted",
                                           "seeds_completed": i, "spend": cumulative})
            break

        seed = seeds[i]
        is_primary = i == 0
        seed_cfg = replace(cfg, seed=seed, run_id="primary" if is_primary else "MC",
                           max_cost=remaining)
        orch = Orchestrator(seed_cfg)
        orch.on_progress = _make_progress(bus, run_id, i, seed)
        orch.initialize()
        run = await orch.run()

        spend_seed = getattr(getattr(orch.llm, "usage", None), "cost_estimate", 0.0)
        cumulative += spend_seed

        finals = _seed_finals(run)
        for m in _COLLECT:
            mc[m].append(finals[m])
        _save_mc(run_id, mc)

        if is_primary:
            orch.export_results(run)          # lays down meta/metrics/state + auto report.md
            primary_dir = out_dir / "primary"

        # Authoritative resume checkpoint (awaited) — the source of truth after a crash.
        await db.persist_progress(run_id, seeds_completed=i + 1, spend=cumulative)
        bus.publish(run_id, "seed", {"seed_index": i, "seed": seed,
                                     "spend_delta": spend_seed, "spend": cumulative})

        if budget is not None and cumulative >= budget:
            await db.set_status(run_id, "budget_exhausted", error="budget exhausted")
            bus.publish(run_id, "status", {"status": "budget_exhausted",
                                           "seeds_completed": i + 1, "spend": cumulative})
            break

    # Report from whatever completed (full MC, or the subset under budget). On a resumed
    # run the primary's folder persists on disk from the prior launch.
    completed = len(mc["ppp"])
    primary_dir = primary_dir or (out_dir / "primary")
    if primary_dir.exists() and completed > 0:
        report_ref = await reportgen.generate_report(run_id, primary_dir, rc, cfg, mc)
    else:
        report_ref = None

    final_status = "complete" if completed >= row.total_seeds else "budget_exhausted"
    await db.set_status(run_id, final_status, report_ref=str(report_ref) if report_ref else None)
    bus.publish(run_id, "status", {"status": final_status, "seeds_completed": completed,
                                   "total_seeds": row.total_seeds, "spend": cumulative})
    bus.publish(run_id, "report_ready", {"report_ref": report_ref}) if report_ref else None
