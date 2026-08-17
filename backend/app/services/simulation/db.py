"""Postgres access for the simulation runner. Reuses legal-os's shared asyncpg pool.

The db layer is the source of truth for run state: the `runs` row carries the resume
checkpoint (`seeds_completed` + `spend`), and `run_events` persists the SSE stream for
replay. Methods are async so the runner can await the authoritative checkpoint writes
while per-sprint progress events persist fire-and-forget.
"""
import json
from dataclasses import dataclass
from typing import Optional

from app.database import get_pool


@dataclass
class RunRow:
    run_id: str
    status: str
    provider: str
    total_seeds: int
    seeds_completed: int
    budget: Optional[float]
    max_cost: Optional[float]
    spend: float
    config_snapshot: dict
    report: Optional[str]
    mc_checkpoint: Optional[dict]
    error: Optional[str]


class DB:
    """Thin wrapper over legal-os's shared asyncpg pool. Swap for a stub in tests."""

    def __init__(self) -> None:
        self._pool = None

    async def connect(self) -> None:
        # Reuse legal-os's singleton pool; app.database.close_pool() owns its lifecycle.
        self._pool = await get_pool()

    async def close(self) -> None:
        self._pool = None  # the shared pool is closed by app.database on shutdown

    # --- runs ---

    async def create_run(self, firm_id: Optional[str], config_snapshot: dict, *,
                         provider: str, total_seeds: int, budget: Optional[float],
                         max_cost: Optional[float]) -> str:
        run_id = str(__import__("uuid").uuid4())
        await self._pool.execute(
            """insert into runs (id, firm_id, status, provider, total_seeds, budget, max_cost,
               config_snapshot)
               values ($1, $2, 'queued', $3, $4, $5, $6, $7)""",
            run_id, firm_id, provider, total_seeds, budget, max_cost,
            json.dumps(config_snapshot),
        )
        return run_id

    async def fetch_run(self, run_id: str) -> Optional[RunRow]:
        row = await self._pool.fetchrow(
            """select id, status, provider, total_seeds, seeds_completed, budget, max_cost,
               spend, config_snapshot, report, mc_checkpoint, error
               from runs where id = $1""", run_id)
        if row is None:
            return None
        return RunRow(
            run_id=str(row["id"]), status=row["status"], provider=row["provider"],
            total_seeds=row["total_seeds"], seeds_completed=row["seeds_completed"],
            budget=row["budget"], max_cost=row["max_cost"], spend=row["spend"],
            config_snapshot=json.loads(row["config_snapshot"]),
            report=row["report"],
            mc_checkpoint=json.loads(row["mc_checkpoint"]) if row["mc_checkpoint"] else None,
            error=row["error"],
        )

    async def set_status(self, run_id: str, status: str, *, report: Optional[str] = None,
                         error: Optional[str] = None) -> None:
        await self._pool.execute(
            "update runs set status = $2, report = coalesce($3, report), "
            "error = $4, updated_at = now() where id = $1",
            run_id, status, report, error,
        )

    async def save_checkpoint(self, run_id: str, mc: dict) -> None:
        """Persist the per-seed finals so a resumed run rebuilds the full MC band."""
        await self._pool.execute(
            "update runs set mc_checkpoint = $2, updated_at = now() where id = $1",
            run_id, json.dumps(mc),
        )

    async def load_checkpoint(self, run_id: str) -> Optional[dict]:
        row = await self._pool.fetchrow(
            "select mc_checkpoint from runs where id = $1", run_id)
        return json.loads(row["mc_checkpoint"]) if row and row["mc_checkpoint"] else None

    async def persist_progress(self, run_id: str, seeds_completed: int, spend: float) -> None:
        """The authoritative resume checkpoint — awaited in the runner loop."""
        await self._pool.execute(
            "update runs set seeds_completed = $2, spend = $3, updated_at = now() "
            "where id = $1",
            run_id, seeds_completed, spend,
        )

    async def list_runs(self, firm_id: str | None = None) -> list[dict]:
        if firm_id:
            rows = await self._pool.fetch(
                "select id, firm_id, status, total_seeds, seeds_completed, spend, created_at "
                "from runs where firm_id = $1 order by created_at desc", firm_id)
        else:
            rows = await self._pool.fetch(
                "select id, firm_id, status, total_seeds, seeds_completed, spend, created_at "
                "from runs order by created_at desc limit 100")
        return [dict(r) for r in rows]

    async def list_stale_runs(self, statuses: tuple = ("queued", "running")) -> list[str]:
        rows = await self._pool.fetch(
            "select id from runs where status = any($1::text[]) order by created_at", statuses)
        return [str(r["id"]) for r in rows]

    # --- events (SSE replay source of truth) ---

    async def append_event(self, run_id: str, seq: int, kind: str, payload: dict) -> None:
        await self._pool.execute(
            "insert into run_events (run_id, seq, kind, payload) values ($1, $2, $3, $4)",
            run_id, seq, kind, json.dumps(payload),
        )

    async def list_events(self, run_id: str) -> list[dict]:
        rows = await self._pool.fetch(
            "select seq, kind, payload from run_events where run_id = $1 order by seq", run_id)
        return [{"seq": r["seq"], "kind": r["kind"], "payload": json.loads(r["payload"])} for r in rows]
