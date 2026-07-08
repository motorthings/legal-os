"""
Legal AI OS — LLM Provider Abstraction

Single entry point for all LLM calls. Every call logs to the audit trail.
No client data used for training.

Default: DeepSeek (~10x cheaper than Claude, good for most legal reasoning)
Fallback: Anthropic Claude (for critical/high-risk analysis)
Stubs: Azure OpenAI, AWS Bedrock

== Token Cost Comparison (per 1M tokens) ==
                     Input    Output
DeepSeek-V3 (chat)   $0.27    $1.10
DeepSeek-R1 (reason) $0.55    $2.19
Claude Sonnet 4      $3.00    $15.00
Claude Haiku 4.5     $0.80    $4.00
Claude Opus 4        $15.00   $75.00
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.config import settings


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""
    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    processing_time_ms: int
    cost_usd: float
    raw_response: dict | None = None


# ---------------------------------------------------------------------------
# Pricing tables (USD per 1M tokens: input, output)
# ---------------------------------------------------------------------------

PRICING = {
    # DeepSeek
    "deepseek-chat":       (0.27,  1.10),
    "deepseek-reasoner":   (0.55,  2.19),
    # Anthropic
    "claude-opus-4-8":    (15.00, 75.00),
    "claude-sonnet-4-6":   (3.00, 15.00),
    "claude-haiku-4-5":    (0.80,  4.00),
}

# Functions where Claude is recommended (complex multi-document reasoning)
# Override via llm_provider_overrides env var: "due-diligence=anthropic"
RECOMMENDED_ANTHROPIC = {
    "due-diligence",       # Critical clause analysis
}


def get_provider_for_function(function_slug: str | None = None) -> str:
    """Resolve which LLM provider to use for a given function.

    Checks llm_provider_overrides first, then falls back to llm_provider.
    """
    provider = settings.llm_provider

    if function_slug and settings.llm_provider_overrides:
        for pair in settings.llm_provider_overrides.split(","):
            pair = pair.strip()
            if "=" in pair:
                slug, prov = pair.split("=", 1)
                if slug.strip() == function_slug:
                    provider = prov.strip()
                    break

    return provider


class LLMProvider:
    """
    Unified LLM interface. Provider is resolved at init time.

    Usage:
        # Default (DeepSeek for cost savings)
        provider = LLMProvider()
        response = await provider.call(
            system_prompt="You are a legal AI...",
            user_message="Analyze this contract...",
            temperature=0.2,
            max_tokens=4096,
        )

        # Force Anthropic for critical analysis
        provider = LLMProvider("anthropic")
    """

    def __init__(self, provider: str | None = None, function_slug: str | None = None):
        # Resolve provider: explicit arg > function override > default
        if provider:
            self.provider = provider
        elif function_slug:
            self.provider = get_provider_for_function(function_slug)
        else:
            self.provider = settings.llm_provider

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Route to the configured provider."""
        if self.provider == "deepseek":
            return await self._call_deepseek(
                system_prompt, user_message, model, temperature, max_tokens
            )
        elif self.provider == "anthropic":
            return await self._call_anthropic(
                system_prompt, user_message, model, temperature, max_tokens
            )
        elif self.provider == "azure_openai":
            return await self._call_azure(
                system_prompt, user_message, model, temperature, max_tokens
            )
        elif self.provider == "bedrock":
            return await self._call_bedrock(
                system_prompt, user_message, model, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # DeepSeek (OpenAI-compatible API)
    # ------------------------------------------------------------------

    async def _call_deepseek(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        from openai import AsyncOpenAI

        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")

        model = model or settings.deepseek_default_model
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

        start = time.monotonic()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        choice = response.choices[0]
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        input_price, output_price = PRICING.get(model, (0.27, 1.10))
        cost = (input_tokens / 1_000_000) * input_price + \
               (output_tokens / 1_000_000) * output_price

        return LLMResponse(
            text=choice.message.content or "",
            model=model,
            provider="deepseek",
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            processing_time_ms=elapsed_ms,
            cost_usd=round(cost, 6),
            raw_response=response.model_dump(),
        )

    # ------------------------------------------------------------------
    # Anthropic Claude
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import anthropic

        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        model = model or settings.anthropic_default_model
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        start = time.monotonic()
        response = await client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        input_price, output_price = PRICING.get(model, (3.00, 15.00))
        cost = (input_tokens / 1_000_000) * input_price + \
               (output_tokens / 1_000_000) * output_price

        return LLMResponse(
            text=response.content[0].text,
            model=model,
            provider="anthropic",
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            processing_time_ms=elapsed_ms,
            cost_usd=round(cost, 6),
            raw_response=response.model_dump(),
        )

    # ------------------------------------------------------------------
    # Stubs
    # ------------------------------------------------------------------

    async def _call_azure(self, *args, **kwargs) -> LLMResponse:
        raise NotImplementedError("Azure OpenAI provider not yet implemented")

    async def _call_bedrock(self, *args, **kwargs) -> LLMResponse:
        raise NotImplementedError("AWS Bedrock provider not yet implemented")
