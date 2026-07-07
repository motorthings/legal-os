"""
Application Configuration Constants
Centralizes magic numbers and configuration values for better maintainability.

This module extracts hardcoded values from across the codebase into
documented, type-safe configuration classes.
"""

import os
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunkingConfig:
    """
    Configuration for document text chunking.

    Text chunking splits large documents into smaller, semantically coherent
    chunks for vector embedding and search.
    """

    # Default chunk size in characters
    # Rationale: 800 chars ≈ 200 tokens, optimal for embedding models
    DEFAULT_CHUNK_SIZE: int = 800

    # Overlap between chunks to maintain context
    # Rationale: 200 chars ensures sentence continuity across chunks
    DEFAULT_OVERLAP: int = 200

    # Threshold for sentence boundary detection (0.0-1.0)
    # Rationale: Only use boundaries in last 20% of chunk to avoid too-small chunks
    SENTENCE_BOUNDARY_THRESHOLD: float = 0.8

    # Maximum characters per token (rough estimate for English)
    # Rationale: Used for cost estimation, English averages 4 chars/token
    MAX_CHARS_PER_TOKEN: int = 4


@dataclass(frozen=True)
class EmbeddingConfig:
    """
    Configuration for vector embedding generation.

    Controls how documents are converted to vector embeddings for semantic search.
    """

    # Batch size for embedding API calls
    # Rationale: 100 texts per batch balances API efficiency with memory usage
    DEFAULT_BATCH_SIZE: int = 100

    # Voyage AI model to use
    # Rationale: voyage-3 provides best quality-to-cost ratio
    MODEL_NAME: str = "voyage-3"

    # Cost per million tokens (USD)
    # Rationale: Current Voyage AI pricing as of 2025
    COST_PER_MILLION_TOKENS: float = 0.02

    # Maximum concurrent embedding batches
    # Rationale: Prevents rate limiting and memory exhaustion
    MAX_CONCURRENT_BATCHES: int = 5

    # Input type for document embeddings
    INPUT_TYPE_DOCUMENT: str = "document"

    # Input type for query embeddings
    INPUT_TYPE_QUERY: str = "query"


@dataclass(frozen=True)
class SearchConfig:
    """
    Configuration for semantic search and vector similarity.

    Controls how similar documents are retrieved from the knowledge base.
    """

    # Similarity thresholds by query type (0.0-1.0 cosine similarity)
    # Higher values = more strict matching
    SIMILARITY_THRESHOLDS: Dict[str, float] = None

    # Default similarity threshold (fallback)
    DEFAULT_SIMILARITY: float = 0.0

    # Default search result limit
    DEFAULT_LIMIT: int = 5

    # Maximum search result limit
    MAX_LIMIT: int = 50

    def __post_init__(self):
        # Initialize SIMILARITY_THRESHOLDS if not provided
        if self.SIMILARITY_THRESHOLDS is None:
            object.__setattr__(self, 'SIMILARITY_THRESHOLDS', {
                # Factual queries need high precision (exact matches)
                'factual': 0.50,
                # Exploratory queries can be more lenient (related concepts)
                'exploratory': 0.40,
                # Default for unspecified query types
                'default': 0.0
            })


@dataclass(frozen=True)
class RateLimits:
    """
    Rate limiting configuration for API endpoints.

    Prevents abuse and ensures fair resource allocation.
    """

    # Chat endpoint: 20 requests per minute
    # Rationale: Balance between UX and API cost control
    CHAT: str = "20/minute"

    # Document upload: 10 per minute
    # Rationale: Resource-intensive operation, needs stricter limit
    DOCUMENTS: str = "10/minute"

    # Document listing: 30 per minute
    DOCUMENTS_LIST: str = "30/minute"

    # Conversation operations: 30 per minute
    CONVERSATIONS: str = "30/minute"

    # KPI endpoints: 30 per minute
    KPIS: str = "30/minute"

    # OAuth operations: 10 per minute
    OAUTH: str = "10/minute"

    # Admin operations: 100 per minute
    ADMIN: str = "100/minute"


