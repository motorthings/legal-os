-- Migration: Add processing logs table for contract processing visibility
-- Description: Stores step-by-step logs of contract processing for debugging and transparency

CREATE TABLE IF NOT EXISTS contract_processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    step_status TEXT NOT NULL CHECK (step_status IN ('started', 'completed', 'failed')),
    message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON contract_processing_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON contract_processing_logs(created_at DESC);

-- Add RLS policies
ALTER TABLE contract_processing_logs ENABLE ROW LEVEL SECURITY;

-- Users can view logs for their own documents
CREATE POLICY "processing_logs_user_view" ON contract_processing_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = contract_processing_logs.document_id
            AND d.uploaded_by = auth.uid()
        )
    );

-- Admins can view all logs
CREATE POLICY "processing_logs_admin_all" ON contract_processing_logs
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

COMMENT ON TABLE contract_processing_logs IS 'Step-by-step logs of contract processing for debugging and transparency';
COMMENT ON COLUMN contract_processing_logs.step_name IS 'Name of the processing step (e.g., "router_classification", "text_extraction")';
COMMENT ON COLUMN contract_processing_logs.step_status IS 'Status of the step: started, completed, or failed';
COMMENT ON COLUMN contract_processing_logs.metadata IS 'Additional data about the step (e.g., classification result, error details)';
