-- Migration: Create theme_settings table
-- Description: Store customizable theme/branding settings per client
-- Created: 2025-12-06

-- Create theme_settings table
CREATE TABLE IF NOT EXISTS public.theme_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,

    -- Brand colors
    color_primary VARCHAR(7) DEFAULT '#6366f1',
    color_primary_hover VARCHAR(7) DEFAULT '#4f46e5',
    color_secondary VARCHAR(7) DEFAULT '#8b5cf6',
    color_text_on_primary VARCHAR(7) DEFAULT '#ffffff',
    color_text_on_secondary VARCHAR(7) DEFAULT '#ffffff',

    -- Background colors
    color_bg_page VARCHAR(7) DEFAULT '#0a0a0a',
    color_bg_card VARCHAR(7) DEFAULT '#111111',
    color_bg_hover VARCHAR(7) DEFAULT '#1a1a1a',

    -- Text colors
    color_text_primary VARCHAR(7) DEFAULT '#ffffff',
    color_text_secondary VARCHAR(7) DEFAULT '#a1a1aa',
    color_text_muted VARCHAR(7) DEFAULT '#71717a',

    -- Border colors
    color_border VARCHAR(7) DEFAULT '#27272a',
    color_border_focus VARCHAR(7) DEFAULT '#6366f1',

    -- Status colors
    color_success VARCHAR(7) DEFAULT '#22c55e',
    color_warning VARCHAR(7) DEFAULT '#f59e0b',
    color_error VARCHAR(7) DEFAULT '#ef4444',

    -- Typography
    font_family_heading VARCHAR(100) DEFAULT 'Inter',
    font_weight_heading VARCHAR(20) DEFAULT '600',
    font_family_body VARCHAR(100) DEFAULT 'Inter',
    font_weight_body VARCHAR(20) DEFAULT '400',
    font_size_base VARCHAR(20) DEFAULT '16px',

    -- Border radius
    border_radius_sm VARCHAR(20) DEFAULT '0.25rem',
    border_radius_md VARCHAR(20) DEFAULT '0.5rem',
    border_radius_lg VARCHAR(20) DEFAULT '0.75rem',

    -- Panel/Card styling
    panel_border_width VARCHAR(20) DEFAULT '1px',
    panel_border_color VARCHAR(7) DEFAULT '#27272a',
    panel_shadow_size VARCHAR(20) DEFAULT '1px',
    panel_shadow_color VARCHAR(7) DEFAULT '#000000',

    -- Header styling
    header_logo_url TEXT,
    header_bg_color VARCHAR(7) DEFAULT '#111111',
    header_title_color VARCHAR(7) DEFAULT '#14b8a6',
    header_nav_color VARCHAR(7) DEFAULT '#a1a1aa',
    header_nav_active_color VARCHAR(7) DEFAULT '#14b8a6',
    header_font_size VARCHAR(20) DEFAULT '20px',
    header_height VARCHAR(20) DEFAULT '64px',
    page_title_font_size VARCHAR(20) DEFAULT '32px',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one theme per client
    UNIQUE(client_id)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_theme_settings_client_id ON public.theme_settings(client_id);

-- Enable RLS
ALTER TABLE public.theme_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Users can only view/update their own client's theme
CREATE POLICY "Users can view their client's theme settings"
    ON public.theme_settings
    FOR SELECT
    USING (client_id = auth.jwt() ->> 'client_id'::text);

CREATE POLICY "Users can update their client's theme settings"
    ON public.theme_settings
    FOR UPDATE
    USING (client_id = auth.jwt() ->> 'client_id'::text);

CREATE POLICY "Users can insert their client's theme settings"
    ON public.theme_settings
    FOR INSERT
    WITH CHECK (client_id = auth.jwt() ->> 'client_id'::text);

-- Update trigger
CREATE TRIGGER update_theme_settings_updated_at
    BEFORE UPDATE ON public.theme_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default theme for existing clients
INSERT INTO public.theme_settings (client_id)
SELECT id FROM public.clients
WHERE NOT EXISTS (
    SELECT 1 FROM public.theme_settings WHERE client_id = clients.id
);
