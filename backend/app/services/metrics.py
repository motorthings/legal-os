"""
Legal AI OS — Metrics Service

Shared across all 8 functions. Every invocation writes one telemetry row.
ROI reporting is a query against the metrics table.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import settings
from app.database import get_supabase
from app.llm import LLMResponse


class MetricsCollector:
    """
    Collects and persists invocation-level telemetry.

    Usage:
        collector = MetricsCollector()
        collector.start(client_id, function_id, matter_id, initiated_by)

        # ... run the function pipeline ...

        collector.finish(
            llm_response=response,
            human_time_equivalent_ms=1_800_000,  # 30 min
        )
    """

    def __init__(self):
        self._start_time: float | None = None
        self._started_at: datetime | None = None
        self._client_id: UUID | None = None
        self._matter_id: UUID | None = None
        self._function_id: UUID | None = None
        self._initiated_by: UUID | None = None
        self._audit_trail_id: UUID | None = None
        self._practice_group_id: UUID | None = None
        self._tags: dict = {}

    def start(
        self,
        client_id: UUID,
        function_id: UUID,
        initiated_by: UUID,
        matter_id: UUID | None = None,
        practice_group_id: UUID | None = None,
        audit_trail_id: UUID | None = None,
        tags: dict | None = None,
    ) -> None:
        self._start_time = time.monotonic()
        self._started_at = datetime.now(timezone.utc)
        self._client_id = client_id
        self._function_id = function_id
        self._initiated_by = initiated_by
        self._matter_id = matter_id
        self._practice_group_id = practice_group_id
        self._audit_trail_id = audit_trail_id
        self._tags = tags or {}

    def finish(
        self,
        llm_response: LLMResponse | None = None,
        human_time_equivalent_ms: int = 0,
        result_quality: str | None = None,
        confidence: int | None = None,
    ) -> None:
        """Persist the metrics row to Supabase."""
        if self._start_time is None:
            return

        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
        completed_at = datetime.now(timezone.utc)

        prompt_tokens = llm_response.prompt_tokens if llm_response else 0
        completion_tokens = llm_response.completion_tokens if llm_response else 0
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = llm_response.cost_usd if llm_response else 0.0
        model = llm_response.model if llm_response else "unknown"

        time_saved = max(0, human_time_equivalent_ms - elapsed_ms)

        row = {
            "id": str(uuid4()),
            "client_id": str(self._client_id) if self._client_id else None,
            "matter_id": str(self._matter_id) if self._matter_id else None,
            "function_id": str(self._function_id) if self._function_id else None,
            "audit_trail_id": str(self._audit_trail_id) if self._audit_trail_id else None,
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "processing_time_ms": elapsed_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "model_used": model,
            "human_time_equivalent_ms": human_time_equivalent_ms,
            "time_saved_ms": time_saved,
            "result_quality": result_quality,
            "confidence": confidence,
            "initiated_by": str(self._initiated_by) if self._initiated_by else None,
            "practice_group_id": str(self._practice_group_id) if self._practice_group_id else None,
            "tags": self._tags,
        }

        try:
            get_supabase().table("metrics").insert(row).execute()
        except Exception:
            # Metrics failure should never break the function
            import logging
            logging.getLogger("metrics").warning(
                "Failed to persist metrics row", exc_info=True
            )

    def get_elapsed_ms(self) -> int:
        """Get elapsed time so far without stopping."""
        if self._start_time is None:
            return 0
        return int((time.monotonic() - self._start_time) * 1000)


# ---------------------------------------------------------------------------
# Reporting queries
# ---------------------------------------------------------------------------

def get_client_monthly_rollup(
    client_id: UUID,
    months: int = 12,
) -> list[dict]:
    """Return monthly metrics rollup for a client (powers the portfolio dashboard)."""
    result = (
        get_supabase()
        .table("metrics_monthly_rollup")
        .select("*")
        .eq("client_id", str(client_id))
        .order("month", desc=True)
        .limit(months)
        .execute()
    )
    return result.data


def get_client_summary(client_id: UUID) -> dict | None:
    """Return client-level summary stats."""
    result = (
        get_supabase()
        .table("client_summary")
        .select("*")
        .eq("client_id", str(client_id))
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def get_time_saved_baseline(function_id: UUID, client_id: UUID | None = None) -> int:
    """Get the configured time-saved baseline for a function, falling back to global default."""
    query = (
        get_supabase()
        .table("time_saved_baselines")
        .select("baseline_seconds")
        .eq("function_id", str(function_id))
    )
    if client_id:
        query = query.eq("client_id", str(client_id))
    else:
        query = query.is_("client_id", "null")

    result = query.execute()
    if result.data:
        return result.data[0]["baseline_seconds"]
    return 0
