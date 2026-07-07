-- Migration: Add 'other' to contract_type_instructions constraint
-- Description: Allows the 'other' contract type for ambiguous/uncategorized contracts

-- Drop the old constraint
ALTER TABLE contract_type_instructions
DROP CONSTRAINT IF EXISTS contract_type_instructions_contract_type_check;

-- Add new constraint with 'other' included
ALTER TABLE contract_type_instructions
ADD CONSTRAINT contract_type_instructions_contract_type_check
CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general', 'other'));

-- Update comment
COMMENT ON TABLE contract_type_instructions IS 'Customizable AI system instructions for different contract types (vendor, customer, employment, dpa, general, other)';
