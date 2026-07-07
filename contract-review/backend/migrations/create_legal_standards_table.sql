-- =====================================================
-- Legal Standards Table
-- =====================================================
-- This table stores configurable legal standards that AI agents
-- use to evaluate contracts and generate red/yellow flags.
--
-- Usage:
--   1. Run this SQL in Supabase SQL Editor
--   2. Seed with default standards using seed_legal_standards.py
--   3. Manage via /admin/legal-standards UI
-- =====================================================

-- Create legal_standards table
CREATE TABLE IF NOT EXISTS legal_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client association (NULL = default for all clients)
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,

    -- Contract type this standard applies to
    contract_type TEXT NOT NULL CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general', 'all')),

    -- Categorization
    category TEXT NOT NULL,  -- e.g., 'payment_terms', 'liability', 'termination', 'ip_rights'
    term_name TEXT NOT NULL,  -- e.g., 'net_days', 'liability_cap_multiple', 'notice_period'

    -- Acceptance criteria (flexible JSON structure)
    acceptable_values JSONB NOT NULL DEFAULT '{}',
    -- Examples:
    -- {"type": "range", "max": 60, "preferred": 30}
    -- {"type": "enum", "allowed": ["Net 30", "Net 45", "Net 60"]}
    -- {"type": "boolean", "allowed": true}
    -- {"type": "required_list", "must_include": ["IP", "Data breach"]}

    -- Severity if this standard is violated
    violation_severity TEXT NOT NULL DEFAULT 'yellow_flag' CHECK (violation_severity IN ('red_flag', 'yellow_flag', 'info')),

    -- Human-readable descriptions
    description TEXT NOT NULL,  -- Short description of the standard
    rationale TEXT,  -- Why this standard exists
    recommendation TEXT,  -- What to do if violated

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Ensure unique standards per client/contract_type/category/term
    UNIQUE(client_id, contract_type, category, term_name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_legal_standards_client_id ON legal_standards(client_id);
CREATE INDEX IF NOT EXISTS idx_legal_standards_contract_type ON legal_standards(contract_type);
CREATE INDEX IF NOT EXISTS idx_legal_standards_category ON legal_standards(category);
CREATE INDEX IF NOT EXISTS idx_legal_standards_is_active ON legal_standards(is_active);
CREATE INDEX IF NOT EXISTS idx_legal_standards_lookup ON legal_standards(client_id, contract_type, is_active);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_legal_standards_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_legal_standards_updated_at
    BEFORE UPDATE ON legal_standards
    FOR EACH ROW
    EXECUTE FUNCTION update_legal_standards_updated_at();

-- Enable Row Level Security (RLS)
ALTER TABLE legal_standards ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Admin users can do everything
CREATE POLICY "Admin users can manage all legal standards"
    ON legal_standards
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE auth.users.id = auth.uid()
            AND auth.users.raw_user_meta_data->>'role' = 'admin'
        )
    );

-- Non-admin users can only read active standards for their client
CREATE POLICY "Users can read active standards for their client"
    ON legal_standards
    FOR SELECT
    USING (
        is_active = true
        AND (
            client_id IS NULL  -- Default standards
            OR client_id = (
                SELECT client_id FROM auth.users
                WHERE auth.users.id = auth.uid()
            )
        )
    );

-- Grant permissions
GRANT SELECT ON legal_standards TO authenticated;
GRANT ALL ON legal_standards TO service_role;

-- Add helpful comment
COMMENT ON TABLE legal_standards IS 'Stores configurable legal standards for contract review. Standards with client_id=NULL are defaults for all clients. Client-specific standards override defaults.';
COMMENT ON COLUMN legal_standards.acceptable_values IS 'JSON structure defining acceptable values. Format depends on type: range, enum, boolean, required_list, etc.';
COMMENT ON COLUMN legal_standards.violation_severity IS 'Severity of flag to generate if standard is violated: red_flag (critical), yellow_flag (concerning), info (informational)';
