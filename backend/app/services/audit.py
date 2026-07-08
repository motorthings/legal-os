"""
Legal AI OS — Audit Trail Service

Shared across all 8 functions. Every AI decision is captured.
Immutable — INSERT only, no UPDATE/DELETE via RLS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.database import get_supabase
from app.llm import LLMResponse


class AuditTrail:
    """
    Immutable audit log for every AI decision.

    Usage:
        audit = AuditTrail()
        entry = await audit.record_function_invocation(
            client_id=...,
            function_id=...,
            matter_id=...,
            llm_response=response,
            ...
        )
    """

    def record(
        self,
        *,
        client_id: UUID,
        event_type: str,
        initiated_by: UUID,
        model_used: str,
        function_id: UUID | None = None,
        matter_id: UUID | None = None,
        event_summary: str | None = None,
        prompt_raw: str | None = None,
        response_raw: str | None = None,
        reasoning_chain: str | None = None,
        dimension_scores: list[dict] | None = None,
        overall_score: int | None = None,
        rubric_snapshot: dict | None = None,
        rubric_version: str | None = None,
        model_version: str | None = None,
        provider: str | None = None,
        temperature: float | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost_usd: float | None = None,
        processing_time_ms: int | None = None,
        correlation_id: UUID | None = None,
        overridden_by: UUID | None = None,
        override_reason: str | None = None,
        original_score: int | None = None,
        parent_audit_id: UUID | None = None,
    ) -> dict:
        """Insert an immutable audit row. Returns the created row."""

        entry_id = uuid4()
        row = {
            "id": str(entry_id),
            "client_id": str(client_id),
            "matter_id": str(matter_id) if matter_id else None,
            "function_id": str(function_id) if function_id else None,
            "event_type": event_type,
            "event_summary": event_summary,
            "prompt_raw": prompt_raw,
            "response_raw": response_raw,
            "reasoning_chain": reasoning_chain,
            "dimension_scores": dimension_scores,
            "overall_score": overall_score,
            "rubric_snapshot": rubric_snapshot,
            "rubric_version": rubric_version,
            "model_used": model_used,
            "model_version": model_version,
            "provider": provider or "anthropic",
            "temperature": temperature,
            "prompt_tokens": prompt_tokens or 0,
            "completion_tokens": completion_tokens or 0,
            "total_tokens": total_tokens or 0,
            "cost_usd": cost_usd or 0.0,
            "processing_time_ms": processing_time_ms,
            "overridden_by": str(overridden_by) if overridden_by else None,
            "override_reason": override_reason,
            "original_score": original_score,
            "correlation_id": str(correlation_id) if correlation_id else str(entry_id),
            "parent_audit_id": str(parent_audit_id) if parent_audit_id else None,
            "initiated_by": str(initiated_by),
        }

        result = get_supabase().table("audit_trail").insert(row).execute()
        return result.data[0] if result.data else {}

    def record_llm_call(
        self,
        *,
        client_id: UUID,
        function_id: UUID,
        initiated_by: UUID,
        system_prompt: str,
        user_message: str,
        llm_response: LLMResponse,
        matter_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> dict:
        """Convenience: record a full LLM call with prompt + response."""
        return self.record(
            client_id=client_id,
            function_id=function_id,
            matter_id=matter_id,
            event_type="evaluator_reasoning",
            event_summary=f"LLM call to {llm_response.model} — {llm_response.total_tokens} tokens",
            initiated_by=initiated_by,
            model_used=llm_response.model,
            provider=llm_response.provider,
            prompt_raw=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_message}",
            response_raw=llm_response.text,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            cost_usd=llm_response.cost_usd,
            processing_time_ms=llm_response.processing_time_ms,
            correlation_id=correlation_id,
        )

    def record_human_override(
        self,
        *,
        client_id: UUID,
        function_id: UUID,
        matter_id: UUID,
        original_audit_id: UUID,
        original_score: int,
        new_score: int,
        override_reason: str,
        overridden_by: UUID,
        correlation_id: UUID,
    ) -> dict:
        """Record an attorney override of an AI decision."""
        return self.record(
            client_id=client_id,
            function_id=function_id,
            matter_id=matter_id,
            event_type="human_override",
            event_summary=f"Score overridden: {original_score} → {new_score}",
            initiated_by=overridden_by,
            model_used="human",
            overall_score=new_score,
            original_score=original_score,
            overridden_by=overridden_by,
            override_reason=override_reason,
            correlation_id=correlation_id,
            parent_audit_id=original_audit_id,
        )

    def get_audit_trail(
        self,
        *,
        client_id: UUID,
        matter_id: UUID | None = None,
        function_id: UUID | None = None,
        correlation_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Query the audit trail with filters."""
        query = (
            get_supabase()
            .table("audit_trail")
            .select("*")
            .eq("client_id", str(client_id))
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )
        if matter_id:
            query = query.eq("matter_id", str(matter_id))
        if function_id:
            query = query.eq("function_id", str(function_id))
        if correlation_id:
            query = query.eq("correlation_id", str(correlation_id))

        result = query.execute()
        return result.data
