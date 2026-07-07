#!/bin/bash
# Start Celery worker for local development

echo "🚀 Starting Celery worker..."

celery -A celery_app worker \
  --loglevel=info \
  --concurrency=3 \
  -Q default,urgent,batch \
  --pool=solo
