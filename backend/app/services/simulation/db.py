"""Postgres access for the simulation runner. Reuses legal-os's shared asyncpg pool.

The db layer is the source of truth for run state: the `runs` row carries the resume
checkpoint (`seeds_completed` + `spend`), and `run_events` persists the SSE stream for
replay. Methods are async so the runner can await the authoritative checkpoint writes
while per-sprint progress events persist fire-and-forget.
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Optional

from app.database import get_pool


def replay_hash(config_snapshot: dict, provider: str, total_seeds: int) -> str:
    """A stable fingerprint of exactly what a run will replay with. Same config + provider +
    seed count => same hash, so a published report is bound to its inputs and any replay is
    verifiably the same run. Computed from the stored snapshot (not the engine's typed
    config) so it never drifts from what the DB actually holds."""
    canonical = json.dumps(config_snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        canonical.encode() + b"|" + provider.encode() + b"|" + str(total_seeds).encode()
    ).hexdigest()[:16]


def _divergence_rows(rows: list) -> list[dict]:
    """Shape raw prediction+outcome rows into the divergence record: the error, the percentage
    error, and whether the actual landed inside the predicted band. Pure so it's testable
    without a database."""
    out = []
    for r in rows:
        pred = r["predicted_value"]
        actual = r["actual_value"]
        lo, hi = r["band_low"], r["band_high"]
        in_band = (lo is not None and hi is not None and actual is not None
                   and lo <= actual <= hi)
        out.append({
            "prediction_id": str(r["id"]),
            "run_id": str(r["run_id"]) if r["run_id"] else None,
            "metric": r["metric"],
            "predicted_value": pred,
            "band_low": lo, "band_high": hi,
            "horizon_sprints": r["horizon_sprints"],
            "config_hash": r["config_hash"],
            "predicted_at": r["predicted_at"].isoformat() if r["predicted_at"] else None,
            "actual_value": actual,
            "source": r["source"],
            "error": (actual - pred) if (actual is not None and pred is not None) else None,
            "pct_error": (100.0 * (actual - pred) / pred
                          if (actual is not None and pred) else None),
            "in_band": in_band,
            "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
        })
    return out


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
    firm_id: Optional[str] = None
    model_variance: Optional[dict] = None


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
               spend, config_snapshot, report, mc_checkpoint, error, firm_id, model_variance
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
            firm_id=str(row["firm_id"]) if row["firm_id"] else None,
            model_variance=json.loads(row["model_variance"]) if row["model_variance"] else None,
        )

    async def save_model_variance(self, run_id: str, mv: dict) -> None:
        await self._pool.execute(
            "update runs set model_variance = $2, updated_at = now() where id = $1",
            run_id, json.dumps(mv),
        )

    async def load_model_variance(self, run_id: str) -> Optional[dict]:
        row = await self._pool.fetchrow(
            "select model_variance from runs where id = $1", run_id)
        return json.loads(row["model_variance"]) if row and row["model_variance"] else None

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

    async def save_metrics(self, run_id: str, metrics: dict) -> None:
        """Persist the primary seed's per-sprint trajectories for the frontend charts."""
        await self._pool.execute(
            "update runs set metrics = $2, updated_at = now() where id = $1",
            run_id, json.dumps(metrics),
        )

    async def load_metrics(self, run_id: str) -> Optional[dict]:
        row = await self._pool.fetchrow("select metrics from runs where id = $1", run_id)
        return json.loads(row["metrics"]) if row and row["metrics"] else None

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

    async def delete_run(self, run_id: str) -> bool:
        """Delete a run and its persisted event stream. Returns True if the run existed."""
        await self._pool.execute("delete from run_events where run_id = $1", run_id)
        row = await self._pool.fetchrow("delete from runs where id = $1 returning id", run_id)
        return row is not None

    # --- reports (one row per stage: baseline / lever_optimization / scenario_simulation) ---

    async def insert_report(self, run_id: str, stage: str, title: str, *,
                            report_markdown: str, lever_set: Optional[list] = None,
                            payload: Optional[dict] = None) -> str:
        """Save a stage's report. Never overwrites — each call is a new saved report, so a
        scenario simulation can be re-run against the same lever set again and again."""
        row = await self._pool.fetchrow(
            """insert into sim_reports (run_id, stage, title, lever_set, payload, report_markdown)
               values ($1, $2, $3, $4, $5, $6) returning id""",
            run_id, stage, title, json.dumps(lever_set or []),
            json.dumps(payload) if payload is not None else None, report_markdown,
        )
        return str(row["id"])

    async def list_reports(self, run_id: str) -> list[dict]:
        """All saved reports for a run, newest first."""
        rows = await self._pool.fetch(
            """select id, stage, title, lever_set, payload, report_markdown, created_at
               from sim_reports where run_id = $1 order by created_at desc""", run_id)
        return [{
            "id": str(r["id"]), "stage": r["stage"], "title": r["title"],
            "lever_set": json.loads(r["lever_set"]) if r["lever_set"] else [],
            "payload": json.loads(r["payload"]) if r["payload"] else None,
            "report_markdown": r["report_markdown"],
            "created_at": r["created_at"].isoformat(),
        } for r in rows]

    async def latest_report(self, run_id: str, stage: str) -> Optional[dict]:
        """The most recent report for a run at a given stage, with its stored payload."""
        r = await self._pool.fetchrow(
            """select id, stage, title, lever_set, payload, report_markdown, created_at
               from sim_reports where run_id = $1 and stage = $2
               order by created_at desc limit 1""", run_id, stage)
        if r is None:
            return None
        return {
            "id": str(r["id"]), "stage": r["stage"], "title": r["title"],
            "lever_set": json.loads(r["lever_set"]) if r["lever_set"] else [],
            "payload": json.loads(r["payload"]) if r["payload"] else None,
            "report_markdown": r["report_markdown"],
            "created_at": r["created_at"].isoformat(),
        }

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

    # --- predictions & outcomes (the back-test / validation loop) ---

    async def insert_prediction(self, *, firm_id, run_id, metric, predicted_value,
                                band_low=None, band_high=None, horizon_sprints=None,
                                config_hash=None) -> str:
        """Record a model prediction (point + honest band) for a firm/run. Later an actual
        outcome attaches to it via record_outcome, and divergence is measured from the pair."""
        pid = str(__import__("uuid").uuid4())
        await self._pool.execute(
            """insert into prediction_records (id, firm_id, run_id, metric, predicted_value,
               band_low, band_high, horizon_sprints, config_hash)
               values ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            pid, firm_id, run_id, metric, predicted_value, band_low, band_high,
            horizon_sprints, config_hash,
        )
        return pid

    async def run_predictions(self, run_id: str) -> list[dict]:
        rows = await self._pool.fetch(
            """select id, metric, predicted_value, band_low, band_high, horizon_sprints,
                      config_hash, created_at from prediction_records
               where run_id = $1 order by created_at desc""", run_id)
        return [{
            "prediction_id": str(r["id"]), "metric": r["metric"],
            "predicted_value": r["predicted_value"], "band_low": r["band_low"],
            "band_high": r["band_high"], "horizon_sprints": r["horizon_sprints"],
            "config_hash": r["config_hash"],
            "predicted_at": r["created_at"].isoformat() if r["created_at"] else None,
        } for r in rows]

    async def latest_prediction(self, run_id: str, metric: str) -> Optional[dict]:
        row = await self._pool.fetchrow(
            """select id, firm_id, predicted_value, band_low, band_high from prediction_records
               where run_id = $1 and metric = $2 order by created_at desc limit 1""",
            run_id, metric)
        if row is None:
            return None
        return {**dict(row), "id": str(row["id"]),
                "firm_id": str(row["firm_id"]) if row["firm_id"] else None}

    async def record_outcome(self, prediction_record_id: str, actual_value: float,
                             source: Optional[str] = None) -> None:
        """Attach a real outcome to a prediction. The recorded_at timestamp anchors the
        divergence check — an outcome recorded long after the horizon is less meaningful."""
        await self._pool.execute(
            """insert into outcome_records (prediction_record_id, actual_value, source)
               values ($1,$2,$3)""",
            prediction_record_id, actual_value, source)

    async def firm_divergence(self, firm_id: str) -> list[dict]:
        """Every prediction with its recorded outcome: the error and whether the actual fell
        inside the predicted band. This is the validation record — 'here's where the model
        was wrong', shown honestly, not hidden."""
        rows = await self._pool.fetch(
            """select p.id, p.run_id, p.metric, p.predicted_value, p.band_low, p.band_high,
                      p.horizon_sprints, p.config_hash, p.created_at as predicted_at,
                      o.actual_value, o.source, o.recorded_at
               from prediction_records p
               left join outcome_records o on o.prediction_record_id = p.id
               where p.firm_id = $1
               order by p.created_at desc""", firm_id)
        return _divergence_rows(rows)
