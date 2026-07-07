from logger_config import get_logger
from cache import get_cached_system_instructions, cache_system_instructions

logger = get_logger(__name__)

"""
System Instructions Loader

Loads per-user system instructions (system prompts) for the AI assistant.
Instructions are stored in Supabase Storage (persistent) with fallback to local files.

Storage Priority:
1. Supabase Storage: system-instructions bucket, path: users/{user_id}.txt (persistent)
2. Local files: system_instructions/users/{user_id}.txt (ephemeral on Railway)
3. Default: system_instructions/default.txt (fallback)

Supports template variables that are replaced at runtime with user/client data:
- {user_name} - User's full name
- {user_email} - User's email address
- {user_role} - User's role (admin, user)
- {client_name} - Organization name (uses default in single-tenant mode)
- {client_id} - Client UUID (uses default in single-tenant mode)
- {assistant_name} - Custom assistant name (from client or default "SuperAssistant")
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache
from config import get_default_client_id, get_client_name, get_assistant_name
from database import get_supabase
from supabase import Client

# Get centralized Supabase client
try:
    supabase: Optional[Client] = get_supabase()
except ValueError:
    supabase = None
    logger.warning("⚠️  WARNING: Supabase not configured for system instructions storage")
    logger.warning("   Will fall back to local files only (ephemeral on Railway)")

# Path to system instructions directory
SYSTEM_INSTRUCTIONS_DIR = Path(__file__).parent / "system_instructions"
DEFAULT_PROMPT_FILE = SYSTEM_INSTRUCTIONS_DIR / "default.txt"
USERS_DIR = SYSTEM_INSTRUCTIONS_DIR / "users"


def replace_template_variables(template: str, variables: Dict[str, str]) -> str:
    """
    Replace template variables in the format {variable_name} with actual values.

    Args:
        template: The template string with {variable_name} placeholders
        variables: Dictionary mapping variable names to their values

    Returns:
        String with all variables replaced
    """
    result = template
    for key, value in variables.items():
        # Replace {key} with value
        result = result.replace(f"{{{key}}}", str(value))
    return result


@lru_cache(maxsize=32)
def load_user_system_instructions(
    user_id: str,
    user_name: str = "User",
    user_email: str = "",
    user_role: str = "user",
    client_id: str = None,
    client_name: str = None,
    assistant_name: str = None
) -> str:
    """
    Load system instructions for a specific user.

    Priority:
    1. Supabase Storage: system-instructions bucket, users/{user_id}.txt (persistent)
    2. Local file: system_instructions/users/{user_id}.txt (ephemeral on Railway)
    3. Default file: system_instructions/default.txt (fallback)

    Replaces template variables with actual user/client data.

    Args:
        user_id: UUID of the user
        user_name: User's full name
        user_email: User's email address
        user_role: User's role (admin or user)
        client_id: Client's UUID
        client_name: Client organization name
        assistant_name: Custom assistant name

    Returns:
        str: The system instructions with variables replaced

    Raises:
        FileNotFoundError: If no instructions found anywhere
    """
    template = None

    # PRIORITY 1: Try Supabase Storage (persistent)
    if supabase:
        try:
            storage_path = f"users/{user_id}.txt"
            logger.info(f"   📋 Attempting to load from Supabase Storage: {storage_path}")

            # Download from Supabase Storage
            response = supabase.storage.from_('system-instructions').download(storage_path)

            if response:
                template = response.decode('utf-8')
                logger.info(f"   ✅ Loaded user-specific instructions from Supabase Storage")
        except Exception as e:
            logger.info(f"   ℹ️  No instructions in Supabase Storage: {str(e)}")
            # Not an error - will try local files next

    # PRIORITY 2: Try local file (ephemeral on Railway, but works for dev/testing)
    if not template:
        user_file = USERS_DIR / f"{user_id}.txt"
        if user_file.exists():
            logger.info(f"   📋 Loading user-specific system instructions from local file")
            with open(user_file, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"   ✅ Loaded from local file (ephemeral on Railway)")

    # PRIORITY 3: Fall back to default
    if not template:
        if DEFAULT_PROMPT_FILE.exists():
            logger.info(f"   📋 Loading default system instructions (no user-specific found for {user_id})")
            with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            raise FileNotFoundError(
                f"No system instructions found anywhere:\n"
                f"  - Supabase Storage: system-instructions/users/{user_id}.txt (not found)\n"
                f"  - Local file: {USERS_DIR / f'{user_id}.txt'} (not found)\n"
                f"  - Default: {DEFAULT_PROMPT_FILE} (not found)"
            )

    # Use config defaults for missing values (single-tenant mode)
    if client_id is None:
        client_id = get_default_client_id()
    if client_name is None:
        client_name = get_client_name()
    if assistant_name is None:
        assistant_name = get_assistant_name()

    # Prepare variables for replacement
    variables = {
        "user_name": user_name,
        "user_email": user_email,
        "user_role": user_role,
        "client_id": client_id,
        "client_name": client_name,
        "assistant_name": assistant_name,
    }

    # Replace template variables
    instructions = replace_template_variables(template, variables)

    return instructions


def get_system_instructions_for_user(
    user_id: str,
    user_data: Optional[Dict] = None
) -> str:
    """
    Convenience function to load system instructions from user data dict.

    Uses Redis cache for performance (1-hour TTL), with automatic fallback
    to loading from storage/files if cache miss or Redis unavailable.

    Args:
        user_id: UUID of the user
        user_data: Dict containing user info from Supabase (from get_current_user)

    Returns:
        str: The system instructions with variables replaced
    """
    if user_data is None:
        user_data = {}

    # Try to get from Redis cache first (1-hour TTL)
    cached = get_cached_system_instructions(user_id)
    if cached is not None:
        logger.debug(f"✅ System instructions loaded from cache for user {user_id}")
        return cached

    # Cache miss or Redis unavailable - load from storage/files
    logger.debug(f"📋 Cache miss - loading system instructions for user {user_id}")
    instructions = load_user_system_instructions(
        user_id=user_id,
        user_name=user_data.get('name', 'User'),
        user_email=user_data.get('email', ''),
        user_role=user_data.get('role', 'user'),
        client_id=user_data.get('client_id'),  # Will use default if None
        client_name=user_data.get('client_name'),  # Will use default if None
        assistant_name=user_data.get('assistant_name')  # Will use default if None
    )

    # Cache for 1 hour (3600 seconds)
    cache_system_instructions(user_id, instructions, ttl=3600)

    return instructions


# Legacy function for backwards compatibility
def get_default_system_instructions() -> str:
    """
    Legacy function - loads default system instructions without user customization.

    DEPRECATED: Use get_system_instructions_for_user() instead.

    Returns:
        str: The default system instructions
    """
    print("   ⚠️  WARNING: Using deprecated get_default_system_instructions()")
    print("   ⚠️  Upgrade to get_system_instructions_for_user() for per-user customization")

    if DEFAULT_PROMPT_FILE.exists():
        with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise FileNotFoundError(
            f"Default system instructions not found at {DEFAULT_PROMPT_FILE}"
        )


# For testing/debugging
if __name__ == "__main__":
    print("System Instructions Loader - Test Mode\n")

    # Test loading default
    try:
        default_instructions = get_default_system_instructions()
        logger.info(f"✓ Default instructions loaded: {len(default_instructions)} characters")
        logger.info(f"  First 100 characters: {default_instructions[:100]}...\n")
    except FileNotFoundError as e:
        logger.info(f"✗ Could not load default instructions: {e}\n")

    # Test template variable replacement
    print("Testing template variable replacement:")
    test_template = "Hello {user_name} from {client_name}! Your role is {user_role}."
    test_variables = {
        "user_name": "John Doe",
        "client_name": "Acme Corp",
        "user_role": "admin"
    }
    result = replace_template_variables(test_template, test_variables)
    logger.info(f"  Template: {test_template}")
    logger.info(f"  Result: {result}")
    logger.info(f"  ✓ Variables replaced successfully\n")

    # Test loading user-specific instructions
    print("Testing user-specific loading:")
    test_user_id = "test-user-123"
    try:
        user_instructions = load_user_system_instructions(
            user_id=test_user_id,
            user_name="Test User",
            client_name="Test Corp"
        )
        logger.info(f"✓ Loaded instructions for {test_user_id}: {len(user_instructions)} characters")
    except FileNotFoundError as e:
        logger.info(f"  → No user-specific file found (expected), fell back to default")
