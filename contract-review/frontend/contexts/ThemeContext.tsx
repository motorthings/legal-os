'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';

interface ThemeSettings {
  color_primary: string;
  color_primary_hover: string;
  color_secondary: string;
  color_text_on_primary: string;
  color_text_on_secondary: string;
  color_bg_page: string;
  color_bg_card: string;
  color_bg_hover: string;
  color_text_primary: string;
  color_text_secondary: string;
  color_text_muted: string;
  color_border: string;
  color_border_focus: string;
  color_success: string;
  color_warning: string;
  color_error: string;
  font_family_heading: string;
  font_weight_heading: string;
  font_family_body: string;
  font_weight_body: string;
  font_size_base: string;
  border_radius_sm: string;
  border_radius_md: string;
  border_radius_lg: string;
  panel_border_width: string;
  panel_border_color: string;
  panel_shadow_size: string;
  panel_shadow_color: string;
  header_logo_url: string | null;
  header_bg_color: string;
  header_title_color: string;
  header_nav_color: string;
  header_nav_active_color: string;
  header_font_size: string;
  header_height: string;
  page_title_font_size: string;
}

const defaultTheme: ThemeSettings = {
  color_primary: '#6366f1',
  color_primary_hover: '#4f46e5',
  color_secondary: '#8b5cf6',
  color_text_on_primary: '#ffffff',
  color_text_on_secondary: '#ffffff',
  color_bg_page: '#0a0a0a',
  color_bg_card: '#111111',
  color_bg_hover: '#1a1a1a',
  color_text_primary: '#ffffff',
  color_text_secondary: '#a1a1aa',
  color_text_muted: '#71717a',
  color_border: '#27272a',
  color_border_focus: '#6366f1',
  color_success: '#22c55e',
  color_warning: '#f59e0b',
  color_error: '#ef4444',
  font_family_heading: 'Inter',
  font_weight_heading: '600',
  font_family_body: 'Inter',
  font_weight_body: '400',
  font_size_base: '16px',
  border_radius_sm: '0.25rem',
  border_radius_md: '0.5rem',
  border_radius_lg: '0.75rem',
  panel_border_width: '1px',
  panel_border_color: '#27272a',
  panel_shadow_size: '1px',
  panel_shadow_color: '#000000',
  header_logo_url: null,
  header_bg_color: '#111111',
  header_title_color: '#14b8a6',
  header_nav_color: '#a1a1aa',
  header_nav_active_color: '#14b8a6',
  header_font_size: '20px',
  header_height: '64px',
  page_title_font_size: '32px'
};

interface ThemeContextValue {
  theme: ThemeSettings;
  loading: boolean;
  refreshTheme: () => Promise<void>;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: defaultTheme,
  loading: true,
  refreshTheme: async () => {}
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeSettings>(defaultTheme);
  const [loading, setLoading] = useState(true);

  const applyTheme = (settings: ThemeSettings) => {
    const root = document.documentElement;

    // Apply CSS custom properties
    root.style.setProperty('--color-primary', settings.color_primary);
    root.style.setProperty('--color-primary-hover', settings.color_primary_hover);
    root.style.setProperty('--color-secondary', settings.color_secondary);
    root.style.setProperty('--color-text-on-primary', settings.color_text_on_primary);
    root.style.setProperty('--color-text-on-secondary', settings.color_text_on_secondary);
    root.style.setProperty('--color-bg-page', settings.color_bg_page);
    root.style.setProperty('--color-bg-card', settings.color_bg_card);
    root.style.setProperty('--color-bg-hover', settings.color_bg_hover);
    root.style.setProperty('--color-text-primary', settings.color_text_primary);
    root.style.setProperty('--color-text-secondary', settings.color_text_secondary);
    root.style.setProperty('--color-text-muted', settings.color_text_muted);
    root.style.setProperty('--color-border-default', settings.color_border);
    root.style.setProperty('--color-border-focus', settings.color_border_focus);
    root.style.setProperty('--color-success', settings.color_success);
    root.style.setProperty('--color-warning', settings.color_warning);
    root.style.setProperty('--color-error', settings.color_error);
    root.style.setProperty('--font-family-heading', settings.font_family_heading);
    root.style.setProperty('--font-weight-heading', settings.font_weight_heading);
    root.style.setProperty('--font-family-body', settings.font_family_body);
    root.style.setProperty('--font-weight-body', settings.font_weight_body);
    root.style.setProperty('--font-size-base', settings.font_size_base);
    root.style.setProperty('--border-radius-sm', settings.border_radius_sm);
    root.style.setProperty('--border-radius-md', settings.border_radius_md);
    root.style.setProperty('--border-radius-lg', settings.border_radius_lg);
    root.style.setProperty('--panel-border-width', settings.panel_border_width);
    root.style.setProperty('--panel-border-color', settings.panel_border_color);
    root.style.setProperty('--panel-shadow-size', settings.panel_shadow_size);
    root.style.setProperty('--panel-shadow-color', settings.panel_shadow_color);
    root.style.setProperty('--header-bg-color', settings.header_bg_color);
    root.style.setProperty('--header-title-color', settings.header_title_color);
    root.style.setProperty('--header-nav-color', settings.header_nav_color);
    root.style.setProperty('--header-nav-active-color', settings.header_nav_active_color);
    root.style.setProperty('--header-font-size', settings.header_font_size);
    root.style.setProperty('--header-height', settings.header_height);
    root.style.setProperty('--page-title-font-size', settings.page_title_font_size);
    if (settings.header_logo_url) {
      root.style.setProperty('--header-logo-url', `url(${settings.header_logo_url})`);
    } else {
      root.style.removeProperty('--header-logo-url');
    }
  };

  const fetchTheme = async () => {
    try {
      const response = await apiGet<{ theme: ThemeSettings }>('/api/theme');
      if (response?.theme) {
        const mergedTheme = { ...defaultTheme, ...response.theme };
        setTheme(mergedTheme);
        applyTheme(mergedTheme);
      }
    } catch (error) {
      logger.error('Failed to fetch theme:', error);
      // Use default theme on error
      applyTheme(defaultTheme);
    } finally {
      setLoading(false);
    }
  };

  const refreshTheme = async () => {
    await fetchTheme();
  };

  useEffect(() => {
    // Apply default theme immediately to prevent flash
    applyTheme(defaultTheme);
    // Then fetch custom theme
    fetchTheme();
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, loading, refreshTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
