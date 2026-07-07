-- Migration: Create legal_standards table
-- Description: Configurable legal compliance standards for automated contract analysis

CREATE TABLE IF NOT EXISTS legal_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    term_name TEXT NOT NULL,
    description TEXT NOT NULL,
    contract_type TEXT NOT NULL CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general', 'all')),
    violation_severity TEXT NOT NULL CHECK (violation_severity IN ('critical', 'high', 'medium', 'low')),
    acceptable_values JSONB NOT NULL DEFAULT '{}',
    recommendation TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    client_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_legal_standards_contract_type ON legal_standards(contract_type);
CREATE INDEX IF NOT EXISTS idx_legal_standards_category ON legal_standards(category);
CREATE INDEX IF NOT EXISTS idx_legal_standards_is_active ON legal_standards(is_active);
CREATE INDEX IF NOT EXISTS idx_legal_standards_client_id ON legal_standards(client_id);

-- Enable RLS
ALTER TABLE legal_standards ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view all active standards
CREATE POLICY "Users can view active legal standards"
    ON legal_standards FOR SELECT
    USING (is_active = true);

-- Policy: Admins can manage all standards
CREATE POLICY "Admins can manage all legal standards"
    ON legal_standards FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- Add comment
COMMENT ON TABLE legal_standards IS 'Configurable legal compliance standards used for automated contract analysis and risk detection';
