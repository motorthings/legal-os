"""
Legal AI OS — Celery Task Queue

Three queues: default, urgent, batch.
Rate-limited to prevent overwhelming LLM APIs.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "legal_os",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.due_diligence",
    ],
)

celery_app.conf.update(
    task_routes={
        "app.workers.tasks.due_diligence.*": {"queue": "default"},
    },
    task_default_priority=5,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_annotations={
        "app.workers.tasks.due_diligence.process_dd_document": {
            "rate_limit": "20/m"       # 20 docs/min — generous for batch
        }
    },
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
