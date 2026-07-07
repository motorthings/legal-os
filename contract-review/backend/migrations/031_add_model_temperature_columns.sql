-- Migration 031: Add model_name and temperature columns to contract_analyses
-- Description: Track which AI model and temperature was used for each analysis
-- Created: 2025-12-06

-- Add columns to contract_analyses table
ALTER TABLE contract_analyses
ADD COLUMN IF NOT EXISTS model_name TEXT DEFAULT 'claude-3-7-sonnet-20250219',
ADD COLUMN IF NOT EXISTS temperature NUMERIC(3,2) DEFAULT 0.0 CHECK (temperature >= 0.0 AND temperature <= 1.0);

-- Create index for model queries
CREATE INDEX IF NOT EXISTS idx_contract_analyses_model_name ON contract_analyses(model_name);

-- Add comments
COMMENT ON COLUMN contract_analyses.model_name IS 'Anthropic model used for this analysis (e.g., claude-3-7-sonnet-20250219)';
COMMENT ON COLUMN contract_analyses.temperature IS 'Temperature parameter used for this analysis (0.0-1.0)';

-- Create a settings table for default values
CREATE TABLE IF NOT EXISTS admin_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key TEXT NOT NULL UNIQUE,
    setting_value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- Admins can view and modify all settings
CREATE POLICY admin_settings_admin_all ON admin_settings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

-- Insert default model settings
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('default_model', '{"model": "claude-3-7-sonnet-20250219", "display_name": "Claude 3.7 Sonnet"}', 'Default AI model for contract analysis'),
    ('default_temperature', '{"temperature": 0.0}', 'Default temperature for contract analysis (0.0-1.0)')
ON CONFLICT (setting_key) DO NOTHING;

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_admin_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_admin_settings_updated_at
    BEFORE UPDATE ON admin_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_admin_settings_updated_at();

COMMENT ON TABLE admin_settings IS 'Global admin settings for the application';
