"""
Environment variable configuration for the Matter Intake Evaluator.

Provider auto-detection from API key prefix:
  - sk-ant-... → Anthropic (default model: claude-sonnet-4-6)
  - sk-...     → OpenAI-compatible (default model: deepseek-chat, base URL: api.deepseek.com)

Override with LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL env vars.
"""

import os

# CORS (allow all origins for demo)
CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "*").split(",")
