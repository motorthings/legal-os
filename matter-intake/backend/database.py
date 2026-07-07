"""
Async SQLite database for storing evaluation records with full audit trail.

Schema stores every decision the pipeline made:
  - Router raw input/output
  - Evaluator raw input/output
  - All 5 dimension scores with reasoning
  - Timestamps, tokens, model info

GET /api/evaluations/:id/audit returns the complete decision chain.
"""

import json
import os
from datetime import datetime, timezone

import aiosqlite

from logger import get_logger

log = get_logger("database")

DB_DIR = os.environ.get("DB_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DB_DIR, "evaluations.db")

_initialized = False


async def get_db() -> aiosqlite.Connection:
    global _initialized
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    if not _initialized:
        await _create_schema(db)
        _initialized = True
    return db


async def _create_schema(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            overall_risk_level TEXT NOT NULL,
            practice_area TEXT NOT NULL,
            practice_area_confidence INTEGER NOT NULL,
            urgency_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            conflict_type TEXT NOT NULL,
            conflict_entity TEXT,
            recommended_role TEXT NOT NULL,
            estimated_hours INTEGER NOT NULL,
            team_assignment TEXT,
            completeness INTEGER NOT NULL,
            clarity INTEGER NOT NULL,
            summary_preview TEXT NOT NULL,
            processing_time_ms INTEGER NOT NULL,
            model_used TEXT NOT NULL,
            matter_summary TEXT NOT NULL DEFAULT '',
            router_raw_input TEXT NOT NULL DEFAULT '',
            router_raw_output TEXT NOT NULL DEFAULT '',
            evaluator_raw_input TEXT NOT NULL DEFAULT '',
            evaluator_raw_output TEXT NOT NULL DEFAULT '',
            dimension_scores_json TEXT NOT NULL DEFAULT '[]',
            full_response_json TEXT NOT NULL DEFAULT '{}',
            rubrics_snapshot TEXT NOT NULL DEFAULT '{}'
        )
    """)
    # Add rubrics_snapshot to existing tables (migration for deployed DB)
    try:
        await db.execute("ALTER TABLE evaluations ADD COLUMN rubrics_snapshot TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass  # Column already exists

    # Settings table (key-value for teams, rubrics, preferences)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    await db.commit()
    log.info("db_init", extra={
        "event_type": "db_init",
        "context": None,
        "data": {"path": DB_PATH},
        "duration_ms": 0,
    })


# ---------------------------------------------------------------------------
# Evaluations CRUD
# ---------------------------------------------------------------------------

async def save_evaluation(
    matter_summary: str,
    response_json: dict,
    router_raw_input: str,
    router_raw_output: str,
    evaluator_raw_input: str,
    evaluator_raw_output: str,
    dimension_scores: list[dict],
    rubrics_snapshot: dict,
) -> int:
    db = await get_db()
    cursor = await db.execute(
        """
        INSERT INTO evaluations (
            created_at, overall_score, overall_risk_level,
            practice_area, practice_area_confidence,
            urgency_level, risk_score,
            conflict_type, conflict_entity,
            recommended_role, estimated_hours,
            completeness, clarity,
            summary_preview, processing_time_ms, model_used,
            matter_summary,
            router_raw_input, router_raw_output,
            evaluator_raw_input, evaluator_raw_output,
            dimension_scores_json, full_response_json,
            rubrics_snapshot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            response_json["overall_score"],
            response_json["overall_risk_level"],
            response_json["practice_area"]["practice_area"],
            response_json["practice_area"]["confidence"],
            response_json["urgency_risk"]["urgency_level"],
            response_json["urgency_risk"]["risk_score"],
            response_json["conflict_check"]["conflict_type"],
            response_json["conflict_check"].get("entity_name"),
            response_json["staffing"]["recommended_role"],
            response_json["staffing"]["estimated_hours"],
            response_json["data_integrity"]["completeness"],
            response_json["data_integrity"]["clarity"],
            matter_summary[:200],
            response_json["processing_time_ms"],
            response_json["model_used"],
            matter_summary,
            router_raw_input,
            router_raw_output,
            evaluator_raw_input,
            evaluator_raw_output,
            json.dumps(dimension_scores),
            json.dumps(response_json),
            json.dumps(rubrics_snapshot),
        ),
    )
    await db.commit()
    row_id = cursor.lastrowid
    log.info("db_save", extra={
        "event_type": "db_save",
        "context": None,
        "data": {"id": row_id, "score": response_json["overall_score"]},
        "duration_ms": 0,
    })
    return row_id


