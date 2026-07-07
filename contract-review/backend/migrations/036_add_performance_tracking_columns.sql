-- Migration 036: Add performance tracking columns
-- Track page count and processing time for performance metrics

-- Add page_count to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;

COMMENT ON COLUMN documents.page_count IS 'Number of pages in the document (for performance tracking)';

-- Add processing_time_seconds to contract_analysis table
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS processing_time_seconds NUMERIC(10, 2);

COMMENT ON COLUMN contract_analysis.processing_time_seconds IS 'Total time in seconds to process the contract (for performance metrics)';

-- Create index for performance queries
CREATE INDEX IF NOT EXISTS idx_contract_analysis_created_at
ON contract_analysis(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_page_count
ON documents(page_count) WHERE page_count IS NOT NULL;
