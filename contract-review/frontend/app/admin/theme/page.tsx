'use client';

import { useState, useEffect } from 'react';
import { apiGet, apiPut, apiPost, apiDelete, authenticatedFetch } from '@/lib/api';
import { useTheme } from '@/contexts/ThemeContext';
import LoadingSpinner from '@/components/LoadingSpinner';
import toast from 'react-hot-toast';
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

interface ColorInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  description?: string;
}

// Fixed input styles for color hex inputs - these don't change with theme
// to ensure they remain readable while editing colors
const fixedColorInputStyle = {
  backgroundColor: '#1e293b',
  color: '#f8fafc',
  borderColor: '#475569',
};

function ColorInput({ label, value, onChange, description }: ColorInputProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 shrink-0">
        <label className="block text-sm font-medium text-primary">{label}</label>
        {description && <p className="text-xs text-muted">{description}</p>}
      </div>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-8 h-8 rounded cursor-pointer border border-default"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-20 px-2 py-1 text-sm font-mono border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          style={fixedColorInputStyle}
          pattern="^#[0-9a-fA-F]{6}$"
        />
      </div>
    </div>
  );
}

// Dropdown options
const FONT_OPTIONS = [
  { value: 'Geist', label: 'Geist (Vercel)' },
  { value: 'Geist Mono', label: 'Geist Mono (Vercel)' },
  { value: 'Inter', label: 'Inter' },
  { value: 'Roboto', label: 'Roboto' },
  { value: 'Open Sans', label: 'Open Sans' },
  { value: 'Lato', label: 'Lato' },
  { value: 'Poppins', label: 'Poppins' },
  { value: 'Montserrat', label: 'Montserrat' },
  { value: 'Source Sans Pro', label: 'Source Sans Pro' },
  { value: 'Nunito', label: 'Nunito' },
  { value: 'Raleway', label: 'Raleway' },
  { value: 'Ubuntu', label: 'Ubuntu' },
  { value: 'system-ui', label: 'System Default' },
];

const FONT_WEIGHT_OPTIONS = [
  { value: '400', label: 'Regular' },
  { value: '500', label: 'Medium' },
  { value: '600', label: 'Semi Bold' },
  { value: '700', label: 'Bold' },
];

const FONT_SIZE_OPTIONS = [
  { value: '14px', label: '14px' },
  { value: '15px', label: '15px' },
  { value: '16px', label: '16px' },
  { value: '17px', label: '17px' },
  { value: '18px', label: '18px' },
];

const BORDER_RADIUS_OPTIONS = [
  { value: '0', label: 'None' },
  { value: '0.125rem', label: 'Extra Small' },
  { value: '0.25rem', label: 'Small' },
  { value: '0.375rem', label: 'Medium Small' },
  { value: '0.5rem', label: 'Medium' },
  { value: '0.75rem', label: 'Large' },
  { value: '1rem', label: 'Extra Large' },
];

const BORDER_WIDTH_OPTIONS = [
  { value: '0', label: 'None' },
  { value: '1px', label: '1px' },
  { value: '2px', label: '2px' },
  { value: '3px', label: '3px' },
];

const SHADOW_SIZE_OPTIONS = [
  { value: '0', label: 'None' },
  { value: '2px', label: 'Small' },
  { value: '4px', label: 'Medium' },
  { value: '8px', label: 'Large' },
  { value: '12px', label: 'Extra Large' },
];

const NAV_BAR_FONT_SIZE_OPTIONS = [
  { value: '12px', label: '12px' },
  { value: '14px', label: '14px' },
  { value: '16px', label: '16px' },
  { value: '18px', label: '18px' },
  { value: '20px', label: '20px' },
  { value: '22px', label: '22px' },
  { value: '24px', label: '24px' },
  { value: '26px', label: '26px' },
  { value: '28px', label: '28px' },
  { value: '30px', label: '30px' },
  { value: '32px', label: '32px' },
  { value: '36px', label: '36px' },
];

const PAGE_TITLE_FONT_SIZE_OPTIONS = [
  { value: '20px', label: '20px' },
  { value: '24px', label: '24px' },
  { value: '28px', label: '28px' },
  { value: '32px', label: '32px' },
  { value: '36px', label: '36px' },
  { value: '40px', label: '40px' },
  { value: '48px', label: '48px' },
];

const HEADER_HEIGHT_OPTIONS = [
  { value: '48px', label: '48px' },
  { value: '56px', label: '56px' },
  { value: '64px', label: '64px' },
  { value: '72px', label: '72px' },
  { value: '80px', label: '80px' },
];

