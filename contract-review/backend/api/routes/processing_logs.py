"""
Processing Logs API Routes

Provides endpoints to fetch contract processing logs for debugging and transparency.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import get_supabase
from logger_config import get_logger

router = APIRouter(prefix="/api/contracts/{document_id}/processing-logs", tags=["processing_logs"])
logger = get_logger(__name__)

@router.get("")
async def get_processing_logs(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get processing logs for a specific contract

    Returns a chronological list of processing steps with timestamps.
    """
    try:
        supabase = get_supabase()

        # Fetch logs for this document
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_processing_logs')
                .select('*')
                .eq('document_id', document_id)
                .order('created_at', desc=False)  # Chronological order
                .execute()
        )

        return {
            'success': True,
            'logs': result.data or []
        }

    except Exception as e:
        logger.error(f"Error fetching processing logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
