-- Migration: Create contract_type_instructions table
-- Description: Stores customizable system instructions for different contract types

CREATE TABLE IF NOT EXISTS contract_type_instructions (
    contract_type TEXT PRIMARY KEY CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general')),
    instructions TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE contract_type_instructions ENABLE ROW LEVEL SECURITY;

-- Policy: Admins can manage all contract type instructions
CREATE POLICY "Admins can manage contract type instructions"
    ON contract_type_instructions FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

-- Policy: All authenticated users can view contract type instructions (needed for contract analysis)
CREATE POLICY "Users can view contract type instructions"
    ON contract_type_instructions FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Add comment
COMMENT ON TABLE contract_type_instructions IS 'Customizable AI system instructions for different contract types (vendor, customer, employment, dpa, general)';
