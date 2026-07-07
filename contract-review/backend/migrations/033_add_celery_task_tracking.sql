-- Add Celery task ID column to documents table for status tracking
-- Migration: 033_add_celery_task_tracking.sql
-- Created: 2025-01-06

-- Add celery_task_id column to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS celery_task_id TEXT;

-- Add index for fast task lookups
CREATE INDEX IF NOT EXISTS idx_documents_celery_task_id
ON documents(celery_task_id)
WHERE celery_task_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN documents.celery_task_id IS 'Celery task ID for async contract processing';