// WCAG AA compliant color palette presets
const COLOR_PALETTE_PRESETS = [
  {
    name: 'Indigo Professional',
    description: 'Clean, modern look with indigo accents',
    colors: {
      color_primary: '#4f46e5',
      color_primary_hover: '#4338ca',
      color_secondary: '#7c3aed',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#f8fafc',
      color_bg_page: '#0f172a',
      color_bg_card: '#1e293b',
      color_bg_hover: '#334155',
      color_text_primary: '#f8fafc',
      color_text_secondary: '#cbd5e1',
      color_text_muted: '#94a3b8',
      color_border: '#334155',
      color_border_focus: '#4f46e5',
      color_success: '#22c55e',
      color_warning: '#f59e0b',
      color_error: '#ef4444',
      header_bg_color: '#1e293b',
      header_title_color: '#4f46e5',
      header_nav_color: '#94a3b8',
      header_nav_active_color: '#4f46e5',
    }
  },
  {
    name: 'Ocean Blue',
    description: 'Calming blue tones for a trustworthy feel',
    colors: {
      color_primary: '#0284c7',
      color_primary_hover: '#0369a1',
      color_secondary: '#06b6d4',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#f0f9ff',
      color_bg_page: '#0c1222',
      color_bg_card: '#172033',
      color_bg_hover: '#1e3a5f',
      color_text_primary: '#f0f9ff',
      color_text_secondary: '#bae6fd',
      color_text_muted: '#7dd3fc',
      color_border: '#1e3a5f',
      color_border_focus: '#0284c7',
      color_success: '#10b981',
      color_warning: '#fbbf24',
      color_error: '#f87171',
      header_bg_color: '#172033',
      header_title_color: '#0284c7',
      header_nav_color: '#7dd3fc',
      header_nav_active_color: '#0284c7',
    }
  },
  {
    name: 'Forest Green',
    description: 'Natural, eco-friendly appearance',
    colors: {
      color_primary: '#059669',
      color_primary_hover: '#047857',
      color_secondary: '#14b8a6',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#ecfdf5',
      color_bg_page: '#0a1612',
      color_bg_card: '#132a22',
      color_bg_hover: '#1a3d31',
      color_text_primary: '#ecfdf5',
      color_text_secondary: '#a7f3d0',
      color_text_muted: '#6ee7b7',
      color_border: '#1a3d31',
      color_border_focus: '#059669',
      color_success: '#22c55e',
      color_warning: '#fbbf24',
      color_error: '#f87171',
      header_bg_color: '#132a22',
      header_title_color: '#059669',
      header_nav_color: '#6ee7b7',
      header_nav_active_color: '#059669',
    }
  },
  {
    name: 'Royal Purple',
    description: 'Elegant and creative styling',
    colors: {
      color_primary: '#7c3aed',
      color_primary_hover: '#6d28d9',
      color_secondary: '#a855f7',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#faf5ff',
      color_bg_page: '#0f0a1a',
      color_bg_card: '#1a1228',
      color_bg_hover: '#2d1f47',
      color_text_primary: '#faf5ff',
      color_text_secondary: '#e9d5ff',
      color_text_muted: '#c4b5fd',
      color_border: '#2d1f47',
      color_border_focus: '#7c3aed',
      color_success: '#22c55e',
      color_warning: '#fbbf24',
      color_error: '#f87171',
      header_bg_color: '#1a1228',
      header_title_color: '#7c3aed',
      header_nav_color: '#c4b5fd',
      header_nav_active_color: '#7c3aed',
    }
  },
  {
    name: 'Warm Coral',
    description: 'Friendly and inviting warm tones',
    colors: {
      color_primary: '#f97316',
      color_primary_hover: '#ea580c',
      color_secondary: '#fb923c',
      color_text_on_primary: '#1a0f0a',
      color_text_on_secondary: '#fff7ed',
      color_bg_page: '#1a0f0a',
      color_bg_card: '#2a1a12',
      color_bg_hover: '#3d261a',
      color_text_primary: '#fff7ed',
      color_text_secondary: '#fed7aa',
      color_text_muted: '#fdba74',
      color_border: '#3d261a',
      color_border_focus: '#f97316',
      color_success: '#22c55e',
      color_warning: '#fbbf24',
      color_error: '#ef4444',
      header_bg_color: '#2a1a12',
      header_title_color: '#f97316',
      header_nav_color: '#fdba74',
      header_nav_active_color: '#f97316',
    }
  },
  {
    name: 'Slate Minimal',
    description: 'Clean, neutral business style',
    colors: {
      color_primary: '#64748b',
      color_primary_hover: '#475569',
      color_secondary: '#94a3b8',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#f8fafc',
      color_bg_page: '#0f172a',
      color_bg_card: '#1e293b',
      color_bg_hover: '#334155',
      color_text_primary: '#f8fafc',
      color_text_secondary: '#e2e8f0',
      color_text_muted: '#94a3b8',
      color_border: '#334155',
      color_border_focus: '#64748b',
      color_success: '#22c55e',
      color_warning: '#f59e0b',
      color_error: '#ef4444',
      header_bg_color: '#1e293b',
      header_title_color: '#64748b',
      header_nav_color: '#94a3b8',
      header_nav_active_color: '#64748b',
    }
  },
  {
    name: 'Rose Gold',
    description: 'Sophisticated with warm pink accents',
    colors: {
      color_primary: '#e11d48',
      color_primary_hover: '#be123c',
      color_secondary: '#f43f5e',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#fff1f2',
      color_bg_page: '#1a0a10',
      color_bg_card: '#2a1219',
      color_bg_hover: '#3d1a24',
      color_text_primary: '#fff1f2',
      color_text_secondary: '#fecdd3',
      color_text_muted: '#fda4af',
      color_border: '#3d1a24',
      color_border_focus: '#e11d48',
      color_success: '#22c55e',
      color_warning: '#fbbf24',
      color_error: '#ef4444',
      header_bg_color: '#2a1219',
      header_title_color: '#e11d48',
      header_nav_color: '#fda4af',
      header_nav_active_color: '#e11d48',
    }
  },
  {
    name: 'Light Professional',
    description: 'Light theme for daytime use',
    colors: {
      color_primary: '#2563eb',
      color_primary_hover: '#1d4ed8',
      color_secondary: '#3b82f6',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#0f172a',
      color_bg_page: '#f8fafc',
      color_bg_card: '#ffffff',
      color_bg_hover: '#f1f5f9',
      color_text_primary: '#0f172a',
      color_text_secondary: '#475569',
      color_text_muted: '#94a3b8',
      color_border: '#e2e8f0',
      color_border_focus: '#2563eb',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#2563eb',
      header_nav_color: '#475569',
      header_nav_active_color: '#2563eb',
    }
  },
  {
    name: 'Teal Modern',
    description: 'Fresh and contemporary teal theme',
    colors: {
      color_primary: '#0d9488',
      color_primary_hover: '#0f766e',
      color_secondary: '#14b8a6',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#f0fdfa',
      color_bg_page: '#0a1414',
      color_bg_card: '#132525',
      color_bg_hover: '#1a3636',
      color_text_primary: '#f0fdfa',
      color_text_secondary: '#99f6e4',
      color_text_muted: '#5eead4',
      color_border: '#1a3636',
      color_border_focus: '#0d9488',
      color_success: '#22c55e',
      color_warning: '#fbbf24',
      color_error: '#f87171',
      header_bg_color: '#132525',
      header_title_color: '#0d9488',
      header_nav_color: '#5eead4',
      header_nav_active_color: '#0d9488',
    }
  },
  {
    name: 'Amber Warmth',
    description: 'Golden amber for a welcoming feel',
    colors: {
      color_primary: '#d97706',
      color_primary_hover: '#b45309',
      color_secondary: '#f59e0b',
      color_text_on_primary: '#1a150a',
      color_text_on_secondary: '#fffbeb',
      color_bg_page: '#1a150a',
      color_bg_card: '#2a2212',
      color_bg_hover: '#3d331a',
      color_text_primary: '#fffbeb',
      color_text_secondary: '#fde68a',
      color_text_muted: '#fcd34d',
      color_border: '#3d331a',
      color_border_focus: '#d97706',
      color_success: '#22c55e',
      color_warning: '#f59e0b',
      color_error: '#ef4444',
      header_bg_color: '#2a2212',
      header_title_color: '#d97706',
      header_nav_color: '#fcd34d',
      header_nav_active_color: '#d97706',
    }
  },
  {
    name: 'Light Teal',
    description: 'Fresh teal on clean white',
    colors: {
      color_primary: '#0d9488',
      color_primary_hover: '#0f766e',
      color_secondary: '#14b8a6',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#134e4a',
      color_bg_page: '#f0fdfa',
      color_bg_card: '#ffffff',
      color_bg_hover: '#ccfbf1',
      color_text_primary: '#134e4a',
      color_text_secondary: '#115e59',
      color_text_muted: '#5eead4',
      color_border: '#99f6e4',
      color_border_focus: '#0d9488',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#0d9488',
      header_nav_color: '#115e59',
      header_nav_active_color: '#0d9488',
    }
  },
  {
    name: 'Light Purple',
    description: 'Elegant purple on soft lavender',
    colors: {
      color_primary: '#7c3aed',
      color_primary_hover: '#6d28d9',
      color_secondary: '#8b5cf6',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#4c1d95',
      color_bg_page: '#faf5ff',
      color_bg_card: '#ffffff',
      color_bg_hover: '#f3e8ff',
      color_text_primary: '#4c1d95',
      color_text_secondary: '#6b21a8',
      color_text_muted: '#a78bfa',
      color_border: '#e9d5ff',
      color_border_focus: '#7c3aed',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#7c3aed',
      header_nav_color: '#6b21a8',
      header_nav_active_color: '#7c3aed',
    }
  },
  {
    name: 'Light Green',
    description: 'Natural green on soft mint',
    colors: {
      color_primary: '#16a34a',
      color_primary_hover: '#15803d',
      color_secondary: '#22c55e',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#14532d',
      color_bg_page: '#f0fdf4',
      color_bg_card: '#ffffff',
      color_bg_hover: '#dcfce7',
      color_text_primary: '#14532d',
      color_text_secondary: '#166534',
      color_text_muted: '#86efac',
      color_border: '#bbf7d0',
      color_border_focus: '#16a34a',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#16a34a',
      header_nav_color: '#166534',
      header_nav_active_color: '#16a34a',
    }
  },
  {
    name: 'Light Warm',
    description: 'Cozy amber on warm cream',
    colors: {
      color_primary: '#d97706',
      color_primary_hover: '#b45309',
      color_secondary: '#f59e0b',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#78350f',
      color_bg_page: '#fffbeb',
      color_bg_card: '#ffffff',
      color_bg_hover: '#fef3c7',
      color_text_primary: '#78350f',
      color_text_secondary: '#92400e',
      color_text_muted: '#fcd34d',
      color_border: '#fde68a',
      color_border_focus: '#d97706',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#d97706',
      header_nav_color: '#92400e',
      header_nav_active_color: '#d97706',
    }
  },
  {
    name: 'Light Rose',
    description: 'Romantic pink on blush',
    colors: {
      color_primary: '#e11d48',
      color_primary_hover: '#be123c',
      color_secondary: '#f43f5e',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#881337',
      color_bg_page: '#fff1f2',
      color_bg_card: '#ffffff',
      color_bg_hover: '#ffe4e6',
      color_text_primary: '#881337',
      color_text_secondary: '#9f1239',
      color_text_muted: '#fda4af',
      color_border: '#fecdd3',
      color_border_focus: '#e11d48',
      color_success: '#16a34a',
      color_warning: '#d97706',
      color_error: '#dc2626',
      header_bg_color: '#ffffff',
      header_title_color: '#e11d48',
      header_nav_color: '#9f1239',
      header_nav_active_color: '#e11d48',
    }
  },
  {
    name: 'Contentful Brand',
    description: 'Contentful brand colors - cyan blue on warm cream/white',
    colors: {
      color_primary: '#3ab2e6',
      color_primary_hover: '#2a9dd4',
      color_secondary: '#ffd75e',
      color_text_on_primary: '#ffffff',
      color_text_on_secondary: '#1a1a1a',
      color_bg_page: '#FFFCF5',
      color_bg_card: '#FFFFFF',
      color_bg_hover: '#F8F9FA',
      color_text_primary: '#1a1a1a',
      color_text_secondary: '#6B7280',
      color_text_muted: '#9CA3AF',
      color_border: '#E5E7EB',
      color_border_focus: '#3ab2e6',
      color_success: '#10B981',
      color_warning: '#F59E0B',
      color_error: '#f05a65',
      header_bg_color: '#FFFFFF',
      header_title_color: '#3ab2e6',
      header_nav_color: '#6B7280',
      header_nav_active_color: '#3ab2e6',
    }
  },
];

