"""
Legal AI OS — Due Diligence Document Processor

Process a single document through the DD pipeline:
  1. Extract text from storage
  2. Load target standards for the project
  3. Compare each clause against target standards via LLM
  4. Programmatic severity scoring
  5. Store deviations + audit trail + metrics

Callable directly (FastAPI BackgroundTasks) or via Celery (when Redis is added).
"""

from __future__ import annotations

import json
import re
import asyncio
from uuid import UUID

from app.database import get_supabase
from app.llm import LLMProvider, LLMResponse
from app.services.audit import AuditTrail
from app.services.metrics import MetricsCollector
from app.config import settings


def process_dd_document(document_id: str, initiated_by: str) -> dict:
    """
    Process a single document synchronously. Called via FastAPI BackgroundTasks.

    Returns a summary dict: {document_id, deviations_found, critical, high, tokens_used, cost_usd}
    """
    supabase = get_supabase()
    audit = AuditTrail()
    metrics = MetricsCollector()

    # ------------------------------------------------------------------
    # 1. Load document
    # ------------------------------------------------------------------
    doc_result = (
        supabase.table("dd_documents")
        .select("*, dd_projects!inner(*)")
        .eq("id", document_id)
        .execute()
    )
    if not doc_result.data:
        raise ValueError(f"Document {document_id} not found")

    doc = doc_result.data[0]
    project = doc["dd_projects"]
    client_id = UUID(doc["client_id"])
    project_id = UUID(doc["project_id"])
    function_id = _get_dd_function_id(supabase)

    # Mark as extracting
    supabase.table("dd_documents").update({"status": "extracting"}).eq("id", document_id).execute()

    # Download from storage and extract text
    try:
        file_data = supabase.storage.from_("documents").download(doc["storage_path"])
        text = _extract_text(file_data, doc["filename"])
    except Exception as e:
        supabase.table("dd_documents").update({
            "status": "error",
            "error_message": f"Extraction failed: {str(e)}",
        }).eq("id", document_id).execute()
        raise

    # Store extracted text
    supabase.table("dd_documents").update({
        "extracted_text": text,
        "extracted_at": "now()",
        "status": "analyzing",
    }).eq("id", document_id).execute()

    # ------------------------------------------------------------------
    # 2. Load target standards
    # ------------------------------------------------------------------
    standards_result = (
        supabase.table("dd_target_standards")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("is_active", True)
        .execute()
    )
    target_standards = standards_result.data or []

    if not target_standards:
        supabase.table("dd_documents").update({
            "status": "error",
            "error_message": "No target standards defined for this project",
        }).eq("id", document_id).execute()
        return {"status": "error", "reason": "no_target_standards"}

    # ------------------------------------------------------------------
    # 3. Per-standard analysis via LLM
    # ------------------------------------------------------------------
    metrics.start(
        client_id=client_id,
        function_id=function_id,
        initiated_by=UUID(initiated_by),
        practice_group_id=UUID(project["practice_group_id"]),
    )

    provider = LLMProvider()

    # Build analysis prompt
    standards_text = "\n\n".join(
        f"STANDARD [{ts['category']}] (severity: {ts['severity']}):\n"
        f"Expected: {ts.get('standard_text', 'N/A')}\n"
        f"Acceptable: {', '.join(ts.get('acceptable_values', []) or [])}"
        for ts in target_standards
    )

    system_prompt = """You are a legal due diligence analyst. Review the document text against the target standards below.

For EACH standard:
- Find the relevant clause in the document (or note if missing)
- Compare against the target standard
- Flag deviations with severity and detailed reasoning
- Recommend a fix if applicable

Return a JSON array of deviations found:
[{
    "clause_type": "indemnification",
    "clause_text": "actual text from document",
    "clause_location": "Section 4.2",
    "deviation_summary": "one-line description of gap",
    "detailed_analysis": "full reasoning",
    "recommendation": "suggested fix",
    "severity": "critical|high|medium|low|info",
    "confidence": 0-100
}]

If a standard is fully met, do not include it in the output.
If a standard's clause is entirely missing, flag it as critical with clause_text: "CLAUSE MISSING"."""

    try:
        response: LLMResponse = _call_llm_sync(
            provider,
            system_prompt=system_prompt,
            user_message=f"TARGET STANDARDS:\n\n{standards_text}\n\n---\n\nDOCUMENT TEXT:\n\n{text[:120000]}",
            temperature=0.1,
            max_tokens=8192,
        )
    except Exception as e:
        supabase.table("dd_documents").update({
            "status": "error",
            "error_message": f"LLM analysis failed: {str(e)}",
        }).eq("id", document_id).execute()
        raise

    # Parse structured output
    try:
        deviations_raw = json.loads(response.text)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response.text, re.DOTALL)
        if match:
            deviations_raw = json.loads(match.group(1))
        else:
            deviations_raw = []

    # ------------------------------------------------------------------
    # 4. Programmatic severity scoring
    # ------------------------------------------------------------------
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    for dev in deviations_raw:
        # Rule: missing required clause → always critical
        if dev.get("clause_text") == "CLAUSE MISSING":
            dev["severity"] = "critical"

        # Rule: low confidence → escalate severity
        if dev.get("confidence", 100) < settings.auto_escalation_confidence:
            current_idx = severity_order.get(dev["severity"], 2)
            dev["severity"] = list(severity_order.keys())[max(0, current_idx - 1)]

        # Generate clause grouping key
        clause_identity = f"{dev.get('clause_type', '')}|{dev.get('clause_text', '')[:100]}"
        dev["clause_group_key"] = str(hash(clause_identity))

    # ------------------------------------------------------------------
    # 5. Store deviations + audit
    # ------------------------------------------------------------------
    audit_entry = audit.record_llm_call(
        client_id=client_id,
        function_id=function_id,
        initiated_by=UUID(initiated_by),
        system_prompt=system_prompt,
        user_message=f"Document: {doc['filename']}",
        llm_response=response,
    )

    for dev in deviations_raw:
        deviation_row = {
            "document_id": document_id,
            "project_id": str(project_id),
            "client_id": str(client_id),
            "clause_type": dev.get("clause_type", "unknown"),
            "clause_text": dev.get("clause_text"),
            "clause_location": dev.get("clause_location"),
            "deviation_summary": dev.get("deviation_summary"),
            "detailed_analysis": dev.get("detailed_analysis"),
            "recommendation": dev.get("recommendation"),
            "severity": dev.get("severity", "medium"),
            "clause_group_key": dev.get("clause_group_key"),
            "confidence": dev.get("confidence", 0),
            "audit_trail_id": audit_entry.get("id"),
            "model_used": response.model,
        }
        supabase.table("dd_deviations").insert(deviation_row).execute()

    # ------------------------------------------------------------------
    # 6. Update document status + project counts
    # ------------------------------------------------------------------
    supabase.table("dd_documents").update({
        "status": "analyzed",
        "analyzed_at": "now()",
    }).eq("id", document_id).execute()

    # Count deviations for this document
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for d in deviations_raw:
        sev = d.get("severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Update project-level counts
    project_devs = (
        supabase.table("dd_deviations")
        .select("id, severity")
        .eq("project_id", str(project_id))
        .execute()
    )

    supabase.table("dd_projects").update({
        "deviation_count": len(project_devs.data) if project_devs.data else 0,
        "critical_count": sum(1 for d in (project_devs.data or []) if d.get("severity") == "critical"),
    }).eq("id", str(project_id)).execute()

    # Check if all docs are done → mark project ready for review
    pending = (
        supabase.table("dd_documents")
        .select("id")
        .eq("project_id", str(project_id))
        .not_.in_("status", ["analyzed", "reviewed", "error"])
        .execute()
    )
    if not pending.data:
        supabase.table("dd_projects").update({"status": "review"}).eq("id", str(project_id)).execute()

    # Metrics
    metrics.finish(
        llm_response=response,
        human_time_equivalent_ms=54_000_000,  # 15 hours per BUILD_PLAN baseline
        result_quality="flag" if deviations_raw else "pass",
    )

    return {
        "document_id": document_id,
        "deviations_found": len(deviations_raw),
        "critical": severity_counts["critical"],
        "high": severity_counts["high"],
        "tokens_used": response.total_tokens,
        "cost_usd": response.cost_usd,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_dd_function_id(supabase) -> UUID:
    result = supabase.table("functions").select("id").eq("slug", "due-diligence").execute()
    if result.data:
        return UUID(result.data[0]["id"])
    raise ValueError("Due diligence function not registered")


def _extract_text(file_data: bytes, filename: str) -> str:
    """Extract text from uploaded file."""
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(file_data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    elif ext == "docx":
        from docx import Document
        from io import BytesIO
        doc = Document(BytesIO(file_data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == "txt":
        return file_data.decode("utf-8", errors="replace")

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _call_llm_sync(provider: LLMProvider, **kwargs) -> LLMResponse:
    """Blocking wrapper for async LLM call."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(provider.call(**kwargs))
    finally:
        loop.close()
