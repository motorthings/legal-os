-- Migration: Add router classification columns to contract_analysis table
-- Description: Adds dedicated columns for storing router classification data instead of only in full_analysis JSONB

-- Add router classification columns
ALTER TABLE contract_analysis
ADD COLUMN IF NOT EXISTS router_classification TEXT,
ADD COLUMN IF NOT EXISTS router_confidence_score INTEGER,
ADD COLUMN IF NOT EXISTS router_reasoning TEXT,
ADD COLUMN IF NOT EXISTS router_key_signals JSONB DEFAULT '[]'::jsonb;

-- Add check constraint for confidence score
ALTER TABLE contract_analysis
ADD CONSTRAINT contract_analysis_router_confidence_check
CHECK (router_confidence_score IS NULL OR (router_confidence_score >= 0 AND router_confidence_score <= 100));

-- Add index on router_classification for filtering
CREATE INDEX IF NOT EXISTS idx_contract_analysis_router_classification
ON contract_analysis(router_classification);

-- Add comment explaining the columns
COMMENT ON COLUMN contract_analysis.router_classification IS 'Contract type determined by the router agent (e.g., NDA, employment, vendor, etc.)';
COMMENT ON COLUMN contract_analysis.router_confidence_score IS 'Confidence score (0-100) of the router classification';
COMMENT ON COLUMN contract_analysis.router_reasoning IS 'Explanation of why the router chose this classification';
COMMENT ON COLUMN contract_analysis.router_key_signals IS 'Key signals that led to the classification decision';
