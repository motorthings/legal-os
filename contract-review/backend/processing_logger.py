"""
Processing Logger Module

Logs contract processing steps to database for debugging and transparency.
Allows users to see real-time progress of their contract analysis.
"""
import asyncio
from typing import Dict, Any, Optional
from database import get_supabase
from logger_config import get_logger

logger = get_logger(__name__)

async def log_processing_step(
    document_id: str,
    step_name: str,
    step_status: str,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log a processing step to the database

    Args:
        document_id: UUID of the document being processed
        step_name: Name of the step (e.g., 'router_classification', 'text_extraction')
        step_status: Status of the step ('started', 'completed', 'failed')
        message: Optional human-readable message
        metadata: Optional additional data (JSON)
    """
    try:
        supabase = get_supabase()

        log_entry = {
            'document_id': document_id,
            'step_name': step_name,
            'step_status': step_status,
            'message': message,
            'metadata': metadata or {}
        }

        await asyncio.to_thread(
            lambda: supabase.table('contract_processing_logs')
                .insert(log_entry)
                .execute()
        )

        logger.debug(f"Logged processing step: {step_name} - {step_status} for document {document_id}")

    except Exception as e:
        # Don't fail the entire processing if logging fails
        logger.error(f"Failed to log processing step: {str(e)}")
