"""Test fixtures and mocks for the Matter Intake Evaluator."""

import os
import sys

import pytest

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test env vars — use a non-Anthropic key to trigger OpenAI provider path
os.environ["LLM_API_KEY"] = "sk-test-fake-key"

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Sample matter summaries (canned inputs)
# ---------------------------------------------------------------------------

@pytest.fixture
def matter_corporate_ma() -> str:
    return _read_fixture("matter_corporate_m_a.txt")


@pytest.fixture
def matter_litigation() -> str:
    return _read_fixture("matter_litigation.txt")


@pytest.fixture
def matter_ip_patent() -> str:
    return _read_fixture("matter_ip_patent.txt")


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_router_response() -> dict:
    return {
        "practice_area": "Corporate M&A",
        "confidence": 92,
        "reasoning": "Clear acquisition structure with equity consideration and HSR filing requirement",
        "key_signals": ["stock-for-stock", "acquisition", "shareholder approval", "HSR filing"],
        "matter_type": "transactional",
        "jurisdiction": "Delaware",
        "urgency_indicators": ["Q3 2026 closing", "regulatory filing required"],
    }


@pytest.fixture
def mock_evaluator_response() -> dict:
    return {
        "practice_area": {
            "practice_area": "Corporate M&A",
            "confidence": 92,
            "reasoning": "Classic M&A structure with cross-border complexity",
        },
        "urgency_risk": {
            "urgency_level": "short-term",
            "risk_level": "medium",
            "risk_score": 45,
            "reasoning": "Regulatory filing deadline within 60 days, $500M transaction has significant financial stakes",
        },
        "conflict_check": {
            "entity_name": "Acme Corp",
            "conflict_type": "business_conflict",
            "detail": "Firm previously represented a competitor in the same industry sector",
        },
        "staffing": {
            "recommended_role": "Partner + 2 Senior Associates",
            "estimated_hours": 250,
            "reasoning": "Complex cross-border transaction requiring senior M&A oversight and regulatory expertise",
        },
        "data_integrity": {
            "completeness": 75,
            "clarity": 80,
            "issues": [
                "Counterparty valuation details not specified",
                "Specific jurisdictions beyond Delaware not listed",
            ],
        },
    }
