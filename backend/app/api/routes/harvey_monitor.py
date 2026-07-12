"""Harvey Agent Monitoring API — agent registry, evaluation, drift detection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.config import settings
from app.database import get_supabase
from app.services.harvey_evaluator import evaluate_harvey_output, run_drift_check
from app.services.scoring import calculate_weighted_score

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentCreate(BaseModel):
    name: str
    agent_type: str
    harvey_agent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    evaluation_schedule: str = "weekly"
    client_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    evaluation_schedule: Optional[str] = None
    status: Optional[str] = None


class EvaluationRequest(BaseModel):
    harvey_agent_id: str
    user_prompt: str
    harvey_response: str
    context: Optional[str] = None
    is_drift_check: bool = False


class DriftCheckRequest(BaseModel):
    harvey_agent_id: str
    harvey_response: str


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

@router.get("/agents")
async def list_agents(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """List registered Harvey agents, optionally filtered."""
    supabase = get_supabase()
    query = supabase.table("harvey_agents").select("*").order("created_at", desc=True)

    if client_id:
        query = query.eq("client_id", client_id)
    if status:
        query = query.eq("status", status)
    if agent_type:
        query = query.eq("agent_type", agent_type)

    result = query.execute()
    return {"agents": result.data, "count": len(result.data)}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user=Depends(get_current_user)):
    """Get a single Harvey agent by ID."""
    supabase = get_supabase()
    result = supabase.table("harvey_agents").select("*").eq("id", agent_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.data[0]


@router.post("/agents")
async def create_agent(body: AgentCreate, user=Depends(get_current_user)):
    """Register a new Harvey agent for monitoring."""
    supabase = get_supabase()
    result = supabase.table("harvey_agents").insert({
        "name": body.name,
        "agent_type": body.agent_type,
        "harvey_agent_id": body.harvey_agent_id,
        "system_prompt": body.system_prompt,
        "evaluation_schedule": body.evaluation_schedule,
        "client_id": body.client_id,
        "status": "active",
    }).execute()
    return result.data[0] if result.data else {}


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdate, user=Depends(get_current_user)):
    """Update a Harvey agent's monitoring configuration."""
    supabase = get_supabase()
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.system_prompt is not None:
        updates["system_prompt"] = body.system_prompt
    if body.evaluation_schedule is not None:
        updates["evaluation_schedule"] = body.evaluation_schedule
    if body.status is not None:
        updates["status"] = body.status

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table("harvey_agents").update(updates).eq("id", agent_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.data[0]


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, user=Depends(get_current_user)):
    """Remove a Harvey agent from monitoring."""
    supabase = get_supabase()
    supabase.table("harvey_agents").delete().eq("id", agent_id).execute()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

