"""
Multi-provider LLM client for the simulation.

Supports:
- Anthropic (Claude models)
- OpenAI-compatible (DeepSeek, GPT-4o, etc.)
- Mock (deterministic, for testing)

All clients share a single interface: callable that takes messages → returns text.
"""

import json
import time
import os
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, Literal


# === USAGE TRACKING ===

@dataclass
class UsageTracker:
    """Tracks token usage and cost across the simulation.

    Thread-safe: the async refactor runs the LLM client inside `asyncio.to_thread`
    worker threads, so `record_*` mutates these counters concurrently. A lock
    serializes the read-modify-write so totals are never lost.
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    api_calls: int = 0
    cost_estimate: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_openai(self, usage, model: str):
        """Record usage from an OpenAI-compatible API response.

        DeepSeek does automatic server-side prefix caching and reports
        `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`. Hits bill at the
        cached rate (~4x cheaper), so pricing all prompt tokens at the miss rate
        overstates cost. Split the prompt tokens and price each bucket correctly."""
        with self._lock:
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            cache_hit = usage.get("prompt_cache_hit_tokens", 0) or 0
            cache_miss = usage.get("prompt_cache_miss_tokens", 0)
            # Fall back to "all miss" when the provider doesn't report the split.
            if not cache_miss and not cache_hit:
                cache_miss = prompt

            self.input_tokens += prompt
            self.output_tokens += completion
            self.cache_read_tokens += cache_hit
            self.api_calls += 1

            input_price, output_price, cache_read_price = _openai_pricing(model)
            self.cost_estimate += (
                cache_miss * input_price +
                cache_hit * cache_read_price +
                completion * output_price
            )

    def record_anthropic(self, usage, model: str):
        """Record usage from an Anthropic API response."""
        with self._lock:
            self.input_tokens += usage.input_tokens
            self.output_tokens += usage.output_tokens
            self.api_calls += 1

            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
            self.cache_read_tokens += cache_read
            self.cache_write_tokens += cache_write

            input_price, output_price, cache_write_mult, cache_read_mult = _anthropic_pricing(model)
            regular_input = usage.input_tokens - cache_read - cache_write
            self.cost_estimate += (
                regular_input * input_price +
                usage.output_tokens * output_price +
                cache_write * input_price * cache_write_mult +
                cache_read * input_price * cache_read_mult
            )

    def summary(self) -> str:
        with self._lock:
            input_tokens, output_tokens = self.input_tokens, self.output_tokens
            cache_read_tokens, cache_write_tokens = self.cache_read_tokens, self.cache_write_tokens
            api_calls, cost_estimate = self.api_calls, self.cost_estimate
        parts = [f"API calls: {api_calls}"]
        if input_tokens:
            parts.append(f"Tokens: {input_tokens:,} in / {output_tokens:,} out")
        if cache_read_tokens or cache_write_tokens:
            parts.append(f"Cache: {cache_read_tokens:,} read / {cache_write_tokens:,} write")
        parts.append(f"Est. cost: ${cost_estimate:.2f}")
        return " | ".join(parts)


def _openai_pricing(model: str) -> tuple[float, float, float]:
    """Return (input_miss_price, output_price, input_cache_hit_price) per token.

    The cache-hit price is the discounted rate DeepSeek bills for prompt tokens
    served from its automatic prefix cache."""
    M = 1_000_000
    model_lower = model.lower()
    # DeepSeek published PEAK rates (per 1M tokens), verified against
    # api-docs.deepseek.com/quick_start/pricing (Aug 2026). Returned as
    # (in_miss, out, in_hit). NOTE: as of 2026-08-16 DeepSeek bills peak/off-peak
    # — off-peak (all hours outside 01:00-04:00 and 06:00-10:00 UTC) is HALF these
    # rates. This table uses peak, so the estimate is a conservative upper bound;
    # a run made entirely off-peak actually costs ~50% of what's shown.
    if "v4-pro" in model_lower or model_lower == "deepseek-pro":
        return (0.435 / M, 0.87 / M, 0.003625 / M)
    elif "v4-flash" in model_lower or "flash" in model_lower:
        return (0.14 / M, 0.28 / M, 0.0028 / M)
    elif "deepseek" in model_lower:
        # Legacy deepseek-chat / V3-era alias (no longer on the pricing page):
        # cache miss $0.27/M, cache HIT $0.07/M, $1.10/M out. Prefer an explicit
        # deepseek-v4-* model so pricing is unambiguous.
        return (0.27 / M, 1.10 / M, 0.07 / M)
    elif "gpt-4o" in model_lower:
        return (2.50 / 1_000_000, 10.00 / 1_000_000, 1.25 / 1_000_000)
    elif "gpt-4.5" in model_lower:
        return (75.00 / 1_000_000, 150.00 / 1_000_000, 37.50 / 1_000_000)
    else:
        return (0.27 / 1_000_000, 1.10 / 1_000_000, 0.07 / 1_000_000)  # default conservative


def _anthropic_pricing(model: str) -> tuple[float, float, float, float]:
    """Return (input, output, cache_write_mult, cache_read_mult) for Anthropic models."""
    model_lower = model.lower()
    if "haiku" in model_lower:
        return (0.25 / 1_000_000, 1.25 / 1_000_000, 1.25, 0.10)
    elif "sonnet" in model_lower:
        return (3.00 / 1_000_000, 15.00 / 1_000_000, 1.25, 0.10)
    elif "opus" in model_lower:
        return (15.00 / 1_000_000, 75.00 / 1_000_000, 1.25, 0.10)
    else:
        return (3.00 / 1_000_000, 15.00 / 1_000_000, 1.25, 0.10)


# === ANTHROPIC CLIENT ===

class AnthropicClient:
    """Thin wrapper around the Anthropic SDK."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20251001",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        import anthropic as anthropic_sdk
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.usage = UsageTracker()

        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            kwargs["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        self.client = anthropic_sdk.Anthropic(**kwargs)

    def __call__(self, messages: list[dict]) -> str:
        system_content, conversation = _split_system_messages(messages)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": conversation,
                }
                if system_content:
                    kwargs["system"] = system_content

                response = self.client.messages.create(**kwargs)
                self.usage.record_anthropic(response.usage, self.model)

                text = ""
                for block in response.content:
                    if block.type == "text":
                        text += block.text
                return text

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

        raise last_error or RuntimeError("Anthropic call failed")


