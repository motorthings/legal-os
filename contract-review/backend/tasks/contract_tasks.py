"""
Celery tasks for contract processing
"""
from celery import Task
from celery_app import celery_app
from contract_processor import process_contract
from logger_config import get_logger
from typing import Dict, Any
import asyncio

logger = get_logger(__name__)


class ContractProcessingTask(Task):
    """
    Base class for contract processing tasks with custom error handling
    """
    autoretry_for = (Exception,)  # Retry on any exception
    retry_kwargs = {'max_retries': 3, 'countdown': 60}  # 3 retries, 60s between
    retry_backoff = True  # Exponential backoff (60s, 120s, 240s)
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add randomness to prevent thundering herd

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries"""
        document_id = args[0] if args else kwargs.get('document_id')
        logger.error(f"❌ Contract processing FAILED permanently: {document_id} - {str(exc)}")

        # Update document status in database
        try:
            from database import get_supabase
            supabase = get_supabase()
            supabase.table('documents').update({
                'processing_status': f'error: {str(exc)[:200]}'
            }).eq('id', document_id).execute()
        except Exception as e:
            logger.error(f"Failed to update error status: {e}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        document_id = args[0] if args else kwargs.get('document_id')
        retry_count = self.request.retries
        logger.warning(f"⚠️ Retrying contract processing: {document_id} (attempt {retry_count + 1}/3)")


@celery_app.task(base=ContractProcessingTask, name='tasks.contract_tasks.process_contract_task')
def process_contract_task(document_id: str) -> Dict[str, Any]:
    """
    Process a contract asynchronously via Celery

    Args:
        document_id: UUID of the document to process

    Returns:
        Contract analysis result
    """
    logger.info(f"📋 Processing contract: {document_id}")

    # Update status to processing
    try:
        from database import get_supabase
        supabase = get_supabase()
        supabase.table('documents').update({
            'processing_status': 'processing'
        }).eq('id', document_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update processing status: {e}")

    # Run async process_contract in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(process_contract(document_id))
        logger.info(f"✅ Contract processed successfully: {document_id}")
        return result
    finally:
        loop.close()


@celery_app.task(base=ContractProcessingTask, name='tasks.contract_tasks.process_urgent_contract_task')
def process_urgent_contract_task(document_id: str) -> Dict[str, Any]:
    """
    High-priority contract processing (user-triggered re-analysis)

    Uses 'urgent' queue for immediate processing
    """
    logger.info(f"🚨 URGENT contract processing: {document_id}")
    return process_contract_task(document_id)


@celery_app.task(base=ContractProcessingTask, name='tasks.contract_tasks.process_batch_contract_task')
def process_batch_contract_task(document_id: str) -> Dict[str, Any]:
    """
    Low-priority batch contract processing

    Uses 'batch' queue for non-urgent bulk uploads
    """
    logger.info(f"📦 Batch contract processing: {document_id}")
    return process_contract_task(document_id)


@celery_app.task(name='tasks.contract_tasks.cleanup_old_results')
def cleanup_old_results():
    """
    Periodic task to clean up old task results from Redis

    Scheduled via Celery Beat (cron-like)
    """
    logger.info("🧹 Cleaning up old Celery task results")
    # Celery automatically expires results based on result_expires config
    return {'status': 'cleaned'}
