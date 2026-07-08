"""
Legal AI OS — Regulatory Change Monitor Worker

Polls regulatory sources, extracts structured changes via LLM,
matches to active matters by jurisdiction + practice area.

Callable directly or via BackgroundTasks.
"""

from __future__ import annotations

import json
import re
import asyncio
from datetime import datetime, timezone, date
from uuid import UUID

from app.database import get_supabase
from app.llm import LLMProvider, LLMResponse
from app.services.audit import AuditTrail
from app.config import settings


def poll_all_sources():
    """Poll all active regulatory sources. Called via BackgroundTasks."""
    supabase = get_supabase()

    sources = (
        supabase.table("regulatory_sources")
        .select("*")
        .eq("status", "active")
        .execute()
    )

    results = []
    for source in (sources.data or []):
        try:
            result = process_regulatory_source(source["id"])
            results.append({"source_id": source["id"], "name": source["name"], **result})
        except Exception as e:
            results.append({"source_id": source["id"], "name": source["name"], "error": str(e)})

    # Match to active matters
    match_updates_to_matters()

    return {"sources_polled": len(results), "results": results}


def process_regulatory_source(source_id: str) -> dict:
    """Process a single regulatory source: fetch → extract changes → store."""
    supabase = get_supabase()
    audit = AuditTrail()

    source = supabase.table("regulatory_sources").select("*").eq("id", source_id).execute()
    if not source.data:
        return {"error": "Source not found"}

    source = source.data[0]

    # Update last polled
    supabase.table("regulatory_sources").update({
        "last_polled_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", source_id).execute()

    # Fetch source content (simulated for now — real RSS/API fetching later)
    content = _fetch_source_content(source)
    if not content:
        return {"updates_found": 0, "reason": "no_content"}

    # Extract changes via LLM
    provider = LLMProvider()
    system_prompt = """You are a regulatory analyst. Extract structured regulatory changes from the provided text.

For each change found, return a JSON object with:
{
  "regulation_name": "name of the regulation or rule",
  "regulation_reference": "citation if available (e.g., 17 CFR § 240.14a-8)",
  "change_type": "new_regulation|amendment|repeal|guidance|enforcement_action|court_decision|other",
  "change_summary": "one-paragraph summary of what changed and why it matters",
  "detailed_analysis": "full analysis of the change and its implications",
  "effective_date": "YYYY-MM-DD if mentioned",
  "compliance_deadline": "YYYY-MM-DD if mentioned",
  "affected_industries": ["industry1", "industry2"],
  "affected_practice_areas": ["corporate", "litigation", "employment", "ip", "tax", "regulatory"],
  "keywords": ["keyword1", "keyword2"]
}

Return an array of changes found. If no changes found, return [].
Only include substantive regulatory changes — skip press releases, personnel announcements, and procedural notices."""

    try:
        response: LLMResponse = _call_llm_sync(
            provider,
            system_prompt=system_prompt,
            user_message=f"SOURCE: {source['name']} ({source['agency']})\nJURISDICTION: {source['jurisdiction']}\n\nCONTENT:\n\n{content[:80000]}",
            temperature=0.1,
            max_tokens=4096,
        )
    except Exception as e:
        supabase.table("regulatory_sources").update({
            "status": "error",
            "notes": f"LLM extraction failed: {str(e)}",
        }).eq("id", source_id).execute()
        return {"error": str(e)}

    # Parse structured output
    try:
        changes = json.loads(response.text)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response.text, re.DOTALL)
        if match:
            changes = json.loads(match.group(1))
        else:
            changes = []

    # Store each change
    stored = 0
    for change in changes:
        # De-duplicate: check if we already have this regulation + change type recently
        existing = (
            supabase.table("regulatory_updates")
            .select("id")
            .eq("regulation_name", change.get("regulation_name", ""))
            .eq("change_type", change.get("change_type", "other"))
            .gte("created_at", datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat())
            .execute()
        )
        if existing.data:
            continue  # Skip duplicates

        update_row = {
            "source_id": source_id,
            "regulation_name": change.get("regulation_name", "Unknown"),
            "regulation_reference": change.get("regulation_reference"),
            "jurisdiction": source["jurisdiction"],
            "agency": source["agency"],
            "change_type": change.get("change_type", "other"),
            "change_summary": change.get("change_summary", ""),
            "detailed_analysis": change.get("detailed_analysis"),
            "effective_date": change.get("effective_date"),
            "compliance_deadline": change.get("compliance_deadline"),
            "source_url": change.get("source_url", source["url"]),
            "raw_text": content[:5000],
            "affected_industries": change.get("affected_industries", []),
            "affected_practice_areas": change.get("affected_practice_areas", []),
            "keywords": change.get("keywords", []),
            "model_used": response.model,
            "confidence": 85,  # default confidence for LLM extraction
            "is_processed": False,
        }
        supabase.table("regulatory_updates").insert(update_row).execute()
        stored += 1

    # Update source status
    if stored > 0:
        supabase.table("regulatory_sources").update({
            "last_change_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }).eq("id", source_id).execute()

    return {"updates_found": stored, "tokens_used": response.total_tokens, "cost_usd": response.cost_usd}


def match_updates_to_matters():
    """Match unprocessed regulatory updates to active matters by jurisdiction + practice area."""
    supabase = get_supabase()

    # Get unmatched updates
    updates = (
        supabase.table("regulatory_updates")
        .select("*")
        .eq("is_processed", False)
        .execute()
    )

    # Get active matters
    matters= (
        supabase.table("matters")
        .select("*, clients(id)")
        .in_("status", ["active", "intake", "conflict_check"])
        .execute()
    )

    matched = 0
    for update in (updates.data or []):
        for matter in (matters.data or []):
            # Match by jurisdiction
            if update.get("jurisdiction") != matter.get("jurisdiction"):
                # Check if jurisdiction is a prefix (e.g., "US" matches "US-CA")
                update_jur = update.get("jurisdiction", "")
                matter_jur = matter.get("jurisdiction", "")
                if not (update_jur and matter_jur and
                        (matter_jur.startswith(update_jur) or update_jur.startswith(matter_jur))):
                    continue

            # Match by practice area
            update_pas = update.get("affected_practice_areas") or []
            matter_pa = matter.get("practice_area", "")
            if update_pas and matter_pa:
                pa_match = any(
                    pa.lower() in matter_pa.lower() or matter_pa.lower() in pa.lower()
                    for pa in update_pas
                )
                if not pa_match:
                    continue

            # Determine impact severity based on change type
            severity_map = {
                "new_regulation": "high",
                "amendment": "medium",
                "repeal": "high",
                "guidance": "low",
                "enforcement_action": "critical",
                "court_decision": "high",
                "other": "monitor",
            }
            severity = severity_map.get(update.get("change_type", "other"), "monitor")

            # Check if flag already exists
            existing = (
                supabase.table("matter_regulatory_flags")
                .select("id")
                .eq("matter_id", matter["id"])
                .eq("update_id", update["id"])
                .execute()
            )
            if existing.data:
                continue

            # Create flag
            supabase.table("matter_regulatory_flags").insert({
                "matter_id": matter["id"],
                "update_id": update["id"],
                "client_id": matter.get("clients", {}).get("id") if isinstance(matter.get("clients"), dict) else matter.get("client_id"),
                "impact_severity": severity,
                "impact_summary": f"Regulatory change ({update.get('change_type')}) affecting {matter.get('practice_area', 'your practice area')} matters in {update.get('jurisdiction')}",
                "status": "unreviewed",
            }).execute()
            matched += 1

        # Mark update as processed
        supabase.table("regulatory_updates").update({
            "is_processed": True
        }).eq("id", update["id"]).execute()

    return {"matched": matched}


# ---------------------------------------------------------------------------
# Content fetching (simulated)
# ---------------------------------------------------------------------------

def _fetch_source_content(source: dict) -> str | None:
    """Fetch content from a regulatory source.

    For now, returns simulated content for testing the pipeline.
    Real implementation will use RSS parsing, API calls, or web scraping.
    """
    # Simulated: return a placeholder based on source type
    # In production, this would use httpx to fetch and parse RSS/HTML
    return (
        f"SIMULATED CONTENT from {source['name']} ({source['agency']}) — {source['jurisdiction']}\n\n"
        f"This is placeholder content for testing. In production, this would be the actual "
        f"regulatory text fetched from {source['url']}.\n\n"
        f"Replace with real RSS feed parsing, API calls, or web scraping logic.\n"
    )


def _call_llm_sync(provider: LLMProvider, **kwargs) -> LLMResponse:
    """Blocking wrapper for async LLM call."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(provider.call(**kwargs))
    finally:
        loop.close()
