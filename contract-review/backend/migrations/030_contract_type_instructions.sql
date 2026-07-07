-- Migration 030: Contract Type Instructions Table
-- Date: 2025-12-04
-- Purpose: Create table for storing per-contract-type system instructions
-- Impact: Enables customized AI analysis behavior for each contract type

-- ============================================================================
-- CONTRACT_TYPE_INSTRUCTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS contract_type_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Contract type (unique constraint)
    contract_type TEXT NOT NULL UNIQUE CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general')),

    -- System instructions content
    instructions TEXT NOT NULL,

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for contract_type (primary lookup key)
CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_type_instructions_type
ON contract_type_instructions(contract_type);

-- ============================================================================
-- UPDATED_AT TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_contract_type_instructions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_contract_type_instructions_updated_at ON contract_type_instructions;
CREATE TRIGGER trigger_contract_type_instructions_updated_at
    BEFORE UPDATE ON contract_type_instructions
    FOR EACH ROW
    EXECUTE FUNCTION update_contract_type_instructions_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS
ALTER TABLE contract_type_instructions ENABLE ROW LEVEL SECURITY;

-- Policy: Only admins can read
CREATE POLICY contract_type_instructions_admin_read
ON contract_type_instructions
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.role = 'admin'
    )
);

-- Policy: Only admins can insert
CREATE POLICY contract_type_instructions_admin_insert
ON contract_type_instructions
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.role = 'admin'
    )
);

-- Policy: Only admins can update
CREATE POLICY contract_type_instructions_admin_update
ON contract_type_instructions
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.role = 'admin'
    )
);

-- ============================================================================
-- SEED DEFAULT INSTRUCTIONS
-- ============================================================================

-- Insert default instructions for all contract types
INSERT INTO contract_type_instructions (contract_type, instructions)
VALUES
    ('vendor', 'You are analyzing vendor/supplier agreements. Focus on payment terms, service level agreements, liability limitations, termination clauses, and vendor performance requirements. Provide analysis in structured JSON format.'),
    ('customer', 'You are analyzing customer contracts and sales agreements. Focus on pricing, delivery terms, warranties, intellectual property ownership, customer obligations, and limitation of liability. Provide analysis in structured JSON format.'),
    ('employment', 'You are analyzing employment and HR contracts. Focus on compensation, benefits, non-compete clauses, confidentiality obligations, termination provisions, and intellectual property assignment. Provide analysis in structured JSON format.'),
    ('dpa', 'You are analyzing Data Processing Agreements. Focus on GDPR compliance, data subject rights, security measures, sub-processor provisions, data retention, and breach notification requirements. Provide analysis in structured JSON format.'),
    ('general', 'You are analyzing general contracts. Provide comprehensive analysis covering key terms, parties, obligations, payment terms, termination, liability, and any unusual or high-risk provisions. Provide analysis in structured JSON format.')
ON CONFLICT (contract_type) DO NOTHING;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    row_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Check table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'contract_type_instructions'
    ) INTO table_exists;

    -- Count rows
    SELECT COUNT(*) INTO row_count
    FROM contract_type_instructions;

    -- Count policies
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename = 'contract_type_instructions';

    RAISE NOTICE 'Migration 030 Verification:';
    RAISE NOTICE '  - Table exists: %', table_exists;
    RAISE NOTICE '  - Seed rows inserted: %', row_count;
    RAISE NOTICE '  - RLS policies created: %', policy_count;

    IF NOT table_exists THEN
        RAISE EXCEPTION 'Migration 030 failed: contract_type_instructions table not created';
    END IF;

    IF row_count != 5 THEN
        RAISE NOTICE '  ⚠️  Warning: Expected 5 seed rows, found %', row_count;
    END IF;
END $$;
