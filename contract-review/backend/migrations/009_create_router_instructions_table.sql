-- Migration: Create router_instructions table
-- Description: Store router classification system instructions separately from contract-type instructions
-- Created: 2025-12-06

-- Create router_instructions table
CREATE TABLE IF NOT EXISTS public.router_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instructions TEXT NOT NULL,
    version TEXT NOT NULL, -- Version number from XML (e.g., "1.0.0")
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_router_instructions_active ON public.router_instructions(is_active);
CREATE INDEX IF NOT EXISTS idx_router_instructions_version ON public.router_instructions(version);

-- Enable RLS
ALTER TABLE public.router_instructions ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Admins only
CREATE POLICY "Admins can view router instructions"
    ON public.router_instructions
    FOR SELECT
    TO authenticated
    USING ((EXISTS ( SELECT 1
   FROM users
  WHERE ((users.id = auth.uid()) AND (users.role = 'admin'::text)))));

CREATE POLICY "Admins can insert router instructions"
    ON public.router_instructions
    FOR INSERT
    TO authenticated
    WITH CHECK ((EXISTS ( SELECT 1
   FROM users
  WHERE ((users.id = auth.uid()) AND (users.role = 'admin'::text)))));

CREATE POLICY "Admins can update router instructions"
    ON public.router_instructions
    FOR UPDATE
    TO authenticated
    USING ((EXISTS ( SELECT 1
   FROM users
  WHERE ((users.id = auth.uid()) AND (users.role = 'admin'::text)))));

-- Update trigger
CREATE TRIGGER update_router_instructions_updated_at
    BEFORE UPDATE ON public.router_instructions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Remove router from contract_type_instructions if it exists
DELETE FROM public.contract_type_instructions WHERE contract_type = 'router';

-- Restore the original constraint without 'router'
ALTER TABLE public.contract_type_instructions DROP CONSTRAINT IF EXISTS contract_type_instructions_contract_type_check;
ALTER TABLE public.contract_type_instructions
ADD CONSTRAINT contract_type_instructions_contract_type_check
CHECK (contract_type = ANY (ARRAY['vendor'::text, 'customer'::text, 'employment'::text, 'dpa'::text, 'general'::text, 'other'::text]));