# === OPENAI-COMPATIBLE CLIENT ===

class OpenAIClient:
    """
    OpenAI-compatible client. Works with:
    - DeepSeek (via OpenRouter, DeepSeek direct, or other providers)
    - OpenAI (GPT-4o, GPT-4.5, etc.)
    - Any OpenAI-compatible endpoint

    Configure via:
        OPENAI_API_KEY=...
        OPENAI_BASE_URL=https://api.deepseek.com/v1   # or OpenRouter, etc.
    """

    def __init__(
        self,
        model: str = "deepseek-chat",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
    ):
        from openai import OpenAI as OpenAISDK
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.usage = UsageTracker()

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not resolved_key or resolved_key.startswith("sk-placeholder"):
            raise ValueError(
                "No API key provided. Set OPENAI_API_KEY or DEEPSEEK_API_KEY "
                "environment variable, or pass api_key to create_llm_client()."
            )

        kwargs = {
            "api_key": resolved_key,
            "max_retries": max_retries,
            "timeout": 120.0,  # 2 min per request — prevent hangs
        }
        if base_url:
            kwargs["base_url"] = base_url
        elif "OPENAI_BASE_URL" in os.environ:
            kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]

        self.client = OpenAISDK(**kwargs)

    def __call__(self, messages: list[dict]) -> str:
        system_content, conversation = _split_system_messages(messages)

        # Merge system content into a system message for OpenAI format
        api_messages = []
        if system_content:
            api_messages.append({"role": "system", "content": system_content})
        api_messages.extend(conversation)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": api_messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
                # DeepSeek V4 reasons by DEFAULT: it spends ~1000-1600 hidden
                # reasoning tokens before emitting the answer, which (a) blew past
                # max_tokens=1024 and truncated the JSON (finish_reason=length →
                # ~90% parse failures on the v4 runs), and (b) is output you pay for
                # but never use. These are structured operational decisions, not
                # proofs — the JSON `reasoning` field is the persona rationale we
                # need. So disable thinking: fixes the truncation AND cuts output
                # ~4.4x (1840 → ~420 tokens/call). Verified against v4-pro.
                if "deepseek" in self.model.lower():
                    kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                # Only enforce JSON for OpenAI — DeepSeek support is inconsistent.
                # The decision parser in agents.py extracts JSON from text regardless.
                if "gpt-4" in self.model.lower() or "gpt-3.5" in self.model.lower():
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)

                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    self.usage.record_openai(
                        {
                            "prompt_tokens": u.prompt_tokens,
                            "completion_tokens": u.completion_tokens,
                            # DeepSeek-specific prefix-cache fields (absent on other providers).
                            "prompt_cache_hit_tokens": getattr(u, "prompt_cache_hit_tokens", 0),
                            "prompt_cache_miss_tokens": getattr(u, "prompt_cache_miss_tokens", 0),
                        },
                        self.model,
                    )

                content = response.choices[0].message.content
                return content if content else ""

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

        raise last_error or RuntimeError("OpenAI-compatible call failed")


