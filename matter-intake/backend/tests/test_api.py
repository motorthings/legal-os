"""Integration tests for the /api/evaluate endpoint."""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["LLM_API_KEY"] = "sk-test-fake-key"

from main import app


def _make_mock_llm(router_json: dict, evaluator_json: dict):
    """Create a mock _llm_call that returns router data on 1st call, evaluator on 2nd."""
    call_count = [0]

    async def mock_call(**kwargs):
        call_count[0] += 1
        text = json.dumps(router_json if call_count[0] == 1 else evaluator_json)
        return text, 500, 300

    return AsyncMock(side_effect=mock_call)


@pytest.fixture
def mock_pipeline(mock_router_response, mock_evaluator_response):
    return _make_mock_llm(mock_router_response, mock_evaluator_response)


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /health returns ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_evaluate_success(mock_pipeline):
    """POST /api/evaluate returns 200 with full EvaluateResponse."""
    with patch("evaluator._llm_call", mock_pipeline):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/evaluate",
                json={
                    "matter_summary": "Acquisition of TargetCo by Acme Corp, $500M stock-for-stock, HSR filing required."
                },
            )
            assert response.status_code == 200
            data = response.json()

            assert "overall_score" in data
            assert "overall_risk_level" in data
            assert data["overall_risk_level"] in ("high", "medium", "low")

            assert "practice_area" in data
            assert data["practice_area"]["practice_area"] == "Corporate M&A"

            assert "urgency_risk" in data
            assert "conflict_check" in data
            assert data["conflict_check"]["conflict_type"] in (
                "direct_adverse",
                "business_conflict",
                "none_identified",
            )

            assert "staffing" in data
            assert "data_integrity" in data
            assert "dimension_scores" in data
            assert len(data["dimension_scores"]) == 5

            assert "processing_time_ms" in data
            assert "model_used" in data


@pytest.mark.asyncio
async def test_evaluate_empty_summary():
    """POST /api/evaluate with empty string returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/evaluate", json={"matter_summary": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_evaluate_missing_field():
    """POST /api/evaluate with no body returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/evaluate", json={})
        assert response.status_code == 422
