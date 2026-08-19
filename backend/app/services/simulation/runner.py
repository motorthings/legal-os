"""The Monte-Carlo runner. Executes a run's config across N seeds with:
  - per-seed checkpointing (crash-resume via `runs.seeds_completed`),
  - live per-sprint SSE progress (via the orchestrator's on_progress hook),
  - hard budget enforcement (min of budget / max_cost, minus cumulative spend).
Reuses the engine's build_sim_config + Orchestrator + export_results, and points the
shared report machinery (optimize.set_base_firm) at the run's firm.
"""
import asyncio
import math
from dataclasses import replace
from pathlib import Path

from app.config import settings
from simulation.run_config import build_sim_config
from simulation.src.orchestrator import Orchestrator
from simulation.optimize import set_base_firm, _COLLECT, run_optimization, run_scenario_mc

from . import reportgen

WORK_DIR = Path(settings.work_dir)


def _combo_label(combo: list | None) -> str:
    """A lever set as a human-readable label — 'pricing + seams + comp', or 'no levers'."""
    return " + ".join(combo) if combo else "no levers"


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


def _trajectories(run) -> dict:
    """The primary seed's per-sprint metric values (sprint 1 at index 0), for the charts."""
    out = {}
    for m, h in run.company.metric_history.items():
        out[m] = [round(v.value, 3) for v in h.values]
    return out


async def _load_mc(db, run_id: str, start: int) -> dict:
    """Reload the per-seed finals for seeds already completed on a prior (crashed) launch,
    so a resumed run builds the full MC band from all seeds, not just this session's."""
    data = await db.load_checkpoint(run_id)
    if start > 0 and data and len(data.get("ppp", [])) >= start:
        return {m: list(data.get(m, [])) for m in _COLLECT}
    return {m: [] for m in _COLLECT}


async def _save_mc(db, run_id: str, mc: dict) -> None:
    await db.save_checkpoint(run_id, mc)


async def execute_run(run_id: str, db, bus) -> None:
    """Run a firm simulation end-to-end.

    Any exception is caught and recorded on the run row so a crash doesn't orphan the
    run in `running` (which would re-trigger stale-run recovery and crash-loop on restart).
    """
    try:
        await _execute_run(run_id, db, bus)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        try:
            await db.set_status(run_id, "error", error=tb)
        except Exception:
            pass  # DB may be down too; stale recovery re-queues the run
        bus.publish(run_id, "status", {"status": "error", "error": str(exc)})


async def _execute_run(run_id: str, db, bus) -> None:
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
    mc = await _load_mc(db, run_id, start)
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
        await _save_mc(db, run_id, mc)

        if is_primary:
            orch.export_results(run)          # lays down meta/metrics/state + auto report.md
            primary_dir = out_dir / "primary"
            await db.save_metrics(run_id, _trajectories(run))

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
        bus.publish(run_id, "status", {"status": "generating_report",
                                       "seeds_completed": completed, "total_seeds": row.total_seeds,
                                       "spend": cumulative})
        report = await reportgen.generate_report(
            run_id, primary_dir, rc, cfg, mc,
            progress=lambda msg, done=None, total=None: bus.publish(
                run_id, "progress", {"message": msg, "done": done, "total": total}),
        )
    else:
        report = None

    final_status = "complete" if completed >= row.total_seeds else "budget_exhausted"
    await db.set_status(run_id, final_status, report=report)
    if report:
        # Stage 1 — Baseline. Saved as its own report so the lever optimization can't
        # clobber it; the UI shows both, clearly labeled.
        await db.insert_report(
            run_id, "baseline", f"Baseline · {completed} scenarios",
            report_markdown=report, lever_set=[])
    bus.publish(run_id, "status", {"status": final_status, "seeds_completed": completed,
                                   "total_seeds": row.total_seeds, "spend": cumulative})
    if report:
        bus.publish(run_id, "report_ready", {"report": True})


