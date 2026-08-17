"""
Legal AI OS — Matters

Create a matter, then auto-enrich it with Descrybe (run research on the
matter's jurisdiction, practice area, and adverse parties).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, User
from app.database import get_supabase

router = APIRouter()


def _default_practice_group_id(client_id: UUID) -> str | None:
    result = (
        get_supabase()
        .table("practice_groups")
        .select("id")
        .eq("client_id", str(client_id))
        .limit(1)
        .execute()
    )
    return result.data[0]["id"] if result.data else None


@router.post("/matters")
async def create_matter(data: dict, user: User = Depends(get_current_user)):
    """
    Create a matter and auto-enrich it with Descrybe research.

    Body: {name, description?, jurisdiction?, practice_area?, adverse_parties?,
           risk_level?, risk_score?, practice_group_id?}
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    practice_group_id = data.get("practice_group_id") or _default_practice_group_id(user.client_id)
    if not practice_group_id:
        raise HTTPException(status_code=400, detail="No practice group available for this client")

    row = {
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "created_by": str(user.id),
        "name": name,
        "description": data.get("description"),
        "jurisdiction": data.get("jurisdiction"),
        "practice_area": data.get("practice_area"),
        "adverse_parties": data.get("adverse_parties") or [],
        "risk_level": data.get("risk_level"),
        "risk_score": data.get("risk_score"),
        "confidence": data.get("confidence"),
    }

    result = get_supabase().table("matters").insert(row).execute()
    matter = result.data[0]
    matter_id = matter["id"]

    # Auto-enrich with Descrybe (best-effort — never blocks the response on failure)
    from app.services.matter_enrichment import enrich_matter

    try:
        enrichment = await enrich_matter(matter_id=matter_id, initiated_by=user.id)
    except Exception as e:
        enrichment = {"error": str(e)}

    return {"matter": matter, "enrichment": enrichment}
