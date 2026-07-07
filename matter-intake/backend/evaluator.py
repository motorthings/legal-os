"""
Two-stage LLM pipeline for matter intake evaluation.

Stage 1 — Router: classify matter into practice area
Stage 2 — Evaluator: score across 5 dimensions
Post-processing: programmatic weighted scoring (never trust LLM scores)

Supports both Anthropic and OpenAI-compatible (DeepSeek, OpenAI) APIs.
Auto-detects provider from API key prefix:
  - sk-ant-... → Anthropic
  - sk-...     → OpenAI-compatible (DeepSeek by default)
"""

import json
import os
import time
from typing import Any

from logger import get_logger

log = get_logger("evaluator")

# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))

if LLM_API_KEY.startswith("sk-ant-"):
    PROVIDER = "anthropic"
    PROVIDER_MODEL_DEFAULT = "claude-sonnet-4-6"
else:
    PROVIDER = "openai"
    PROVIDER_MODEL_DEFAULT = "deepseek-chat"

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com" if PROVIDER == "openai" else "")

log.info("init", extra={
    "event_type": "init",
    "context": None,
    "data": {"provider": PROVIDER, "base_url": LLM_BASE_URL},
    "duration_ms": 0,
})

# ---------------------------------------------------------------------------
# Configuration (with provider-appropriate defaults)
# ---------------------------------------------------------------------------
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", PROVIDER_MODEL_DEFAULT)
ROUTER_TEMPERATURE = float(os.environ.get("ROUTER_TEMPERATURE", "0.1"))
ROUTER_MAX_TOKENS = int(os.environ.get("ROUTER_MAX_TOKENS", "1000"))

EVALUATOR_MODEL = os.environ.get("EVALUATOR_MODEL", PROVIDER_MODEL_DEFAULT)
EVALUATOR_TEMPERATURE = float(os.environ.get("EVALUATOR_TEMPERATURE", "0.2"))
EVALUATOR_MAX_TOKENS = int(os.environ.get("EVALUATOR_MAX_TOKENS", "4000"))

LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120.0"))
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "1"))


# ---------------------------------------------------------------------------
# Lazy client singletons
# ---------------------------------------------------------------------------
_anthropic_client: Any = None
_openai_client: Any = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(
            api_key=LLM_API_KEY,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
        )
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
        )
    return _openai_client


# ---------------------------------------------------------------------------
# Unified LLM call — hides provider differences
# ---------------------------------------------------------------------------
async def _llm_call(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str, int, int]:
    """
    Call the LLM and return (response_text, tokens_in, tokens_out).
    Handles both Anthropic and OpenAI-compatible APIs transparently.
    """
    if PROVIDER == "anthropic":
        client = _get_anthropic_client()
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        )
        # Extract text — skip thinking blocks if present
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
                break
        if not text:
            text = response.content[0].text
        return text, response.usage.input_tokens, response.usage.output_tokens
    else:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        text = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        return text, tokens_in, tokens_out


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(name: str) -> str:
    with open(os.path.join(PROMPTS_DIR, name)) as f:
        return f.read()


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------
def extract_json(response_text: str) -> dict[str, Any]:
    """
    Three-way detection for JSON in LLM responses:
    1. ```json ... ```
    2. ``` ... ```
    3. Raw JSON (no code fence)
    """
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        return json.loads(response_text[start:end].strip())
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        return json.loads(response_text[start:end].strip())
    else:
        return json.loads(response_text.strip())


# ---------------------------------------------------------------------------
# Performance timer
# ---------------------------------------------------------------------------
class PipelineTimer:
    """Track timing per pipeline stage using monotonic clock."""

    def __init__(self):
        self.stages: dict[str, float] = {}
        self._start = time.monotonic()

    def record(self, stage: str) -> None:
        self.stages[stage] = time.monotonic()

    def elapsed(self, stage: str) -> int:
        return int((self.stages.get(stage, self._start) - self._start) * 1000)

    def total_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)


