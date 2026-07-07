"""
System Instructions Versioning Module

Tracks versions of system instruction files to enable:
1. Auditing which instruction versions were used for each contract analysis
2. Re-running analyses when instructions are updated
3. A/B testing different instruction versions
"""
import re
from typing import Optional
from logger_config import get_logger
from database import get_supabase

logger = get_logger(__name__)

# Lazy-load Supabase client
_supabase = None

def get_supabase_client():
    """Get or initialize Supabase client"""
    global _supabase
    if _supabase is None:
        _supabase = get_supabase()
    return _supabase


def extract_version_from_xml(xml_content: str) -> str:
    """
    Extract version number from XML instruction content

    Args:
        xml_content: XML instruction file content

    Returns:
        Version number (e.g., "1.0.0") or "unknown"
    """
    try:
        # Look for <number>X.X.X</number> pattern
        match = re.search(r'<number>([\d.]+)</number>', xml_content)
        if match:
            return match.group(1)
        return "unknown"
    except Exception as e:
        logger.error(f"Failed to extract version from XML: {e}")
        return "unknown"


def get_instruction_version(instruction_type: str, instructions_dir: str = None) -> str:
    """
    Get version number for a specific instruction type from database

    Args:
        instruction_type: Type of instructions (router, vendor, customer, etc.)
        instructions_dir: DEPRECATED - kept for backwards compatibility

    Returns:
        Version number (e.g., "1.0.0") from database or "unknown"
    """
    try:
        supabase = get_supabase_client()

        # Load from appropriate table based on instruction type
        if instruction_type == 'router':
            result = supabase.table('router_instructions')\
                .select('version, instructions')\
                .eq('is_active', True)\
                .single()\
                .execute()
        elif instruction_type in ['vendor', 'customer', 'employment', 'dpa', 'general', 'other']:
            result = supabase.table('contract_type_instructions')\
                .select('instructions')\
                .eq('contract_type', instruction_type)\
                .single()\
                .execute()

            if result.data and result.data.get('instructions'):
                # Extract version from XML content
                version = extract_version_from_xml(result.data['instructions'])
                logger.debug(f"Instruction version for {instruction_type}: {version}")
                return version
        else:
            logger.warning(f"Unknown instruction type for versioning: {instruction_type}")
            return "unknown"

        # For router, version is stored directly in the table
        if instruction_type == 'router' and result.data:
            version = result.data.get('version', 'unknown')
            logger.debug(f"Router instruction version: {version}")
            return version

        return "unknown"

    except Exception as e:
        logger.error(f"Failed to get instruction version for {instruction_type}: {e}")
        return "unknown"


def get_legal_standards_version(standards: list) -> str:
    """
    Create a version identifier for the legal standards used

    Args:
        standards: List of legal standard dictionaries with 'id' field

    Returns:
        Comma-separated sorted list of standard IDs (for audit trail)
    """
    if not standards:
        return "none"

    # Sort IDs for consistent ordering
    standard_ids = sorted([str(s.get('id', 'unknown')) for s in standards])

    # Return comma-separated list (first 200 chars to avoid huge strings)
    version_str = ','.join(standard_ids)
    if len(version_str) > 200:
        # Return count instead of hash for very long lists
        return f"{len(standard_ids)}_standards"

    return version_str
