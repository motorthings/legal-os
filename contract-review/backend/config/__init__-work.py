"""
Backend Configuration for SuperAssistant MVP

This module provides centralized configuration management, including
support for single-tenant mode with a default client.
"""

import os
from typing import Optional


# ============================================================================
# Default Client Configuration (Single-Tenant Mode)
# ============================================================================

# Well-known UUID for the default organization in single-tenant deployments
# This allows the application to work without explicit client management
DEFAULT_CLIENT_ID = os.getenv(
    "DEFAULT_CLIENT_ID",
    "00000000-0000-0000-0000-000000000001"
)


def get_default_client_id() -> str:
    """
    Returns the default client ID for single-tenant deployments.

    In single-tenant mode, all users belong to this hidden "default organization".
    This simplifies the user experience by eliminating client management UI
    while preserving multi-tenant database structure for future flexibility.

    Returns:
        str: UUID of the default client

    Example:
        >>> client_id = get_default_client_id()
        >>> print(client_id)
        '00000000-0000-0000-0000-000000000001'
    """
    return DEFAULT_CLIENT_ID


def get_client_id_for_user(user_profile: dict) -> str:
    """
    Returns the appropriate client_id for a given user.

    In single-tenant mode, this always returns the default client ID.
    In multi-tenant mode (future), this would return user_profile.get('client_id').

    Args:
        user_profile: User profile dictionary from authentication

    Returns:
        str: Client ID to use for this user's operations

    Example:
        >>> user = {"id": "123", "email": "user@example.com"}
        >>> client_id = get_client_id_for_user(user)
        >>> print(client_id)
        '00000000-0000-0000-0000-000000000001'
    """
    # For now, always return default client
    # Future: Check if MULTI_TENANT_MODE is enabled
    return get_default_client_id()


def is_multi_tenant_mode() -> bool:
    """
    Checks if the application is running in multi-tenant mode.

    Returns:
        bool: True if multi-tenant features should be enabled

    Note:
        Currently always returns False. Set MULTI_TENANT_MODE=true
        in environment variables to enable multi-tenant features.
    """
    return os.getenv("MULTI_TENANT_MODE", "false").lower() == "true"


# ============================================================================
# Application Configuration
# ============================================================================

# API Configuration
API_VERSION = "v1"
API_TITLE = "SuperAssistant API"
API_DESCRIPTION = "Backend API for SuperAssistant MVP"

# Rate Limiting
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "100/minute")
CHAT_RATE_LIMIT = os.getenv("CHAT_RATE_LIMIT", "20/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")

# File Upload Limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_DOCUMENT_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/csv",
    "text/plain",
]

# Database Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# AI Services
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Feature Flags
ENABLE_VOICE_INTERVIEWS = os.getenv("ENABLE_VOICE_INTERVIEWS", "true").lower() == "true"
ENABLE_DOCUMENT_UPLOAD = os.getenv("ENABLE_DOCUMENT_UPLOAD", "true").lower() == "true"
ENABLE_SYSTEM_INSTRUCTIONS = os.getenv("ENABLE_SYSTEM_INSTRUCTIONS", "true").lower() == "true"

# Volume Storage Configuration (for Railway/Docker deployments)
VOLUME_PATH = os.getenv("VOLUME_PATH")  # e.g., "/data" on Railway


# ============================================================================
# Validation Functions
# ============================================================================

def validate_config():
    """
    Validates that all required configuration is present.

    Raises:
        ValueError: If required configuration is missing
    """
    required_vars = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
    }

    missing = [key for key, value in required_vars.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please check your .env file or environment configuration."
        )


# ============================================================================
# Helper Functions
# ============================================================================

def get_client_name() -> str:
    """
    Returns the display name for the default client.

    Returns:
        str: Friendly name to use in UI/emails
    """
    return os.getenv("CLIENT_NAME", "Your Organization")


def get_assistant_name() -> str:
    """
    Returns the default assistant name.

    Returns:
        str: Name of the AI assistant
    """
    return os.getenv("ASSISTANT_NAME", "SuperAssistant")


# Validate configuration on module import
try:
    validate_config()
except ValueError as e:
    # Log warning but don't crash - allow app to start for debugging
    print(f"  Configuration Warning: {e}")