@router.post("/evaluate")
async def run_evaluation(body: EvaluationRequest, user=Depends(get_current_user)):
    """Run a 4-dimension evaluation on a Harvey agent output.

    Evaluates Accuracy, Safety, Bias, and Compliance in parallel.
    Applies weighted scoring with veto logic.
    Stores full evaluation record.
    """
    supabase = get_supabase()

    # Verify agent exists
    agent_result = supabase.table("harvey_agents").select("*").eq("id", body.harvey_agent_id).execute()
    if not agent_result.data:
        raise HTTPException(status_code=404, detail="Harvey agent not found")

    agent = agent_result.data[0]

    # Run evaluation (tries Anthropic first for quality, falls back to configured provider)
    eval_result = await evaluate_harvey_output(
        user_prompt=body.user_prompt,
        harvey_response=body.harvey_response,
        context=body.context,
        fallback_provider=settings.llm_provider,
    )

    # Store evaluation record
    record = {
        "harvey_agent_id": body.harvey_agent_id,
        "client_id": agent.get("client_id"),
        "user_prompt": body.user_prompt,
        "harvey_response": body.harvey_response,
        "evaluation_context": body.context,
        "accuracy_score": eval_result["accuracy_score"],
        "safety_score": eval_result["safety_score"],
        "bias_score": eval_result["bias_score"],
        "compliance_score": eval_result["compliance_score"],
        "final_score": eval_result["final_score"],
        "certification_level": eval_result["certification_level"],
        "veto_triggered": eval_result["veto_triggered"],
        "accuracy_report": eval_result["accuracy_report"],
        "safety_report": eval_result["safety_report"],
        "bias_report": eval_result["bias_report"],
        "compliance_report": eval_result["compliance_report"],
        "evaluation_time_ms": eval_result["evaluation_time_ms"],
        "is_drift_check": body.is_drift_check,
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    db_result = supabase.table("harvey_evaluations").insert(record).execute()

    return {
        "evaluation": db_result.data[0] if db_result.data else record,
        "scores": {
            "accuracy": eval_result["accuracy_score"],
            "safety": eval_result["safety_score"],
            "bias": eval_result["bias_score"],
            "compliance": eval_result["compliance_score"],
            "final": eval_result["final_score"],
            "certification": eval_result["certification_level"],
            "veto_triggered": eval_result["veto_triggered"],
        },
    }


@router.get("/evaluations")
async def list_evaluations(
    harvey_agent_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """List evaluation runs, optionally filtered by agent."""
    supabase = get_supabase()
    query = supabase.table("harvey_evaluations").select("*").order("created_at", desc=True).limit(limit)

    if harvey_agent_id:
        query = query.eq("harvey_agent_id", harvey_agent_id)

    result = query.execute()
    return {"evaluations": result.data, "count": len(result.data)}


@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(evaluation_id: str, user=Depends(get_current_user)):
    """Get a single evaluation with full reports."""
    supabase = get_supabase()
    result = supabase.table("harvey_evaluations").select("*").eq("id", evaluation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Drift Detection
# ---------------------------------------------------------------------------

@router.post("/drift-check")
async def check_drift(body: DriftCheckRequest, user=Depends(get_current_user)):
    """Run a drift check comparing current Harvey output against agent baseline."""
    supabase = get_supabase()

    agent_result = supabase.table("harvey_agents").select("*").eq("id", body.harvey_agent_id).execute()
    if not agent_result.data:
        raise HTTPException(status_code=404, detail="Harvey agent not found")

    agent = agent_result.data[0]
    if not agent.get("system_prompt"):
        raise HTTPException(status_code=400, detail="Agent has no baseline system prompt for drift comparison")

    drift_result = await run_drift_check(
        agent_id=body.harvey_agent_id,
        agent_system_prompt=agent["system_prompt"],
        harvey_response=body.harvey_response,
        fallback_provider=settings.llm_provider,
    )

    # Store as evaluation with drift flag
    if drift_result.get("drift_score") is not None:
        eval_record = {
            "harvey_agent_id": body.harvey_agent_id,
            "client_id": agent.get("client_id"),
            "harvey_response": body.harvey_response,
            "final_score": drift_result.get("drift_score"),
            "is_drift_check": True,
            "drift_score": drift_result.get("drift_score"),
            "drift_details": drift_result.get("drift_metadata"),
            "synthesis_report": drift_result.get("drift_report"),
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("harvey_evaluations").insert(eval_record).execute()

        # Create alert if significant drift
        drift_score = drift_result["drift_score"]
        if drift_score >= 51:
            severity = "critical" if drift_score >= 76 else "high" if drift_score >= 60 else "moderate"
            alert = {
                "harvey_agent_id": body.harvey_agent_id,
                "drift_score": drift_score,
                "severity": severity,
                "summary": f"Drift score {drift_score}/100 — {severity} severity",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            supabase.table("harvey_drift_alerts").insert(alert).execute()

    return drift_result


@router.get("/drift-alerts")
async def list_drift_alerts(
    harvey_agent_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """List drift alerts, optionally filtered."""
    supabase = get_supabase()
    query = supabase.table("harvey_drift_alerts").select("*").order("created_at", desc=True).limit(limit)

    if harvey_agent_id:
        query = query.eq("harvey_agent_id", harvey_agent_id)
    if severity:
        query = query.eq("severity", severity)
    if acknowledged is not None:
        query = query.eq("acknowledged", acknowledged)

    result = query.execute()
    return {"alerts": result.data, "count": len(result.data)}


@router.post("/drift-alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user=Depends(get_current_user)):
    """Acknowledge a drift alert."""
    supabase = get_supabase()
    result = supabase.table("harvey_drift_alerts").update({
        "acknowledged": True,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", alert_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def get_monitoring_summary(
    client_id: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """Get a summary of all Harvey monitoring activity for the dashboard."""
    supabase = get_supabase()

    # Agent counts
    agent_query = supabase.table("harvey_agents").select("id, status, agent_type")
    if client_id:
        agent_query = agent_query.eq("client_id", client_id)
    agents = agent_query.execute().data or []

    active_agents = [a for a in agents if a["status"] == "active"]

    # Recent evaluations
    eval_query = supabase.table("harvey_evaluations").select("id, final_score, certification_level, created_at, harvey_agent_id").order("created_at", desc=True).limit(50)
    if client_id:
        eval_query = eval_query.eq("client_id", client_id)
    evaluations = eval_query.execute().data or []

    # Active drift alerts
    alert_query = supabase.table("harvey_drift_alerts").select("id, severity, summary, created_at").eq("acknowledged", False).order("created_at", desc=True)
    if client_id:
        # Drift alerts don't have direct client_id — filter via agent
        agent_ids = [a["id"] for a in agents]
        if agent_ids:
            alert_query = alert_query.in_("harvey_agent_id", agent_ids)
        else:
            alert_query = alert_query.eq("harvey_agent_id", "none")  # force empty

    alerts = alert_query.execute().data or []

    # Average scores
    avg_scores = {"accuracy": None, "safety": None, "bias": None, "compliance": None, "final": None}
    non_drift_evals = [e for e in evaluations if not e.get("is_drift_check")]
    if non_drift_evals:
        recent_eval_ids = [e["id"] for e in non_drift_evals[:20]]
        # Get full records for averages
        score_sums = {"accuracy_score": 0, "safety_score": 0, "bias_score": 0, "compliance_score": 0, "final_score": 0}
        score_counts = {k: 0 for k in score_sums}
        for e in non_drift_evals:
            for key in score_sums:
                val = e.get(key)
                if val is not None:
                    score_sums[key] += val
                    score_counts[key] += 1
        for key in score_sums:
            if score_counts[key] > 0:
                short_key = key.replace("_score", "")
                avg_scores[short_key] = round(score_sums[key] / score_counts[key], 1)

    return {
        "agents": {
            "total": len(agents),
            "active": len(active_agents),
            "by_type": _count_by(agents, "agent_type"),
            "by_status": _count_by(agents, "status"),
        },
        "evaluations": {
            "total_recent": len(evaluations),
            "non_drift": len(non_drift_evals),
            "average_scores": avg_scores,
        },
        "alerts": {
            "unacknowledged": len(alerts),
            "by_severity": _count_by(alerts, "severity"),
        },
    }


def _count_by(items: list[dict], key: str) -> dict[str, int]:
    """Count items by a key value."""
    counts: dict[str, int] = {}
    for item in items:
        val = item.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts
