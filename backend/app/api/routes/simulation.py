"""Law-firm simulation runner routes.

Launches Monte-Carlo runs, streams live progress over SSE, and serves the generated
report. Writes go through the service-role pool (bypasses RLS); endpoint reads are
ungated (auth is deferred).
"""
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.services.simulation.db import DB, replay_hash
from app.services.simulation.events import EventBus, sse, sse_comment
from app.services.simulation import runner

router = APIRouter()

db = DB()
bus = EventBus(persist=lambda ev: db.append_event(ev["run_id"], ev["seq"], ev["kind"], ev["payload"]))


class RunRequest(BaseModel):
    config: dict
    provider: str = Field(default="mock")
    seeds: int = Field(default=20, ge=1, le=100)
    budget: float | None = None
    max_cost: float | None = None
    firm_id: str | None = None


class OutcomeRequest(BaseModel):
    metric: str = Field(default="ppp")
    actual_value: float
    source: str | None = None


class RunOut(BaseModel):
    run_id: str
    status: str = "queued"
    events_url: str


@router.get("/health")
async def health():
    return {"ok": True}


@router.post("/runs", status_code=202)
async def create_run(req: RunRequest) -> RunOut:
    run_id = await db.create_run(
        req.firm_id, req.config, provider=req.provider, total_seeds=req.seeds,
        budget=req.budget, max_cost=req.max_cost,
    )
    asyncio.create_task(runner.execute_run(run_id, db, bus))
    return RunOut(run_id=run_id, events_url=f"/runs/{run_id}/events")


@router.post("/runs/{run_id}/optimize", status_code=202)
async def optimize(run_id: str):
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    if row.status not in ("complete", "budget_exhausted"):
        raise HTTPException(409, "run must be complete before optimizing")
    asyncio.create_task(runner.optimize_run(run_id, db, bus))
    return {"run_id": run_id, "status": "optimizing"}


@router.post("/runs/{run_id}/scenario", status_code=202)
async def scenario(run_id: str):
    """Stage 3 — run the Monte Carlo against the optimizer's determined lever set. Repeatable:
    each call saves a new scenario_simulation report."""
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    prior = await db.latest_report(run_id, "lever_optimization")
    if prior is None:
        raise HTTPException(409, "run the lever optimization first")
    asyncio.create_task(runner.scenario_run(run_id, db, bus))
    return {"run_id": run_id, "status": "optimizing"}


@router.get("/runs/{run_id}/reports")
async def list_reports(run_id: str):
    """Every saved report for a run — baseline, lever optimization, and scenario simulations —
    newest first, each with its stage, title, and markdown."""
    return await db.list_reports(run_id)


@router.get("/runs")
async def list_runs(firm_id: str | None = None):
    return await db.list_runs(firm_id)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    if not await db.delete_run(run_id):
        raise HTTPException(404, "run not found")
    return {"deleted": run_id}


_RAW_FILES = {"metrics.csv", "decisions.jsonl", "trace.jsonl", "state.json"}


@router.get("/runs/{run_id}/files/{filename}")
async def download_file(run_id: str, filename: str):
    """Serve a run's raw data file for download."""
    if filename not in _RAW_FILES:
        raise HTTPException(404, "unknown file")
    path = Path(settings.work_dir) / run_id / "primary" / filename
    if not path.is_file():
        raise HTTPException(404, "file not available")
    return FileResponse(path, filename=filename)


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    return {
        "run_id": row.run_id, "status": row.status, "provider": row.provider,
        "total_seeds": row.total_seeds, "seeds_completed": row.seeds_completed,
        "budget": row.budget, "max_cost": row.max_cost, "spend": row.spend,
        "has_report": row.report is not None, "error": row.error,
        "replay_hash": replay_hash(row.config_snapshot, row.provider, row.total_seeds),
        "model_variance": row.model_variance,
    }


@router.post("/runs/{run_id}/replay", status_code=202)
async def replay_run(run_id: str):
    """Re-run the exact run from its stored inputs — same config, same provider, same seed
    count. Anyone can check that a replay reproduces the original by comparing the hashes."""
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    new_id = await db.create_run(
        None, row.config_snapshot, provider=row.provider, total_seeds=row.total_seeds,
        budget=row.budget, max_cost=row.max_cost,
    )
    asyncio.create_task(runner.execute_run(new_id, db, bus))
    return RunOut(run_id=new_id, events_url=f"/runs/{new_id}/events")


@router.get("/runs/{run_id}/predictions")
async def list_predictions(run_id: str):
    """The model's recorded predictions for this run — the falsifiable claims awaiting or
    carrying a real outcome."""
    if await db.fetch_run(run_id) is None:
        raise HTTPException(404, "run not found")
    return await db.run_predictions(run_id)


@router.post("/runs/{run_id}/outcomes", status_code=201)
async def record_outcome(run_id: str, req: OutcomeRequest):
    """Attach a real outcome to the run's prediction for a metric. This is the validation
    write: predicted PPP vs what actually happened, measured against the predicted band."""
    if await db.fetch_run(run_id) is None:
        raise HTTPException(404, "run not found")
    pred = await db.latest_prediction(run_id, req.metric)
    if pred is None:
        raise HTTPException(409, f"no {req.metric} prediction recorded for this run")
    await db.record_outcome(pred["id"], req.actual_value, req.source)
    return {"prediction_id": pred["id"], "metric": req.metric,
            "actual_value": req.actual_value}


@router.get("/firms/{firm_id}/divergence")
async def firm_divergence(firm_id: str):
    """The validation record for a firm: every prediction, its outcome, the error, and whether
    the actual landed inside the predicted band. The honest 'where the model was wrong' page."""
    return await db.firm_divergence(firm_id)


@router.get("/runs/{run_id}/config")
async def get_config(run_id: str):
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    return row.config_snapshot


@router.get("/runs/{run_id}/metrics")
async def get_metrics(run_id: str):
    metrics = await db.load_metrics(run_id)
    if not metrics:
        raise HTTPException(404, "metrics not available")
    return metrics


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str):
    row = await db.fetch_run(run_id)
    if row is None:
        raise HTTPException(404, "run not found")
    if not row.report:
        raise HTTPException(409, "report not ready")
    return StreamingResponse(iter([row.report]), media_type="text/markdown")


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str):
    async def gen():
        # Replay the persisted history first (source of truth after crash/resume), then tail live.
        watermark = 0
        for ev in await db.list_events(run_id):
            watermark = max(watermark, ev["seq"])
            yield sse({"run_id": run_id, **ev})
        yield sse_comment("live")

        q = bus.subscribe(run_id)
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield sse_comment("ping")  # keep-alive
                    continue
                if ev["seq"] <= watermark:
                    continue
                yield sse(ev)
        finally:
            bus.unsubscribe(run_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
