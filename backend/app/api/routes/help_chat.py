"""Help chat routes — RAG-based help system with vector search.

Ported from AESOP help system. Uses existing LLMProvider (with fallback resilience)
instead of direct Anthropic client, so it works with any configured provider.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import settings
from app.database import get_supabase
from app.llm import LLMProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/help", tags=["help"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    feedback: int  # -1, 0, or 1


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------


async def _create_embedding(text: str) -> list[float]:
    """Generate embedding using Voyage AI (512-dim). Falls back gracefully."""
    if not settings.voyage_api_key:
        raise HTTPException(
            status_code=500,
            detail="VOYAGE_API_KEY not configured. Embeddings unavailable.",
        )

    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "input": [text],
                "model": "voyage-3-lite",
                "input_type": "query",
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Embedding generation failed: {resp.text}",
            )
        data = resp.json()
        return data["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# RAG: ask a question
# ---------------------------------------------------------------------------


@router.post("/ask")
async def ask_question(
    body: AskRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """RAG question: embed query → match_help_chunks → LLM answer with sources."""
    supabase = get_supabase()

    # Default roles for filtering
    filter_roles = ["user"]

    try:
        # Generate embedding for the question
        query_embedding = await _create_embedding(body.question)

        # Vector search via RPC
        search_result = supabase.rpc(
            "match_help_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.3,
                "match_count": 5,
                "filter_roles": filter_roles,
            },
        ).execute()

        chunks = search_result.data or []

        # Soft fallback: if no chunks at 0.3, retry with lower threshold
        if not chunks:
            fallback_result = supabase.rpc(
                "match_help_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.15,
                    "match_count": 3,
                    "filter_roles": filter_roles,
                },
            ).execute()
            chunks = fallback_result.data or []

        # Build context from matched chunks
        sources = []
        if chunks:
            context_parts = []
            for chunk in chunks:
                context_parts.append(
                    f"[Source: {chunk['document_title']} > {chunk.get('heading_context', 'General')}]\n{chunk['content']}"
                )
                sources.append({
                    "title": chunk["document_title"],
                    "heading": chunk.get("heading_context", ""),
                    "similarity": round(chunk["similarity"], 3),
                    "file_path": chunk.get("document_file_path", ""),
                })
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = ""

        # Build conversation history if continuing
        history_messages = []
        if body.conversation_id:
            msg_result = (
                supabase.table("help_messages")
                .select("role, content")
                .eq("conversation_id", body.conversation_id)
                .order("created_at")
                .limit(10)
                .execute()
            )
            for msg in msg_result.data or []:
                history_messages.append({"role": msg["role"], "content": msg["content"]})

        # Build system prompt with context
        system_prompt = (
            "You are the Legal AI OS Help Assistant. Legal AI OS is a governed AI platform "
            "for legal enterprises. It provides an independent measurement, governance, and "
            "enablement layer around existing AI tools like Harvey AI.\n\n"
            "## Platform Overview\n\n"
            "Legal AI OS operates across five layers:\n"
            "- Layer 0: Knowledge Foundation (documents, precedents, playbooks)\n"
            "- Layer 1: Governance & Trust (audit trail, explainability, RLS, HITL)\n"
            "- Layer 2: Legal AI Functions (8 POC demos: matter intake, contract review, "
            "employment, due diligence, regulatory, KM, value reporting, maturity)\n"
            "- Layer 3: Program Operations (portfolio dashboard, ROI framework, POC pipeline, "
            "Harvey agent monitoring, enablement kit)\n"
            "- Layer 4: Organizational Model (K&I PM role, interface maps, metrics)\n\n"
            "## Key Facts\n\n"
            "- Harvey Monitor: 4-dimension independent evaluation (Accuracy, Safety, Bias, Compliance). "
            "Tier 1 (Accuracy/Safety/Bias) weighted at 1.5x, Tier 2 (Compliance) at 1.0x. "
            "Hard veto at 75 on any Tier 1 dimension. Certification: Platinum 90+, Gold 85+, "
            "Silver 80+, Bronze 75+.\n"
            "- ROI Framework: cost impact = time saved x billable rate from rate cards. "
            "Quality tracked via accuracy rate, override rate, false positive rate. "
            "Adoption = active users / eligible users.\n"
            "- POC Pipeline: Discovery → Build → Review → Graduated (or Cancelled). "
            "Kanban board with project cards and feedback log.\n"
            "- Governance: every LLM call recorded in append-only audit trail. "
            "RLS-enforced client data isolation. ABA Formal Opinion 512 alignment.\n"
            "- All 8 AI functions follow the same pattern: Input → Router → Evaluator → "
            "Scoring → Audit Trail. The LLM provides reasoning. The system provides judgment.\n\n"
            "## Instructions\n\n"
            "Answer the user's question based on the documentation context below and your "
            "core knowledge above. Be brief — 2-4 sentences max. Use markdown sparingly. "
            "The user can ask follow-up questions if they need more detail. "
            "If the context doesn't contain enough information, use your core knowledge. "
            "Do not make up features or capabilities not described here."
        )

        if context:
            system_prompt += f"\n\n--- Documentation Context ---\n{context}"

        messages = history_messages + [{"role": "user", "content": body.question}]

        # Generate answer using LLMProvider (respects configured provider with fallback)
        llm = LLMProvider()
        response = await llm.call(
            system_prompt=system_prompt,
            user_message=body.question,
            temperature=0.3,
            max_tokens=300,
        )

        answer = response.text

        # Create or continue conversation
        conversation_id = body.conversation_id
        if not conversation_id:
            title = body.question[:80].strip()
            conv_result = (
                supabase.table("help_conversations")
                .insert({
                    "user_id": str(user.id),
                    "title": title,
                })
                .execute()
            )
            if conv_result.data:
                conversation_id = conv_result.data[0]["id"]
            else:
                conversation_id = None

        # Store messages
        if conversation_id:
            supabase.table("help_messages").insert([
                {
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": body.question,
                },
                {
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                },
            ]).execute()

            # Update conversation timestamp
            supabase.table("help_conversations").update({
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", conversation_id).execute()

        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Help ask error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.get("/conversations")
async def list_conversations(user=Depends(get_current_user)):
    """List user's help conversations."""
    supabase = get_supabase()
    result = (
        supabase.table("help_conversations")
        .select("id, title, created_at, updated_at")
        .eq("user_id", str(user.id))
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
    )
    return {"success": True, "conversations": result.data or []}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user=Depends(get_current_user)):
    """Load full conversation with messages."""
    supabase = get_supabase()

    conv_result = (
        supabase.table("help_conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", str(user.id))
        .execute()
    )
    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = (
        supabase.table("help_messages")
        .select("id, role, content, sources, feedback, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    return {
        "success": True,
        "conversation": conv_result.data[0],
        "messages": messages_result.data or [],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user=Depends(get_current_user)):
    """Delete a help conversation."""
    supabase = get_supabase()

    conv_result = (
        supabase.table("help_conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", str(user.id))
        .execute()
    )
    if not conv_result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    supabase.table("help_conversations").delete().eq("id", conversation_id).execute()
    return {"success": True}


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@router.post("/feedback/{message_id}")
async def submit_feedback(message_id: str, body: FeedbackRequest, user=Depends(get_current_user)):
    """Submit thumbs up/down feedback on a help message."""
    if body.feedback not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Feedback must be -1, 0, or 1")

    supabase = get_supabase()

    msg = (
        supabase.table("help_messages")
        .select("conversation_id")
        .eq("id", message_id)
        .single()
        .execute()
    )
    if not msg.data:
        raise HTTPException(status_code=404, detail="Message not found")

    conv = (
        supabase.table("help_conversations")
        .select("id")
        .eq("id", msg.data["conversation_id"])
        .eq("user_id", str(user.id))
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Message not found")

    supabase.table("help_messages").update({"feedback": body.feedback}).eq("id", message_id).execute()
    return {"success": True}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_help(query: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=20)):
    """Direct vector search against help docs (no LLM, just results)."""
    try:
        query_embedding = await _create_embedding(query)
        filter_roles = ["user"]

        result = (
            get_supabase()
            .rpc(
                "match_help_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.3,
                    "match_count": limit,
                    "filter_roles": filter_roles,
                },
            )
            .execute()
        )

        chunks = []
        for chunk in result.data or []:
            chunks.append({
                "content": chunk["content"],
                "title": chunk["document_title"],
                "heading": chunk.get("heading_context", ""),
                "similarity": round(chunk["similarity"], 3),
                "file_path": chunk.get("document_file_path", ""),
            })

        return {"success": True, "results": chunks}

    except Exception as exc:
        logger.error(f"Help search error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Status / health
# ---------------------------------------------------------------------------


@router.get("/status")
async def help_status():
    """Health check: is the help system indexed?"""
    try:
        supabase = get_supabase()
        result = supabase.table("help_chunks").select("id", count="exact").execute()
        chunk_count = result.count or 0
        return {
            "success": True,
            "indexed": chunk_count > 0,
            "chunk_count": chunk_count,
        }
    except Exception as exc:
        return {"success": False, "indexed": False, "error": str(exc)}