# ---------------------------------------------------------------------------
# Stage 1: Router — classify matter into practice area
# ---------------------------------------------------------------------------
async def run_router(matter_summary: str) -> dict[str, Any]:
    """Classify matter into practice area. Returns parsed JSON or safe default."""
    system_prompt = load_prompt("ROUTER_SYSTEM.txt")
    try:
        start = time.monotonic()
        text, tokens_in, tokens_out = await _llm_call(
            system_prompt=system_prompt,
            user_message=matter_summary,
            model=ROUTER_MODEL,
            max_tokens=ROUTER_MAX_TOKENS,
            temperature=ROUTER_TEMPERATURE,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        result = extract_json(text)
        log.info(
            "llm_call",
            extra={
                "event_type": "llm_call",
                "context": {"stage": "router", "provider": PROVIDER},
                "data": {
                    "model": ROUTER_MODEL,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                },
                "duration_ms": duration_ms,
            },
        )
        return result
    except Exception as e:
        log.info(
            "error",
            extra={
                "event_type": "error",
                "context": {"stage": "router", "provider": PROVIDER},
                "data": {"error": str(e)},
                "duration_ms": 0,
            },
        )
        return {
            "practice_area": "Other (unclassified)",
            "confidence": 0,
            "reasoning": f"Router failed: {str(e)}",
            "key_signals": [],
            "matter_type": "other",
            "jurisdiction": None,
            "urgency_indicators": [],
        }


# ---------------------------------------------------------------------------
# Stage 2: Evaluator — score across 5 dimensions
# ---------------------------------------------------------------------------
async def run_evaluator(
    matter_summary: str, router_result: dict[str, Any]
) -> dict[str, Any]:
    """Score matter across 5 dimensions. Returns parsed JSON or safe default."""
    system_prompt = load_prompt("EVALUATOR_SYSTEM.txt")

    enriched_prompt = (
        f"Matter Summary:\n{matter_summary}\n\n"
        f"Router Classification: {router_result.get('practice_area', 'Unknown')}\n"
        f"Router Confidence: {router_result.get('confidence', 0)}/100\n"
        f"Router Reasoning: {router_result.get('reasoning', 'N/A')}\n"
        f"Matter Type: {router_result.get('matter_type', 'other')}\n"
        f"Jurisdiction: {router_result.get('jurisdiction', 'Not specified')}\n"
        f"Urgency Indicators: {', '.join(router_result.get('urgency_indicators', [])) or 'None'}"
    )

    try:
        start = time.monotonic()
        text, tokens_in, tokens_out = await _llm_call(
            system_prompt=system_prompt,
            user_message=enriched_prompt,
            model=EVALUATOR_MODEL,
            max_tokens=EVALUATOR_MAX_TOKENS,
            temperature=EVALUATOR_TEMPERATURE,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        result = extract_json(text)
        log.info(
            "llm_call",
            extra={
                "event_type": "llm_call",
                "context": {"stage": "evaluator", "provider": PROVIDER},
                "data": {
                    "model": EVALUATOR_MODEL,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                },
                "duration_ms": duration_ms,
            },
        )
        return result
    except Exception as e:
        log.info(
            "error",
            extra={
                "event_type": "error",
                "context": {"stage": "evaluator", "provider": PROVIDER},
                "data": {"error": str(e)},
                "duration_ms": 0,
            },
        )
        return {
            "practice_area": {
                "practice_area": router_result.get("practice_area", "Unknown"),
                "confidence": router_result.get("confidence", 0),
                "reasoning": f"Evaluator failed: {str(e)}",
            },
            "urgency_risk": {
                "urgency_level": "routine",
                "risk_level": "medium",
                "risk_score": 50,
                "reasoning": f"Evaluator failed: {str(e)}",
            },
            "conflict_check": {
                "entity_name": None,
                "conflict_type": "none_identified",
                "detail": "Evaluation unavailable due to processing error",
            },
            "staffing": {
                "recommended_role": "TBD",
                "estimated_hours": 0,
                "reasoning": "Evaluation unavailable due to processing error",
            },
            "data_integrity": {
                "completeness": 0,
                "clarity": 0,
                "issues": ["Evaluation pipeline error"],
            },
        }


# ---------------------------------------------------------------------------
# Programmatic scoring (NEVER trust LLM's own scores)
# ---------------------------------------------------------------------------
def calculate_overall_score(
    router_result: dict[str, Any],
    evaluator_result: dict[str, Any],
) -> tuple[int, str, list[dict[str, Any]]]:
    """
    Programmatic weighted scoring across 5 dimensions.

    Weights:
      1. Practice Area Classification Accuracy — 25%
      2. Urgency & Risk Assessment — 25%
      3. Conflict Check Completeness — 20%
      4. Staffing Recommendation Quality — 15%
      5. Client/Matter Data Integrity — 15%

    Returns (overall_score, risk_level, dimension_scores).
    """
    dimensions: list[dict[str, Any]] = []

    # 1. Practice Area Classification Accuracy (25%)
    pa_confidence = router_result.get("confidence", 0)
    pa_eval = evaluator_result.get("practice_area", {})
    dimensions.append(
        {
            "dimension_name": "Practice Area Classification",
            "score": pa_confidence,
            "weight": 0.25,
            "reasoning": pa_eval.get("reasoning", router_result.get("reasoning", "")),
        }
    )

    # 2. Urgency & Risk Assessment (25%)
    urgency_data = evaluator_result.get("urgency_risk", {})
    llm_risk = urgency_data.get("risk_score", 50)
    inverted_risk = max(0, min(100, 100 - llm_risk))
    dimensions.append(
        {
            "dimension_name": "Urgency & Risk Assessment",
            "score": inverted_risk,
            "weight": 0.25,
            "reasoning": urgency_data.get("reasoning", ""),
        }
    )

    # 3. Conflict Check Completeness (20%)
    conflict_data = evaluator_result.get("conflict_check", {})
    conflict_type = conflict_data.get("conflict_type", "none_identified")
    if conflict_type == "direct_adverse":
        conflict_score = 90
    elif conflict_type == "business_conflict":
        conflict_score = 75
    else:
        conflict_score = 60
    dimensions.append(
        {
            "dimension_name": "Conflict Check Completeness",
            "score": conflict_score,
            "weight": 0.20,
            "reasoning": conflict_data.get("detail", ""),
        }
    )

    # 4. Staffing Recommendation Quality (15%)
    staffing = evaluator_result.get("staffing", {})
    has_role = bool(
        staffing.get("recommended_role")
        and staffing.get("recommended_role") != "TBD"
    )
    has_hours = bool(staffing.get("estimated_hours", 0) > 0)
    if has_role and has_hours:
        staffing_score = 85
    elif has_role:
        staffing_score = 65
    else:
        staffing_score = 40
    dimensions.append(
        {
            "dimension_name": "Staffing Recommendation Quality",
            "score": staffing_score,
            "weight": 0.15,
            "reasoning": staffing.get("reasoning", ""),
        }
    )

    # 5. Client/Matter Data Integrity (15%)
    integrity = evaluator_result.get("data_integrity", {})
    completeness = integrity.get("completeness", 0)
    clarity = integrity.get("clarity", 0)
    integrity_score = (completeness + clarity) // 2
    issues = integrity.get("issues", [])
    reasoning = (
        "; ".join(issues) if issues else "No data integrity issues identified"
    )
    dimensions.append(
        {
            "dimension_name": "Data Integrity",
            "score": integrity_score,
            "weight": 0.15,
            "reasoning": reasoning,
        }
    )

    overall_score = round(sum(d["score"] * d["weight"] for d in dimensions))

    if overall_score >= 70:
        risk_level = "low"
    elif overall_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "high"

    return overall_score, risk_level, dimensions
