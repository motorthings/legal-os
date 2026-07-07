"""
Celery task queue configuration for contract processing
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import os
from logger_config import get_logger

logger = get_logger(__name__)

# Redis connection from environment
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery app
celery_app = Celery(
    'contentful_contract_review',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks.contract_tasks']  # Import task modules
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'tasks.contract_tasks.process_contract_task': {'queue': 'default'},
        'tasks.contract_tasks.process_urgent_contract_task': {'queue': 'urgent'},
        'tasks.contract_tasks.process_batch_contract_task': {'queue': 'batch'},
    },

    # Task priority (0-9, higher = more important)
    task_default_priority=5,

    # Retry configuration
    task_acks_late=True,  # Acknowledge task AFTER completion (safer)
    task_reject_on_worker_lost=True,  # Requeue if worker crashes

    # Rate limiting (prevent overwhelming Claude API)
    task_annotations={
        'tasks.contract_tasks.process_contract_task': {
            'rate_limit': '10/m'  # Max 10 contracts processed per minute
        }
    },

    # Timeouts
    task_time_limit=900,  # 15 minutes hard limit
    task_soft_time_limit=600,  # 10 minutes soft limit (raises exception)

    # Worker configuration
    worker_prefetch_multiplier=1,  # Only prefetch 1 task (prevents hogging)
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (prevent memory leaks)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'visibility_timeout': 3600,
    },

    # Serialization (use JSON for safety)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


# Task lifecycle hooks (for logging)
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log when task starts"""
    logger.info(f"🚀 Starting task: {task.name} [ID: {task_id}]")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, **extra):
    """Log when task completes"""
    logger.info(f"✅ Completed task: {task.name} [ID: {task_id}]")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Log task failures"""
    logger.error(f"❌ Task failed: {sender.name} [ID: {task_id}] - {str(exception)}")
