"""The Monte-Carlo runner. Executes a run's config across N seeds with:
  - per-seed checkpointing (crash-resume via `runs.seeds_completed`),
  - live per-sprint SSE progress (via the orchestrator's on_progress hook),
  - hard budget enforcement (min of budget / max_cost, minus cumulative spend).
Reuses the engine's build_sim_config + Orchestrator + export_results, and points the
shared report machinery (optimize.set_base_firm) at the run's firm.
"""
import asyncio
import math
import statistics
from dataclasses import replace
from pathlib import Path

from app.config import settings
from simulation.run_config import build_sim_config
from simulation.src.orchestrator import Orchestrator
from simulation.optimize import set_base_firm, _COLLECT, run_optimization, run_scenario_mc

from . import reportgen
from .db import replay_hash

WORK_DIR = Path(settings.work_dir)

# Sampling temperatures for the model-variance sweep. Same structure, same seed — only the
# LLM's sampling varies — so the spread it yields is the MODEL's uncertainty, separate from
# the Monte-Carlo band over seeds (which is structural/process variance).
_MODEL_VAR_TEMPS = (0.2, 0.7, 1.2)


def _combo_label(combo: list | None) -> str:
    """A lever set as a human-readable label — 'pricing + seams + comp', or 'no levers'."""
    return " + ".join(combo) if combo else "no levers"


async def _model_variance(cfg, *, cumulative, budget, cap) -> dict:
    """Measure the model's own uncertainty by re-running the same firm at different LLM
    sampling temperatures. For a real provider this is the spread the LLM adds ON TOP of the
    Monte-Carlo band; for mock it's trivially zero (deterministic — same answer every time).

    Budget-guarded: the sweep only runs while spend stays under the run's cap, and reports
    honestly if budget ran out before two temperatures could complete."""
    if cfg.llm_provider == "mock":
        return {"mode": "deterministic", "count": 0}
    values, spent = [], cumulative
    for temp in _MODEL_VAR_TEMPS:
        remaining = budget if budget is not None else math.inf
        if cap is not None:
            remaining = min(remaining, cap)
        remaining -= spent
        if remaining <= 0:
            break
        seed_cfg = replace(cfg, seed=cfg.seed, run_id="VAR",
                           llm_temperature=temp, max_cost=remaining)
        orch = Orchestrator(seed_cfg)
        orch.initialize()
        run = await orch.run()
        spent += getattr(getattr(orch.llm, "usage", None), "cost_estimate", 0.0)
        h = run.company.metric_history.get("ppp")
        if h and h.values:
            values.append(h.values[-1].value)
    if len(values) < 2:
        return {"mode": "llm", "count": len(values),
                "reason": "insufficient budget to measure model variance"}
    return {
        "mode": "llm", "count": len(values),
        "temps": list(_MODEL_VAR_TEMPS[:len(values)]),
        "values": [round(v) for v in values],
        "mean": round(statistics.mean(values)),
        "stdev": round(statistics.stdev(values)),
        "low": round(min(values)), "high": round(max(values)),
        "spread": round(max(values) - min(values)),
    }


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

    # The model's own uncertainty — separate from the seed-level MC band. Mock is free
    # (deterministic); a real provider pays the cost of a short temperature sweep, guarded by
    # the run's budget. Persisted so the UI and later-stage reports can both quote it.
    model_variance = await _model_variance(cfg, cumulative=cumulative, budget=budget, cap=cap)
    try:
        await db.save_model_variance(run_id, model_variance)
    except Exception:
        pass  # non-fatal — the report still stamps what it has

    if primary_dir.exists() and completed > 0:
        bus.publish(run_id, "status", {"status": "generating_report",
                                       "seeds_completed": completed, "total_seeds": row.total_seeds,
                                       "spend": cumulative})
        report = await reportgen.generate_report(
            run_id, primary_dir, rc, cfg, mc,
            progress=lambda msg, done=None, total=None: bus.publish(
                run_id, "progress", {"message": msg, "done": done, "total": total}),
            stage="baseline", model_variance=model_variance,
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
    model_variance = await db.load_model_variance(run_id)
    report = await reportgen.generate_report(
        run_id, primary_dir, rc, cfg, mc,
        progress=lambda msg, done=None, total=None: bus.publish(
            run_id, "progress", {"message": msg, "done": done, "total": total}),
        optimize_result=opt, stage="lever_optimization",
        model_variance=model_variance,
    )
    combo = opt.get("best_combo") or []
    await db.set_status(run_id, "complete", report=report)
    # Stage 2 — Lever Optimization. Store the full optimize dict as payload so a Scenario
    # Simulation can reuse this narrative and only refresh the confidence band.
    await db.insert_report(
        run_id, "lever_optimization", f"Lever Optimization · {_combo_label(combo)}",
        report_markdown=report, lever_set=combo, payload=opt)

    # Back-test: record the recommendation's headline claim as a falsifiable prediction
    # (point + band, bound to its inputs by the replay hash). A real outcome recorded later
    # is measured against this — the validation loop that tells us whether the model was right.
    _best = opt.get("best_ppp") or opt.get("best_objective")
    _spread = opt.get("spread")
    if _best is not None:
        try:
            await db.insert_prediction(
                firm_id=row.firm_id, run_id=run_id, metric="ppp",
                predicted_value=_best,
                band_low=(_best - _spread) if _spread is not None else None,
                band_high=(_best + _spread) if _spread is not None else None,
                horizon_sprints=cfg.sprints,
                config_hash=replay_hash(row.config_snapshot, row.provider, row.total_seeds),
            )
        except Exception:
            pass  # non-fatal — the report stands; the validation record is best-effort

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

    # Reuse the optimization's narrative; only the band-dependent numbers move. Keep the
    # optimization's estimate as `prior` so the summary can say whether the re-run held up.
    prior = {"best_delta": base_opt.get("best_delta"),
             "best_delta_objective": base_opt.get("best_delta_objective")}
    opt = {**base_opt, **overlay}
    model_variance = await db.load_model_variance(run_id)
    bus.publish(run_id, "progress", {"message": "writing the scenario report"})
    report = await reportgen.generate_report(
        run_id, primary_dir, rc, cfg, mc,
        progress=lambda msg, done=None, total=None: bus.publish(
            run_id, "progress", {"message": msg, "done": done, "total": total}),
        optimize_result=opt,
        stage="scenario_simulation",
        prior=prior, model_variance=model_variance,
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