@dataclass(frozen=True)
class FileLimits:
    """
    File upload limits and validation rules.

    Ensures safe and reasonable file handling.
    """

    # Maximum file size in megabytes
    # Rationale: Balance between usability and storage costs
    MAX_SIZE_MB: int = 50

    # Maximum file size in bytes (calculated)
    @property
    def MAX_SIZE_BYTES(self) -> int:
        return self.MAX_SIZE_MB * 1024 * 1024

    # Allowed file extensions for upload
    ALLOWED_EXTENSIONS: Set[str] = frozenset({
        # Documents
        'pdf', 'docx', 'doc', 'txt',
        # Spreadsheets
        'xlsx', 'xls', 'csv',
        # Presentations
        'pptx', 'ppt',
        # Other
        'md', 'rtf'
    })

    # MIME type mappings
    MIME_TYPES: Dict[str, str] = None

    def __post_init__(self):
        if self.MIME_TYPES is None:
            object.__setattr__(self, 'MIME_TYPES', {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'doc': 'application/msword',
                'txt': 'text/plain',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'xls': 'application/vnd.ms-excel',
                'csv': 'text/csv',
                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'ppt': 'application/vnd.ms-powerpoint',
                'md': 'text/markdown',
                'rtf': 'application/rtf'
            })


@dataclass(frozen=True)
class OAuthConfig:
    """
    OAuth configuration for external service integrations.

    Centralizes OAuth endpoints, scopes, and parameters.
    """

    # Google OAuth endpoints
    GOOGLE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"

    # Google OAuth scopes
    GOOGLE_DRIVE_SCOPES: List[str] = None

    # Notion OAuth endpoints
    NOTION_AUTH_URI: str = "https://api.notion.com/v1/oauth/authorize"
    NOTION_TOKEN_URI: str = "https://api.notion.com/v1/oauth/token"

    # OAuth state expiry (seconds)
    # Rationale: 10 minutes is standard OAuth flow timeout
    STATE_EXPIRY_SECONDS: int = 600

    # Redirect URLs (from environment)
    @property
    def GOOGLE_REDIRECT_URI(self) -> str:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        return f"{backend_url}/api/google-drive/oauth-callback"

    @property
    def NOTION_REDIRECT_URI(self) -> str:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        return f"{backend_url}/api/notion/oauth-callback"

    def __post_init__(self):
        if self.GOOGLE_DRIVE_SCOPES is None:
            object.__setattr__(self, 'GOOGLE_DRIVE_SCOPES', [
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/userinfo.email'
            ])


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Database operation configuration.

    Controls batch sizes, timeouts, and query limits.
    """

    # Maximum rows per batch insert
    # Rationale: PostgreSQL supports 1000+, but 500 is safer
    BATCH_INSERT_SIZE: int = 500

    # Default pagination page size
    DEFAULT_PAGE_SIZE: int = 20

    # Maximum pagination page size
    MAX_PAGE_SIZE: int = 100

    # Query timeout (seconds)
    # Rationale: Prevent hung queries from blocking resources
    QUERY_TIMEOUT_SECONDS: int = 30


@dataclass(frozen=True)
class RedirectConfig:
    """
    Frontend redirect configuration for OAuth callbacks.

    Ensures consistent redirect behavior across integrations.
    """

    @property
    def FRONTEND_URL(self) -> str:
        return os.getenv("FRONTEND_URL", "http://localhost:3000")

    # OAuth success redirect paths
    OAUTH_SUCCESS_PATHS: Dict[str, str] = None

    # OAuth error redirect paths
    OAUTH_ERROR_PATHS: Dict[str, str] = None

    def __post_init__(self):
        if self.OAUTH_SUCCESS_PATHS is None:
            object.__setattr__(self, 'OAUTH_SUCCESS_PATHS', {
                'google_drive': '/documents?provider=google_drive&status=connected',
                'notion': '/documents?provider=notion&status=connected'
            })

        if self.OAUTH_ERROR_PATHS is None:
            object.__setattr__(self, 'OAUTH_ERROR_PATHS', {
                'google_drive': '/documents?provider=google_drive&status=error',
                'notion': '/documents?provider=notion&status=error'
            })


# Singleton instances for easy import
TEXT_CHUNKING = TextChunkingConfig()
EMBEDDING = EmbeddingConfig()
SEARCH = SearchConfig()
RATE_LIMITS = RateLimits()
FILE_LIMITS = FileLimits()
OAUTH = OAuthConfig()
DATABASE = DatabaseConfig()
REDIRECTS = RedirectConfig()


# Convenience exports
__all__ = [
    'TextChunkingConfig',
    'EmbeddingConfig',
    'SearchConfig',
    'RateLimits',
    'FileLimits',
    'OAuthConfig',
    'DatabaseConfig',
    'RedirectConfig',
    'TEXT_CHUNKING',
    'EMBEDDING',
    'SEARCH',
    'RATE_LIMITS',
    'FILE_LIMITS',
    'OAUTH',
    'DATABASE',
    'REDIRECTS',
]