async def optimize_run(run_id: str, db, bus) -> None:
    """Run the adaptive lever optimizer on a completed baseline run and regenerate the
    report with the recommendation. Kept separate from execute_run so the baseline stays fast."""
    row = await db.fetch_run(run_id)
    if row is None:
        return

    rc = row.config_snapshot
    out_dir = workdir(run_id)
    cfg = build_sim_config(rc, provider=row.provider, output_dir=str(out_dir))
    primary_dir = out_dir / "primary"
    mc = await _load_mc(db, run_id, row.seeds_completed)

    bus.publish(run_id, "status", {"status": "optimizing", "total_seeds": row.total_seeds,
                                   "seeds_completed": row.seeds_completed, "spend": row.spend})
    bus.publish(run_id, "progress", {"message": "running the adaptive lever optimization — three rounds"})

    try:
        loop = asyncio.get_running_loop()

        def progress(msg, done=None, total=None):
            loop.call_soon_threadsafe(
                bus.publish, run_id, "progress", {"message": msg, "done": done, "total": total})

        opt = (await asyncio.to_thread(
            run_optimization, rc, sprints=cfg.sprints, matters=cfg.matters_per_sprint,
            progress=progress,
        ))["optimize"]
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        await db.set_status(run_id, "error", error=tb)
        bus.publish(run_id, "status", {"status": "error", "error": str(exc)})
        return

    bus.publish(run_id, "progress", {"message": "regenerating the report with the recommendation"})
    report = await reportgen.generate_report(
        run_id, primary_dir, rc, cfg, mc,
        progress=lambda msg, done=None, total=None: bus.publish(
            run_id, "progress", {"message": msg, "done": done, "total": total}),
        optimize_result=opt,
    )
    combo = opt.get("best_combo") or []
    await db.set_status(run_id, "complete", report=report)
    # Stage 2 — Lever Optimization. Store the full optimize dict as payload so a Scenario
    # Simulation can reuse this narrative and only refresh the confidence band.
    await db.insert_report(
        run_id, "lever_optimization", f"Lever Optimization · {_combo_label(combo)}",
        report_markdown=report, lever_set=combo, payload=opt)
    bus.publish(run_id, "status", {"status": "complete", "seeds_completed": row.seeds_completed,
                                   "total_seeds": row.total_seeds, "spend": row.spend})
    bus.publish(run_id, "report_ready", {"report": True})


async def scenario_run(run_id: str, db, bus) -> None:
    """Stage 3 — Scenario Simulation. Take the lever set the optimization determined and run
    ONLY the final Monte Carlo against it, saving a new report each time. Repeatable: the
    caller can fire this again and again to re-roll the dice on the same lever set."""
    row = await db.fetch_run(run_id)
    if row is None:
        return
    prior = await db.latest_report(run_id, "lever_optimization")
    if prior is None or not prior.get("payload"):
        bus.publish(run_id, "status", {"status": "error",
                                       "error": "run the lever optimization first"})
        return

    base_opt = prior["payload"]
    combo = prior.get("lever_set") or base_opt.get("best_combo") or []
    rc = row.config_snapshot
    out_dir = workdir(run_id)
    cfg = build_sim_config(rc, provider=row.provider, output_dir=str(out_dir))
    primary_dir = out_dir / "primary"
    mc = await _load_mc(db, run_id, row.seeds_completed)

    bus.publish(run_id, "status", {"status": "optimizing", "total_seeds": row.total_seeds,
                                   "seeds_completed": row.seeds_completed, "spend": row.spend})
    bus.publish(run_id, "progress",
                {"message": f"running the Monte Carlo against {_combo_label(combo)}"})

    try:
        def progress(msg, done=None, total=None):
            bus.publish(run_id, "progress", {"message": msg, "done": done, "total": total})

        overlay = await asyncio.to_thread(
            run_scenario_mc, rc, combo, sprints=cfg.sprints, matters=cfg.matters_per_sprint,
            progress=progress)
    except Exception as exc:
        import traceback
        await db.set_status(run_id, "error", error=traceback.format_exc())
        bus.publish(run_id, "status", {"status": "error", "error": str(exc)})
        return

    # Reuse the optimization's narrative; only the band-dependent numbers move.
    opt = {**base_opt, **overlay}
    bus.publish(run_id, "progress", {"message": "writing the scenario report"})
    report = await reportgen.generate_report(
        run_id, primary_dir, rc, cfg, mc,
        progress=lambda msg, done=None, total=None: bus.publish(
            run_id, "progress", {"message": msg, "done": done, "total": total}),
        optimize_result=opt,
    )
    mc_seeds = overlay.get("mc_seeds")
    title = f"Scenario Simulation · {_combo_label(combo)}" + (
        f" · {mc_seeds} scenarios" if mc_seeds else "")
    await db.insert_report(run_id, "scenario_simulation", title,
                           report_markdown=report, lever_set=combo, payload=opt)
    await db.set_status(run_id, "complete", report=report)
    bus.publish(run_id, "status", {"status": "complete", "seeds_completed": row.seeds_completed,
                                   "total_seeds": row.total_seeds, "spend": row.spend})
    bus.publish(run_id, "report_ready", {"report": True})
