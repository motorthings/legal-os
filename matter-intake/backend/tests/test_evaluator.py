"""Tests for the two-stage evaluator pipeline."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from evaluator import (
    PipelineTimer,
    calculate_overall_score,
    extract_json,
    run_evaluator,
    run_router,
)


def _mock_llm_response(json_data: dict) -> AsyncMock:
    """Create a mock for _llm_call that returns JSON data."""

    async def mock_call(**kwargs):
        return json.dumps(json_data), 500, 300

    return AsyncMock(side_effect=mock_call)


class TestExtractJson:
    def test_json_fenced(self):
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_bare_fenced(self):
        text = '```\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_raw_json(self):
        text = '{"key": "value"}'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        text = '```json\n{"outer": {"inner": [1, 2, 3]}}\n```'
        result = extract_json(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}


class TestPipelineTimer:
    def test_records_stages(self):
        import time

        timer = PipelineTimer()
        time.sleep(0.01)
        timer.record("router")
        assert timer.elapsed("router") > 0
        assert timer.total_ms() > 0

    def test_total_ms_increases(self):
        import time

        timer = PipelineTimer()
        t1 = timer.total_ms()
        time.sleep(0.01)
        t2 = timer.total_ms()
        assert t2 >= t1


class TestCalculateOverallScore:
    def test_full_scoring(self, mock_router_response, mock_evaluator_response):
        overall, risk_level, dimensions = calculate_overall_score(
            mock_router_response, mock_evaluator_response
        )

        assert 0 <= overall <= 100
        assert risk_level in ("high", "medium", "low")
        assert len(dimensions) == 5

        names = [d["dimension_name"] for d in dimensions]
        assert "Practice Area Classification" in names
        assert "Urgency & Risk Assessment" in names
        assert "Conflict Check Completeness" in names
        assert "Staffing Recommendation Quality" in names
        assert "Data Integrity" in names

        total_weight = sum(d["weight"] for d in dimensions)
        assert abs(total_weight - 1.0) < 0.01

    def test_scoring_formula(self, mock_router_response, mock_evaluator_response):
        overall, risk_level, dimensions = calculate_overall_score(
            mock_router_response, mock_evaluator_response
        )

        # PA: 92*0.25 + UR: 55*0.25 + CC: 75*0.20 + SR: 85*0.15 + DI: 77*0.15
        expected = round(
            92 * 0.25 + 55 * 0.25 + 75 * 0.20 + 85 * 0.15 + 77 * 0.15
        )
        assert overall == expected
        assert risk_level == "low"

    def test_high_risk_matter(self, mock_router_response):
        router = {**mock_router_response, "confidence": 20}
        evaluator = {
            "practice_area": {
                "practice_area": "Unknown",
                "confidence": 20,
                "reasoning": "Unclear",
            },
            "urgency_risk": {
                "urgency_level": "immediate",
                "risk_level": "high",
                "risk_score": 90,
                "reasoning": "CRITICAL",
            },
            "conflict_check": {
                "entity_name": None,
                "conflict_type": "none_identified",
                "detail": "",
            },
            "staffing": {
                "recommended_role": "TBD",
                "estimated_hours": 0,
                "reasoning": "",
            },
            "data_integrity": {
                "completeness": 10,
                "clarity": 10,
                "issues": ["Nearly empty summary"],
            },
        }
        overall, risk_level, _ = calculate_overall_score(router, evaluator)
        assert risk_level == "high"
        assert overall < 40

    def test_all_perfect_scores(self, mock_router_response):
        router = {**mock_router_response, "confidence": 100}
        evaluator = {
            "practice_area": {
                "practice_area": "Corporate M&A",
                "confidence": 100,
                "reasoning": "Perfect",
            },
            "urgency_risk": {
                "urgency_level": "routine",
                "risk_level": "low",
                "risk_score": 0,
                "reasoning": "No risk",
            },
            "conflict_check": {
                "entity_name": "Rival Inc",
                "conflict_type": "direct_adverse",
                "detail": "Identified",
            },
            "staffing": {
                "recommended_role": "Partner + 3 Associates",
                "estimated_hours": 500,
                "reasoning": "Detailed",
            },
            "data_integrity": {
                "completeness": 100,
                "clarity": 100,
                "issues": [],
            },
        }
        overall, risk_level, _ = calculate_overall_score(router, evaluator)
        assert risk_level == "low"
        assert overall >= 85


class TestRunRouter:
    @pytest.mark.asyncio
    async def test_router_success(self, mock_router_response):
        """Router returns parsed JSON on successful LLM call."""
        mock_llm = _mock_llm_response(mock_router_response)
        with patch("evaluator._llm_call", mock_llm):
            result = await run_router("Test matter summary about M&A acquisition")
            assert result["practice_area"] == "Corporate M&A"
            assert result["confidence"] == 92
            assert "key_signals" in result

    @pytest.mark.asyncio
    async def test_router_failure_returns_safe_default(self):
        """Router returns safe default when LLM call fails."""
        mock_llm = AsyncMock(side_effect=Exception("API error"))
        with patch("evaluator._llm_call", mock_llm):
            result = await run_router("Test matter")
            assert result["practice_area"] == "Other (unclassified)"
            assert result["confidence"] == 0


class TestRunEvaluator:
    @pytest.mark.asyncio
    async def test_evaluator_success(
        self, mock_router_response, mock_evaluator_response
    ):
        """Evaluator returns parsed JSON on successful LLM call."""
        mock_llm = _mock_llm_response(mock_evaluator_response)
        with patch("evaluator._llm_call", mock_llm):
            result = await run_evaluator("Test matter", mock_router_response)
            assert "urgency_risk" in result
            assert "conflict_check" in result
            assert "staffing" in result
            assert "data_integrity" in result

    @pytest.mark.asyncio
    async def test_evaluator_failure_returns_safe_default(
        self, mock_router_response
    ):
        """Evaluator returns safe default when LLM call fails."""
        mock_llm = AsyncMock(side_effect=Exception("API timeout"))
        with patch("evaluator._llm_call", mock_llm):
            result = await run_evaluator("Test matter", mock_router_response)
            assert result["urgency_risk"]["urgency_level"] == "routine"
            assert result["staffing"]["recommended_role"] == "TBD"
            assert result["data_integrity"]["completeness"] == 0
