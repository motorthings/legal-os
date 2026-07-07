-- Add separate timing fields for router and analysis phases
-- This migration adds two new columns to track processing times separately

ALTER TABLE contract_analysis
ADD COLUMN IF NOT EXISTS router_processing_seconds NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS analysis_processing_seconds NUMERIC(10,2);

COMMENT ON COLUMN contract_analysis.router_processing_seconds IS 'Time in seconds for router classification phase';
COMMENT ON COLUMN contract_analysis.analysis_processing_seconds IS 'Time in seconds for detailed analysis phase';
