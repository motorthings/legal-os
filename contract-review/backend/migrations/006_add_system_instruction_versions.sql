-- Migration: Add system instruction version tracking to contract_analysis table
-- Description: Tracks which versions of system instructions were used for each contract analysis
--              This enables re-running analyses when instructions are updated

-- Add version tracking columns
ALTER TABLE contract_analysis
ADD COLUMN IF NOT EXISTS router_instructions_version TEXT,
ADD COLUMN IF NOT EXISTS analysis_instructions_version TEXT,
ADD COLUMN IF NOT EXISTS legal_standards_version TEXT;

-- Add index for finding contracts analyzed with specific instruction versions
CREATE INDEX IF NOT EXISTS idx_contract_analysis_router_version
ON contract_analysis(router_instructions_version);

CREATE INDEX IF NOT EXISTS idx_contract_analysis_instructions_version
ON contract_analysis(analysis_instructions_version);

-- Add comments explaining the columns
COMMENT ON COLUMN contract_analysis.router_instructions_version IS 'Version/hash of router system instructions used for classification';
COMMENT ON COLUMN contract_analysis.analysis_instructions_version IS 'Version/hash of sub-agent system instructions used for analysis';
COMMENT ON COLUMN contract_analysis.legal_standards_version IS 'Snapshot of legal standards IDs used for this analysis';

-- Create a function to get file hash for versioning
CREATE OR REPLACE FUNCTION get_instruction_file_version(file_path TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    -- This is a placeholder - actual versioning will be done in Python
    -- by calculating file hash or reading embedded version
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION get_instruction_file_version IS 'Placeholder for instruction file versioning - actual implementation in Python';
