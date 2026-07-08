"""
Legal AI OS — KM & Precedent Intelligence API

Semantic search across all firm documents. "Have we done this before?" with citations.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_supabase, get_pool
from app.auth import get_current_user, User
from app.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def km_health():
    return {
        "function": "km-intelligence",
        "status": "healthy",
        "version": "0.1.0",
        "capabilities": [
            "semantic_search",
            "precedent_matching",
            "document_ingestion",
            "practice_area_filtering",
            "citation_linking",
            "embedding_similarity",
        ],
    }


@router.get("/metrics")
async def km_metrics():
    supabase = get_supabase()
    result = supabase.table("knowledge_documents").select("id", count="exact").execute()
    return {
        "function": "km-intelligence",
        "documents_indexed": result.count if hasattr(result, "count") else 0,
    }


@router.get("/targets")
async def km_targets():
    return {
        "function": "km-intelligence",
        "targets": {
            "search_latency_ms": "< 500",
            "recall_at_10": "> 0.90",
            "documents_indexed": "all firm documents",
            "embedding_dimension": settings.embedding_dimension,
        },
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search")
async def semantic_search(
    q: str = Query(..., min_length=3, description="Search query"),
    user: User = Depends(get_current_user),
    document_type: str | None = None,
    practice_area: str | None = None,
    limit: int = Query(default=10, le=50),
):
    """Semantic search across all knowledge documents for the user's client.

    Uses pgvector cosine similarity on Voyage AI embeddings.
    Falls back to text search if embeddings not available.
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Generate query embedding via Voyage AI
    query_embedding = await _embed_query(q)

    if query_embedding:
        # pgvector similarity search via asyncpg
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, document_type, source_url, source_file,
                           chunk_count, metadata, version,
                           1 - (embedding <=> $1) AS similarity
                    FROM knowledge_documents
                    WHERE client_id = $2
                      AND is_active = true
                      AND embedding IS NOT NULL
                      AND 1 - (embedding <=> $1) > $5
                    ORDER BY embedding <=> $1
                    LIMIT $3
                    OFFSET $4
                    """,
                    str(query_embedding),
                    str(user.client_id),
                    limit,
                    0,
                    settings.similarity_threshold,
                )
                results = [dict(r) for r in rows]
                return {"query": q, "results": results, "method": "semantic"}
        except Exception:
            pass  # Fall through to text search

    # Fallback: text search on raw_text
    result = (
        supabase.table("knowledge_documents")
        .select("id, title, document_type, source_url, source_file, chunk_count, metadata, version")
        .eq("client_id", str(user.client_id))
        .eq("is_active", True)
        .ilike("raw_text", f"%{q}%")
        .limit(limit)
        .execute()
    )
    return {"query": q, "results": result.data or [], "method": "text_fallback"}


@router.get("/search/similar/{document_id}")
async def find_similar(
    document_id: UUID,
    user: User = Depends(get_current_user),
    limit: int = Query(default=5, le=20),
):
    """Find documents similar to a given document (by embedding similarity)."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Get source document embedding
    doc = supabase.table("knowledge_documents").select("embedding, title").eq("id", str(document_id)).execute()
    if not doc.data or not doc.data[0].get("embedding"):
        raise HTTPException(status_code=404, detail="Document not found or has no embedding")

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, document_type, source_url, source_file,
                       1 - (embedding <=> $1) AS similarity
                FROM knowledge_documents
                WHERE client_id = $2
                  AND id != $3
                  AND is_active = true
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $4
                """,
                doc.data[0]["embedding"],
                str(user.client_id),
                str(document_id),
                limit,
            )
        return {
            "source_document": doc.data[0]["title"],
            "similar": [dict(r) for r in rows],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


# ---------------------------------------------------------------------------
# Documents CRUD
# ---------------------------------------------------------------------------

@router.get("/documents")
async def list_documents(
    user: User = Depends(get_current_user),
    document_type: str | None = None,
    practice_group_id: UUID | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """List knowledge documents for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    query = (
        get_supabase()
        .table("knowledge_documents")
        .select("id, title, document_type, source_url, source_file, chunk_count, is_active, version, created_at")
        .eq("client_id", str(user.client_id))
        .order("created_at", desc=True)
        .limit(limit)
        .offset(offset)
    )
    if document_type:
        query = query.eq("document_type", document_type)
    if practice_group_id:
        query = query.eq("practice_group_id", str(practice_group_id))

    result = query.execute()
    return result.data or []


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID):
    """Get a single knowledge document with full text."""
    result = (
        get_supabase()
        .table("knowledge_documents")
        .select("*")
        .eq("id", str(document_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return result.data[0]


@router.post("/documents/ingest", status_code=201)
async def ingest_document(
    data: dict,
    user: User = Depends(get_current_user),
):
    """Ingest a document into the knowledge base with embedding generation."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    title = data.get("title", "Untitled")
    text = data.get("text", "")
    doc_type = data.get("document_type", "memo")
    source_url = data.get("source_url")
    source_file = data.get("source_file")

    # Generate embedding
    embedding = await _embed_text(text[:8000])  # Voyage has ~8K token context

    # Chunk count estimate (~800 chars per chunk)
    chunk_count = max(1, len(text) // 800)

    result = (
        get_supabase()
        .table("knowledge_documents")
        .insert({
            "client_id": str(user.client_id),
            "practice_group_id": str(data.get("practice_group_id")) if data.get("practice_group_id") else None,
            "title": title,
            "document_type": doc_type,
            "source_url": source_url,
            "source_file": source_file,
            "raw_text": text,
            "chunk_count": chunk_count,
            "metadata": data.get("metadata", {}),
            "embedding": embedding,
            "created_by": str(user.id),
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to ingest document")
    return result.data[0]


@router.delete("/documents/{document_id}")
async def deactivate_document(document_id: UUID, user: User = Depends(get_current_user)):
    """Soft-delete a document (set is_active=false)."""
    result = (
        get_supabase()
        .table("knowledge_documents")
        .update({"is_active": False})
        .eq("id", str(document_id))
        .eq("client_id", str(user.client_id))
        .execute()
    )
    return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def km_stats(user: User = Depends(get_current_user)):
    """Get KM statistics: document counts by type, practice area."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    docs = (
        supabase.table("knowledge_documents")
        .select("document_type, is_active")
        .eq("client_id", str(user.client_id))
        .execute()
    )

    by_type: dict = {}
    total = 0
    active = 0
    for d in (docs.data or []):
        total += 1
        if d.get("is_active"):
            active += 1
        dt = d.get("document_type", "unknown")
        by_type[dt] = by_type.get(dt, 0) + 1

    return {
        "total_documents": total,
        "active_documents": active,
        "by_type": by_type,
    }


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

async def _embed_query(query: str) -> list[float] | None:
    """Generate embedding for a search query via Voyage AI."""
    import asyncio
    try:
        return await asyncio.to_thread(_embed_sync, query, "query")
    except Exception:
        return None


async def _embed_text(text: str) -> list[float] | None:
    """Generate embedding for document text via Voyage AI."""
    import asyncio
    try:
        return await asyncio.to_thread(_embed_sync, text, "document")
    except Exception:
        return None


def _embed_sync(text: str, input_type: str = "document") -> list[float] | None:
    """Synchronous Voyage AI embedding call."""
    import voyageai
    vo = voyageai.Client()
    result = vo.embed(text, model=settings.voyage_model, input_type=input_type)
    return result.embeddings[0] if result.embeddings else None
