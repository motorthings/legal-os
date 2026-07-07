"""
Centralized database connection management.
Provides singleton Supabase client to avoid connection pool exhaustion.
"""

import os
from supabase import create_client, Client
from typing import Optional
from logger_config import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """Singleton service for managing Supabase database connection."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get the singleton Supabase client instance.

        Returns:
            Supabase Client instance

        Raises:
            ValueError: If SUPABASE_URL or SUPABASE_KEY not configured
        """
        if cls._instance is None:
            supabase_url = os.environ.get("SUPABASE_URL")
            # Prefer service role key for backend operations (bypasses RLS)
            # Fall back to SUPABASE_KEY for backwards compatibility
            supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError(
                    "Supabase not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY)"
                )

            logger.info("Initializing Supabase database connection")
            cls._instance = create_client(supabase_url, supabase_key)

        return cls._instance

    @classmethod
    def reset_client(cls):
        """Reset the client instance. Useful for testing."""
        cls._instance = None


# Convenience function for getting the client
def get_supabase() -> Client:
    """
    Get the Supabase client instance.

    This is the preferred way to access the database throughout the application.

    Returns:
        Supabase Client instance
    """
    return DatabaseService.get_client()