export default function ThemeSettingsPage() {
  const { refreshTheme } = useTheme();
  const [settings, setSettings] = useState<ThemeSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await apiGet<{ theme: ThemeSettings }>('/api/theme');
      if (response?.theme) {
        setSettings(response.theme);
      }
    } catch (error) {
      logger.error('Failed to fetch theme settings:', error);
      toast.error('Failed to load theme settings');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key: keyof ThemeSettings, value: string) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
    setHasChanges(true);
  };

  const applyPalette = (palette: typeof COLOR_PALETTE_PRESETS[0]) => {
    if (!settings) return;
    setSettings({ ...settings, ...palette.colors });
    setHasChanges(true);
    toast.success(`Applied "${palette.name}" palette`);
  };

  const handleSave = async () => {
    if (!settings) return;

    try {
      setSaving(true);
      await apiPut('/api/theme', settings as unknown as Record<string, unknown>);
      await refreshTheme();
      setHasChanges(false);
      toast.success('Theme settings saved');
    } catch (error) {
      logger.error('Failed to save theme settings:', error);
      toast.error('Failed to save theme settings');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset all theme settings to defaults?')) return;

    try {
      setSaving(true);
      const response = await apiPost<{ theme: ThemeSettings }>('/api/theme/reset', {});
      if (response?.theme) {
        setSettings(response.theme);
      }
      await refreshTheme();
      setHasChanges(false);
      toast.success('Theme reset to defaults');
    } catch (error) {
      logger.error('Failed to reset theme:', error);
      toast.error('Failed to reset theme');
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please use PNG, JPEG, GIF, SVG, or WebP.');
      return;
    }

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 2MB.');
      return;
    }

    try {
      setUploadingLogo(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await authenticatedFetch('/api/theme/logo', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();

      if (settings) {
        setSettings({ ...settings, header_logo_url: data.logo_url });
      }
      await refreshTheme();
      toast.success('Logo uploaded successfully');
    } catch (error) {
      logger.error('Failed to upload logo:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to upload logo');
    } finally {
      setUploadingLogo(false);
      // Reset the file input
      e.target.value = '';
    }
  };

  const handleLogoRemove = async () => {
    if (!confirm('Remove the logo?')) return;

    try {
      setUploadingLogo(true);
      await apiDelete('/api/theme/logo');

      if (settings) {
        setSettings({ ...settings, header_logo_url: null });
      }
      await refreshTheme();
      toast.success('Logo removed');
    } catch (error) {
      logger.error('Failed to remove logo:', error);
      toast.error('Failed to remove logo');
    } finally {
      setUploadingLogo(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <p className="text-muted">Failed to load theme settings</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="heading-1 mb-2">Theme Settings</h1>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleReset}
            disabled={saving}
            className="btn-secondary"
          >
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="btn-primary"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {hasChanges && (
        <div className="alert alert-warning mb-6">
          <p className="text-sm">You have unsaved changes</p>
        </div>
      )}

      <div className="space-y-6">
        {/* Color Palette Presets */}
        <div className="card p-6">
          <h2 className="heading-3 mb-2">Color Palette Presets</h2>
          <p className="text-sm text-muted mb-4">WCAG AA accessible color schemes</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {COLOR_PALETTE_PRESETS.map((palette) => (
              <button
                key={palette.name}
                onClick={() => applyPalette(palette)}
                className="group p-3 border border-default rounded-lg hover:border-primary transition-colors text-left"
              >
                <div className="flex gap-1 mb-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: palette.colors.color_primary }}
                  />
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: palette.colors.color_bg_card }}
                  />
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: palette.colors.color_text_primary }}
                  />
                </div>
                <p className="text-xs font-medium text-primary group-hover:text-primary">{palette.name}</p>
                <p className="text-xs text-muted truncate">{palette.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Colors Section */}
        <div className="card p-6">
          <h2 className="heading-3 mb-4">Colors</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Brand Colors */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-primary">Brand</h3>
              <ColorInput
                label="Primary"
                value={settings.color_primary}
                onChange={(v) => handleChange('color_primary', v)}
                description="Main accent color"
              />
              <ColorInput
                label="Primary Hover"
                value={settings.color_primary_hover}
                onChange={(v) => handleChange('color_primary_hover', v)}
                description="Hover state"
              />
              <ColorInput
                label="Secondary"
                value={settings.color_secondary}
                onChange={(v) => handleChange('color_secondary', v)}
                description="Alt accent color"
              />
            </div>

            {/* Background Colors */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-primary">Backgrounds</h3>
              <ColorInput
                label="Page"
                value={settings.color_bg_page}
                onChange={(v) => handleChange('color_bg_page', v)}
              />
              <ColorInput
                label="Card"
                value={settings.color_bg_card}
                onChange={(v) => handleChange('color_bg_card', v)}
              />
              <ColorInput
                label="Hover"
                value={settings.color_bg_hover}
                onChange={(v) => handleChange('color_bg_hover', v)}
              />
            </div>

            {/* Panel/Content Text Colors */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-primary">Panel Text</h3>
              <ColorInput
                label="Headings"
                value={settings.color_text_primary}
                onChange={(v) => handleChange('color_text_primary', v)}
                description="Titles, headers"
              />
              <ColorInput
                label="Body"
                value={settings.color_text_secondary}
                onChange={(v) => handleChange('color_text_secondary', v)}
                description="Content text"
              />
              <ColorInput
                label="Captions"
                value={settings.color_text_muted}
                onChange={(v) => handleChange('color_text_muted', v)}
                description="Subtitles, hints"
              />
            </div>

            {/* Button Text Colors */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-primary">Button Text</h3>
              <ColorInput
                label="Primary Btn"
                value={settings.color_text_on_primary}
                onChange={(v) => handleChange('color_text_on_primary', v)}
                description="Colored buttons"
              />
              <ColorInput
                label="Secondary Btn"
                value={settings.color_text_on_secondary}
                onChange={(v) => handleChange('color_text_on_secondary', v)}
                description="Outline buttons"
              />
            </div>

            {/* Status Colors */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-primary">Status</h3>
              <ColorInput
                label="Success"
                value={settings.color_success}
                onChange={(v) => handleChange('color_success', v)}
              />
              <ColorInput
                label="Warning"
                value={settings.color_warning}
                onChange={(v) => handleChange('color_warning', v)}
              />
              <ColorInput
                label="Error"
                value={settings.color_error}
                onChange={(v) => handleChange('color_error', v)}
              />
            </div>
          </div>
          {/* Colors Preview */}
          <div className="mt-6 pt-6 border-t border-default">
            <p className="text-xs font-bold text-primary mb-3">Preview</p>
            <div className="flex flex-wrap gap-3">
              <button
                style={{ backgroundColor: settings.color_primary }}
                className="px-4 py-2 text-white text-sm font-medium rounded-md"
              >
                Primary Button
              </button>
              <span
                style={{ backgroundColor: settings.color_success }}
                className="px-3 py-1 text-white text-xs rounded-full flex items-center"
              >
                Success
              </span>
              <span
                style={{ backgroundColor: settings.color_warning }}
                className="px-3 py-1 text-white text-xs rounded-full flex items-center"
              >
                Warning
              </span>
              <span
                style={{ backgroundColor: settings.color_error }}
                className="px-3 py-1 text-white text-xs rounded-full flex items-center"
              >
                Error
              </span>
            </div>
          </div>
        </div>

        {/* Top Nav Bar Section */}
        <div className="card p-6">
          <h2 className="heading-3 mb-4">Top Nav Bar</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              {/* Logo Upload */}
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Logo</label>
                <p className="text-xs text-muted mb-2">PNG, JPEG, GIF, SVG, WebP - max 2MB</p>
                <div className="flex items-center gap-4">
                  {settings.header_logo_url ? (
                    <div className="flex items-center gap-4">
                      <img
                        src={settings.header_logo_url}
                        alt="Current logo"
                        className="h-12 w-auto object-contain border border-default rounded p-1"
                      />
                      <button
                        onClick={handleLogoRemove}
                        disabled={uploadingLogo}
                        className="text-sm text-error hover:text-error/80 transition-colors"
                      >
                        {uploadingLogo ? 'Removing...' : 'Remove'}
                      </button>
                    </div>
                  ) : (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/gif,image/svg+xml,image/webp"
                        onChange={handleLogoUpload}
                        disabled={uploadingLogo}
                        className="hidden"
                      />
                      <span className="inline-block px-4 py-2 text-sm border border-default rounded-md hover:bg-hover transition-colors">
                        {uploadingLogo ? 'Uploading...' : 'Upload Logo'}
                      </span>
                    </label>
                  )}
                </div>
              </div>
              <ColorInput
                label="Background"
                value={settings.header_bg_color}
                onChange={(v) => handleChange('header_bg_color', v)}
              />
              <ColorInput
                label="Title Color"
                value={settings.header_title_color}
                onChange={(v) => handleChange('header_title_color', v)}
              />
              <ColorInput
                label="Nav Links"
                value={settings.header_nav_color}
                onChange={(v) => handleChange('header_nav_color', v)}
              />
              <ColorInput
                label="Nav Active"
                value={settings.header_nav_active_color}
                onChange={(v) => handleChange('header_nav_active_color', v)}
              />
              <div className="flex flex-wrap gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-1">Title Font Size</label>
                  <select
                    value={settings.header_font_size}
                    onChange={(e) => handleChange('header_font_size', e.target.value)}
                    className="input-field w-24"
                  >
                    {NAV_BAR_FONT_SIZE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary mb-1">Bar Height</label>
                  <select
                    value={settings.header_height}
                    onChange={(e) => handleChange('header_height', e.target.value)}
                    className="input-field w-24"
                  >
                    {HEADER_HEIGHT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            {/* Top Nav Bar Preview */}
            <div>
              <p className="text-xs font-bold text-primary mb-2">Preview</p>
              <div
                className="flex items-center justify-between px-4 rounded-lg border border-default"
                style={{
                  backgroundColor: settings.header_bg_color,
                  height: settings.header_height
                }}
              >
                {/* Title/Logo */}
                {settings.header_logo_url ? (
                  <img
                    src={settings.header_logo_url}
                    alt="Logo preview"
                    style={{
                      maxHeight: `calc(${settings.header_height} - 16px)`,
                      width: 'auto'
                    }}
                    className="object-contain"
                  />
                ) : (
                  <span
                    style={{
                      color: settings.header_title_color,
                      fontSize: settings.header_font_size,
                      fontWeight: 600
                    }}
                  >
                    Brand Title
                  </span>
                )}
                {/* Nav Links Preview */}
                <div className="flex items-center gap-4 text-sm">
                  <span
                    style={{ color: settings.header_nav_active_color }}
                    className="font-medium"
                  >
                    Active
                  </span>
                  <span style={{ color: settings.header_nav_color }}>
                    Link
                  </span>
                  <span style={{ color: settings.header_nav_color }}>
                    Link
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page Title Section */}
        <div className="card p-6">
          <h2 className="heading-3 mb-4">Page Title</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Font Size</label>
                <select
                  value={settings.page_title_font_size}
                  onChange={(e) => handleChange('page_title_font_size', e.target.value)}
                  className="input-field w-24"
                >
                  {PAGE_TITLE_FONT_SIZE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-muted">
                Page titles use the Heading Font settings from Typography below.
              </p>
            </div>
            {/* Page Title Preview */}
            <div>
              <p className="text-xs font-bold text-primary mb-2">Preview</p>
              <div className="p-4 border border-default rounded-lg" style={{ backgroundColor: settings.color_bg_card }}>
                <h1
                  style={{
                    fontFamily: settings.font_family_heading,
                    fontWeight: settings.font_weight_heading,
                    color: settings.color_text_primary,
                    fontSize: settings.page_title_font_size
                  }}
                >
                  Page Title
                </h1>
              </div>
            </div>
          </div>
        </div>

        {/* Typography Section */}
        <div className="card p-6">
          <h2 className="heading-3 mb-4">Typography</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Heading Font</label>
                <div className="flex gap-2">
                  <select
                    value={settings.font_family_heading}
                    onChange={(e) => handleChange('font_family_heading', e.target.value)}
                    className="input-field w-48"
                  >
                    {FONT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <select
                    value={settings.font_weight_heading}
                    onChange={(e) => handleChange('font_weight_heading', e.target.value)}
                    className="input-field w-32"
                  >
                    {FONT_WEIGHT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Body Font</label>
                <div className="flex gap-2">
                  <select
                    value={settings.font_family_body}
                    onChange={(e) => handleChange('font_family_body', e.target.value)}
                    className="input-field w-48"
                  >
                    {FONT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <select
                    value={settings.font_weight_body}
                    onChange={(e) => handleChange('font_weight_body', e.target.value)}
                    className="input-field w-32"
                  >
                    {FONT_WEIGHT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Base Font Size</label>
                <select
                  value={settings.font_size_base}
                  onChange={(e) => handleChange('font_size_base', e.target.value)}
                  className="input-field w-24"
                >
                  {FONT_SIZE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
            {/* Typography Preview */}
            <div>
              <h3 className="text-sm font-bold text-primary mb-2">Preview</h3>
              <div className="p-4 border border-default rounded-lg" style={{ backgroundColor: settings.color_bg_card }}>
                <h3
                  style={{
                    fontFamily: settings.font_family_heading,
                    fontWeight: settings.font_weight_heading,
                    color: settings.color_text_primary,
                    fontSize: '1.25rem'
                  }}
                  className="mb-2"
                >
                  Heading Text
                </h3>
                <p
                  style={{
                    fontFamily: settings.font_family_body,
                    fontWeight: settings.font_weight_body,
                    color: settings.color_text_secondary,
                    fontSize: settings.font_size_base
                  }}
                >
                  This is body text showing the selected font and weight.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Borders & Panels Section */}
        <div className="card p-6">
          <h2 className="heading-3 mb-4">Borders & Panels</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              {/* Border Colors */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-primary">Border Colors</h3>
                <ColorInput
                  label="Default"
                  value={settings.color_border}
                  onChange={(v) => handleChange('color_border', v)}
                />
                <ColorInput
                  label="Focus"
                  value={settings.color_border_focus}
                  onChange={(v) => handleChange('color_border_focus', v)}
                />
              </div>

              {/* Border Radius */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-primary">Border Radius</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-muted mb-1">Small</label>
                    <select
                      value={settings.border_radius_sm}
                      onChange={(e) => handleChange('border_radius_sm', e.target.value)}
                      className="input-field text-sm"
                    >
                      {BORDER_RADIUS_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted mb-1">Medium</label>
                    <select
                      value={settings.border_radius_md}
                      onChange={(e) => handleChange('border_radius_md', e.target.value)}
                      className="input-field text-sm"
                    >
                      {BORDER_RADIUS_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted mb-1">Large</label>
                    <select
                      value={settings.border_radius_lg}
                      onChange={(e) => handleChange('border_radius_lg', e.target.value)}
                      className="input-field text-sm"
                    >
                      {BORDER_RADIUS_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Panel Edge Styling */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-primary">Panel Styling</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-muted mb-1">Border Width</label>
                    <select
                      value={settings.panel_border_width}
                      onChange={(e) => handleChange('panel_border_width', e.target.value)}
                      className="input-field text-sm"
                    >
                      {BORDER_WIDTH_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted mb-1">Shadow Size</label>
                    <select
                      value={settings.panel_shadow_size}
                      onChange={(e) => handleChange('panel_shadow_size', e.target.value)}
                      className="input-field text-sm"
                    >
                      {SHADOW_SIZE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <ColorInput
                  label="Panel Border Color"
                  value={settings.panel_border_color}
                  onChange={(v) => handleChange('panel_border_color', v)}
                />
                <ColorInput
                  label="Panel Shadow Color"
                  value={settings.panel_shadow_color}
                  onChange={(v) => handleChange('panel_shadow_color', v)}
                />
              </div>
            </div>

            {/* Borders & Panels Preview */}
            <div>
              <h3 className="text-sm font-bold text-primary mb-2">Preview</h3>
              <div
                className="p-4"
                style={{
                  backgroundColor: settings.color_bg_card,
                  border: `${settings.panel_border_width} solid ${settings.panel_border_color}`,
                  boxShadow: `0 0 ${settings.panel_shadow_size} ${settings.panel_shadow_color}`,
                  borderRadius: settings.border_radius_md
                }}
              >
                <h3
                  style={{
                    color: settings.color_text_primary,
                    fontFamily: settings.font_family_heading,
                    fontWeight: settings.font_weight_heading
                  }}
                  className="text-lg mb-2"
                >
                  Sample Panel
                </h3>
                <p
                  style={{
                    color: settings.color_text_secondary,
                    fontFamily: settings.font_family_body,
                    fontWeight: settings.font_weight_body
                  }}
                  className="text-sm mb-3"
                >
                  This panel shows your border width, radius, and shadow settings.
                </p>
                <div className="flex gap-2">
                  <span
                    className="px-3 py-1 text-sm"
                    style={{
                      border: `1px solid ${settings.color_border}`,
                      borderRadius: settings.border_radius_sm,
                      color: settings.color_text_primary
                    }}
                  >
                    Small
                  </span>
                  <span
                    className="px-3 py-1 text-sm"
                    style={{
                      border: `1px solid ${settings.color_border}`,
                      borderRadius: settings.border_radius_md,
                      color: settings.color_text_primary
                    }}
                  >
                    Medium
                  </span>
                  <span
                    className="px-3 py-1 text-sm"
                    style={{
                      border: `1px solid ${settings.color_border}`,
                      borderRadius: settings.border_radius_lg,
                      color: settings.color_text_primary
                    }}
                  >
                    Large
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
