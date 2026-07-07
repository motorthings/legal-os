"""API routes for the Matter Intake Evaluator."""

import json
import os
import subprocess
import tempfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from database import (
    get_all_settings,
    get_audit_trail,
    get_distinct_practice_areas,
    get_evaluation,
    get_setting,
    list_evaluations,
    save_evaluation,
    set_setting,
)
from evaluator import (
    EVALUATOR_MODEL,
    ROUTER_MODEL,
    PipelineTimer,
    calculate_overall_score,
    load_prompt,
    run_evaluator,
    run_router,
)
from logger import get_logger
from models import EvaluateRequest, EvaluateResponse

log = get_logger("api")
router = APIRouter(prefix="/api", tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_matter(request: EvaluateRequest):
    timer = PipelineTimer()

    log.info("evaluation_start", extra={
        "event_type": "evaluation_start", "context": None,
        "data": {"summary_length": len(request.matter_summary)}, "duration_ms": 0,
    })

    # Capture raw inputs for audit trail
    router_prompt = load_prompt("ROUTER_SYSTEM.txt")
    router_raw_input = f"SYSTEM:\n{router_prompt}\n\nUSER:\n{request.matter_summary}"

    # Stage 1: Router
    router_result = await run_router(request.matter_summary)
    router_raw_output = json.dumps(router_result, indent=2)
    timer.record("router")

    # Build evaluator prompt (same as in run_evaluator)
    evaluator_prompt = load_prompt("EVALUATOR_SYSTEM.txt")
    enriched = (
        f"Matter Summary:\n{request.matter_summary}\n\n"
        f"Router Classification: {router_result.get('practice_area', 'Unknown')}\n"
        f"Router Confidence: {router_result.get('confidence', 0)}/100\n"
        f"Router Reasoning: {router_result.get('reasoning', 'N/A')}"
    )
    evaluator_raw_input = f"SYSTEM:\n{evaluator_prompt}\n\nUSER:\n{enriched}"

    # Stage 2: Evaluator
    evaluator_result = await run_evaluator(request.matter_summary, router_result)
    evaluator_raw_output = json.dumps(evaluator_result, indent=2)
    timer.record("evaluator")

    # Programmatic scoring
    overall_score, risk_level, dimensions = calculate_overall_score(
        router_result, evaluator_result
    )
    timer.record("scoring")

    # Build response
    pa_data = evaluator_result.get("practice_area", {})
    response = EvaluateResponse(
        overall_score=overall_score,
        overall_risk_level=risk_level,
        practice_area={
            "practice_area": pa_data.get("practice_area", router_result.get("practice_area", "Unknown")),
            "confidence": pa_data.get("confidence", router_result.get("confidence", 0)),
            "reasoning": pa_data.get("reasoning", router_result.get("reasoning", "")),
        },
        urgency_risk=evaluator_result.get("urgency_risk", {}),
        conflict_check=evaluator_result.get("conflict_check", {}),
        staffing=evaluator_result.get("staffing", {}),
        data_integrity=evaluator_result.get("data_integrity", {}),
        dimension_scores=dimensions,
        processing_time_ms=timer.total_ms(),
        model_used=f"{ROUTER_MODEL} / {EVALUATOR_MODEL}",
    )

    # Persist with full audit trail + rubrics snapshot
    response_dict = response.model_dump()
    try:
        # Capture current rubric settings for audit trail versioning
        rubrics = await get_all_settings()

        row_id = await save_evaluation(
            matter_summary=request.matter_summary,
            response_json=response_dict,
            router_raw_input=router_raw_input,
            router_raw_output=router_raw_output,
            evaluator_raw_input=evaluator_raw_input,
            evaluator_raw_output=evaluator_raw_output,
            dimension_scores=dimensions,
            rubrics_snapshot=rubrics,
        )
        response_dict["id"] = row_id
    except Exception as e:
        log.info("db_error", extra={
            "event_type": "error", "context": {"stage": "save"},
            "data": {"error": str(e)}, "duration_ms": 0,
        })

    log.info("evaluation_complete", extra={
        "event_type": "evaluation_complete", "context": None,
        "data": {"overall_score": overall_score, "risk_level": risk_level},
        "duration_ms": timer.total_ms(),
    })

    return response


# ---------------------------------------------------------------------------
# File upload — extract text via markitdown
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept a matter document (PDF, DOCX, etc.) and return extracted text."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read into memory (capped)
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    suffix = os.path.splitext(file.filename)[1] or ".tmp"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        result = subprocess.run(
            ["markitdown", tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=422,
                detail=f"File extraction failed: {result.stderr.strip() or 'unknown error'}",
            )

        text = result.stdout.strip()
        if not text:
            raise HTTPException(status_code=422, detail="File appears to be empty or unreadable")

        return {
            "success": True,
            "filename": file.filename,
            "text": text,
            "length": len(text),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=422, detail="File extraction timed out")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@router.get("/evaluations")
async def get_evaluations(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default=""),
    risk_level: str = Query(default=""),
    practice_area: str = Query(default=""),
    urgency_level: str = Query(default=""),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
):
    try:
        rows, total = await list_evaluations(
            limit=limit,
            offset=offset,
            search=search,
            risk_level=risk_level,
            practice_area=practice_area,
            urgency_level=urgency_level,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"success": True, "evaluations": rows, "count": len(rows), "total": total}
    except Exception as e:
        return {"success": False, "error": str(e), "evaluations": [], "count": 0, "total": 0}


@router.get("/evaluations/{eval_id}")
async def get_evaluation_detail(eval_id: int):
    record = await get_evaluation(eval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"success": True, "evaluation": record}


@router.get("/evaluations/{eval_id}/audit")
async def get_audit(eval_id: int):
    """Full audit trail — every decision, raw prompt, raw response, reasoning chain."""
    trail = await get_audit_trail(eval_id)
    if not trail:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"success": True, "audit_trail": trail}


# ---------------------------------------------------------------------------
# Filters / metadata
# ---------------------------------------------------------------------------

@router.get("/filters/practice-areas")
async def get_practice_areas():
    """Distinct practice areas seen so far — for filter dropdowns."""
    try:
        areas = await get_distinct_practice_areas()
        return {"success": True, "practice_areas": areas}
    except Exception as e:
        return {"success": False, "error": str(e), "practice_areas": []}


# ---------------------------------------------------------------------------
# Settings (teams, rubrics, API configuration)
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_settings():
    try:
        settings = await get_all_settings()
        return {"success": True, "settings": settings}
    except Exception as e:
        return {"success": False, "error": str(e), "settings": {}}


@router.get("/settings/{key}")
async def get_setting_value(key: str):
    value = await get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"success": True, "key": key, "value": json.loads(value)}


@router.put("/settings/{key}")
async def update_setting(key: str, body: dict):
    await set_setting(key, json.dumps(body.get("value")))
    return {"success": True, "key": key}