# === HELPERS ===

def _split_system_messages(messages: list[dict]) -> tuple[Optional[str], list[dict]]:
    """Separate system message from conversation messages."""
    system_content = None
    conversation = []
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            conversation.append(msg)
    return system_content, conversation


# === FACTORY ===

def create_llm_client(
    provider: Literal["deepseek", "anthropic", "openai", "mock"] = "deepseek",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    seed: int = 42,
) -> Callable:
    """
    Create the appropriate LLM client.

    Args:
        provider: "deepseek", "anthropic", "openai", or "mock"
        model: Override default model for provider
        api_key: API key (falls back to env vars)
        base_url: For OpenAI-compatible, override base URL
        max_tokens: Max response tokens
        temperature: 0-1 sampling temperature
        seed: For mock client reproducibility

    Returns:
        Callable: function(messages) -> text

    Env vars used:
        ANTHROPIC_API_KEY — for anthropic provider
        OPENAI_API_KEY — for deepseek/openai providers
        OPENAI_BASE_URL — for deepseek/openai providers
        DEEPSEEK_API_KEY — alias for OPENAI_API_KEY
    """
    # Default model per provider
    if model is None:
        defaults = {
            "deepseek": "deepseek-v4-pro",
            "anthropic": "claude-sonnet-4-5-20251001",
            "openai": "gpt-4o",
            "mock": "mock",
        }
        model = defaults.get(provider, "deepseek-chat")

    if provider == "mock":
        from .agents import MockLLM
        return MockLLM(seed=seed)

    if provider == "anthropic":
        return AnthropicClient(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_key,
        )

    # OpenAI-compatible (deepseek, openai, etc.)
    if provider == "deepseek":
        # Detect DeepSeek API key from multiple possible env vars
        if api_key is None:
            api_key = (
                os.environ.get("DEEPSEEK_API_KEY") or
                os.environ.get("OPENAI_API_KEY")
            )
        # Default DeepSeek base URL if not specified
        if base_url is None:
            base_url = os.environ.get(
                "OPENAI_BASE_URL",
                "https://api.deepseek.com/v1",
            )

    return OpenAIClient(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )


# === COST ESTIMATION ===

def estimate_run_cost(
    sprints: int = 16,
    claims_per_sprint: int = 50,
    agents_per_claim: float = 8.0,
    system_prompt_tokens: int = 1500,
    task_prompt_tokens: int = 800,
    response_tokens: int = 400,
    model: str = "deepseek-chat",
) -> dict:
    """Estimate the cost of a full simulation run."""
    unique_roles = 11
    total_agent_calls = sprints * claims_per_sprint * agents_per_claim * 2  # ×2 tracks

    total_input_tokens = total_agent_calls * (system_prompt_tokens + task_prompt_tokens)
    total_output_tokens = total_agent_calls * response_tokens

    # Detect provider from model name
    model_lower = model.lower()
    if any(m in model_lower for m in ("claude", "anthropic", "haiku", "sonnet", "opus")):
        input_price, output_price, _, _ = _anthropic_pricing(model)
    else:
        input_price, output_price = _openai_pricing(model)

    total_cost = total_input_tokens * input_price + total_output_tokens * output_price

    return {
        "model": model,
        "total_agent_calls": total_agent_calls,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": round(total_cost, 2),
    }