async def list_evaluations(
    limit: int = 20,
    offset: int = 0,
    search: str = "",
    risk_level: str = "",
    practice_area: str = "",
    urgency_level: str = "",
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict], int]:
    """List evaluations with optional search, filter, and sort. Returns (rows, total_count)."""
    db = await get_db()

    # Build WHERE clauses
    where_clauses: list[str] = []
    params: list = []

    if search:
        where_clauses.append("(practice_area LIKE ? OR summary_preview LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if risk_level:
        where_clauses.append("overall_risk_level = ?")
        params.append(risk_level)

    if practice_area:
        where_clauses.append("practice_area = ?")
        params.append(practice_area)

    if urgency_level:
        where_clauses.append("urgency_level = ?")
        params.append(urgency_level)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Validate sort column to prevent injection
    sort_columns = {
        "created_at", "overall_score", "practice_area",
        "overall_risk_level", "urgency_level",
    }
    if sort_by not in sort_columns:
        sort_by = "created_at"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    # Get total count
    count_cursor = await db.execute(
        f"SELECT COUNT(*) FROM evaluations {where_sql}",
        params,
    )
    total = (await count_cursor.fetchone())[0]

    # Fetch page
    select_sql = f"""
        SELECT id, created_at, overall_score, overall_risk_level,
               practice_area, practice_area_confidence,
               urgency_level, risk_score, conflict_type, conflict_entity,
               recommended_role, estimated_hours,
               completeness, clarity, summary_preview,
               processing_time_ms, model_used
        FROM evaluations
        {where_sql}
        ORDER BY {sort_by} {order}
        LIMIT ? OFFSET ?
    """
    cursor = await db.execute(select_sql, params + [limit, offset])
    rows = await cursor.fetchall()
    return [dict(row) for row in rows], total

async def get_distinct_practice_areas() -> list[str]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT DISTINCT practice_area FROM evaluations ORDER BY practice_area"
    )
    rows = await cursor.fetchall()
    return [row["practice_area"] for row in rows]


async def get_evaluation(eval_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM evaluations WHERE id = ?", (eval_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_audit_trail(eval_id: int) -> dict | None:
    """Return the full audit trail for one evaluation — every decision, raw I/O, and reasoning chain."""
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, created_at, overall_score, overall_risk_level,
               practice_area, practice_area_confidence,
               urgency_level, risk_score,
               conflict_type, conflict_entity,
               recommended_role, estimated_hours,
               completeness, clarity,
               processing_time_ms, model_used,
               matter_summary,
               router_raw_input, router_raw_output,
               evaluator_raw_input, evaluator_raw_output,
               dimension_scores_json, full_response_json,
               rubrics_snapshot
        FROM evaluations WHERE id = ?
        """,
        (eval_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None

    d = dict(row)
    # Parse JSON fields
    for field in ("dimension_scores_json", "full_response_json", "rubrics_snapshot"):
        if d.get(field):
            try:
                d[field.replace("_json", "").replace("_snapshot", "")] = json.loads(d[field])
            except json.JSONDecodeError:
                pass

    # Build structured audit trail
    d["audit_trail"] = {
        "pipeline_stages": [
            {
                "stage": "1_router",
                "description": "Practice area classification using LLM router",
                "input": d.get("router_raw_input", ""),
                "output": d.get("router_raw_output", ""),
                "key_decisions": [
                    f"Classified as: {d.get('practice_area', 'Unknown')}",
                    f"Confidence: {d.get('practice_area_confidence', 0)}/100",
                ],
            },
            {
                "stage": "2_evaluator",
                "description": "Five-dimension evaluation using LLM evaluator",
                "input": d.get("evaluator_raw_input", ""),
                "output": d.get("evaluator_raw_output", ""),
                "key_decisions": [
                    f"Urgency: {d.get('urgency_level', 'N/A')} (risk score: {d.get('risk_score', 0)})",
                    f"Conflict: {d.get('conflict_type', 'N/A')} — {d.get('conflict_entity') or 'no entity'}",
                    f"Staffing: {d.get('recommended_role', 'N/A')} ({d.get('estimated_hours', 0)}h)",
                    f"Data integrity: completeness={d.get('completeness', 0)}, clarity={d.get('clarity', 0)}",
                ],
            },
            {
                "stage": "3_programmatic_scoring",
                "description": "Weighted scoring — deterministic, not LLM-generated",
                "input": d.get("evaluator_raw_output", ""),
                "output": d.get("dimension_scores_json", "[]"),
                "key_decisions": [
                    f"Overall score: {d.get('overall_score', 0)}/100 ({d.get('overall_risk_level', 'N/A')} risk)",
                ],
            },
        ],
        "rubrics_used": d.get("rubrics", {}),
        "explainability_summary": (
            f"This matter was classified as '{d.get('practice_area', 'Unknown')}' "
            f"with {d.get('practice_area_confidence', 0)}% confidence. "
            f"The overall risk level is {d.get('overall_risk_level', 'N/A')} "
            f"(score: {d.get('overall_score', 0)}/100). "
            f"Scoring is programmatic: 25% practice area + 25% urgency/risk + "
            f"20% conflict check + 15% staffing + 15% data integrity. "
            f"Total processing time: {d.get('processing_time_ms', 0)}ms "
            f"using {d.get('model_used', 'unknown model')}."
        ),
    }

    return d


# ---------------------------------------------------------------------------
# Settings CRUD (teams, rubrics, preferences)
# ---------------------------------------------------------------------------

async def get_setting(key: str) -> str | None:
    db = await get_db()
    cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    db = await get_db()
    await db.execute(
        """INSERT INTO settings (key, value, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
        (key, value, datetime.now(timezone.utc).isoformat(),
         value, datetime.now(timezone.utc).isoformat()),
    )
    await db.commit()


async def get_all_settings() -> dict:
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM settings")
    rows = await cursor.fetchall()
    return {row["key"]: json.loads(row["value"]) for row in rows}
