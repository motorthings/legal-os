-- Migration 035: Add redact_requested column to documents table
-- This tracks whether the user requested redaction when uploading the contract

ALTER TABLE documents ADD COLUMN IF NOT EXISTS redact_requested BOOLEAN DEFAULT false;

COMMENT ON COLUMN documents.redact_requested IS 'Whether the user requested confidential information redaction during upload';

-- Create index for filtering by redact_requested
CREATE INDEX IF NOT EXISTS idx_documents_redact_requested
ON documents(redact_requested) WHERE redact_requested = true;
