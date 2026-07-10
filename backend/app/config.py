"""
Legal AI OS — Configuration

All settings loaded from environment variables with sensible defaults.
Uses pydantic-settings for validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "legal-os"
    app_env: str = "development"                # development | staging | production
    debug: bool = True
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    supabase_url: str = ""
    supabase_service_role_key: str = ""         # backend-only (bypasses RLS)
    supabase_anon_key: str = ""                 # public (respects RLS)

    # ------------------------------------------------------------------
    # PostgreSQL (direct connection for asyncpg/pgvector)
    # ------------------------------------------------------------------
    database_url: str = ""                      # postgresql://user:pass@host:5432/db

    # ------------------------------------------------------------------
    # Redis (Celery broker + result backend)
    # ------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # LLM Providers
    # ------------------------------------------------------------------
    # DeepSeek (default — best cost/performance, ~10x cheaper than Claude)
    deepseek_api_key: Optional[str] = None
    deepseek_default_model: str = "deepseek-chat"   # deepseek-chat (V3) or deepseek-reasoner (R1)
    deepseek_base_url: str = "https://api.deepseek.com"

    # Anthropic (fallback for critical/high-risk analysis)
    anthropic_api_key: Optional[str] = None
    anthropic_default_model: str = "claude-sonnet-4-6"

    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None

    aws_bedrock_region: Optional[str] = None
    aws_bedrock_model: Optional[str] = None

    # Default provider: "deepseek" | "anthropic" | "azure_openai" | "bedrock"
    llm_provider: str = "deepseek"

    # Per-function provider overrides (comma-separated slug=provider pairs)
    # Example: "due-diligence=anthropic" forces DD to use Claude for critical docs
    # Leave empty to use llm_provider for everything
    llm_provider_overrides: str = ""

    # ------------------------------------------------------------------
    # Embeddings (Voyage AI)
    # ------------------------------------------------------------------
    voyage_api_key: Optional[str] = None
    voyage_model: str = "voyage-3-large"        # 1024 dimensions
    embedding_dimension: int = 1024

    # ------------------------------------------------------------------
    # RAG / Knowledge Base
    # ------------------------------------------------------------------
    chunk_size: int = 800
    chunk_overlap: int = 200
    max_chunks_per_query: int = 20
    similarity_threshold: float = 0.75

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    celery_task_time_limit: int = 900            # 15 min hard limit
    celery_task_soft_time_limit: int = 600       # 10 min soft limit
    celery_max_retries: int = 3
    celery_retry_backoff: int = 60               # seconds

    # ------------------------------------------------------------------
    # Governance thresholds
    # ------------------------------------------------------------------
    auto_escalation_confidence: int = 70         # escalate if confidence < this
    mandatory_review_risk_level: str = "high"    # force human review for this risk

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://legal.sickofancy.ai",
        "https://legal-os.vercel.app",
        "https://*.vercel.app",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}


settings = Settings()
