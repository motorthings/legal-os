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
from app.services.simulation.db import DB
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
    }


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
