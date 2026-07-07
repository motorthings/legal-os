'use client';

import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import dynamic from 'next/dynamic';

// Dynamically import the theme page component
const ThemeSettings = dynamic(() => import('../theme/page'), { ssr: false });
const SystemInstructions = dynamic(() => import('../system-instructions/page'), { ssr: false });

interface ModelOption {
  id: string;
  name: string;
  description: string;
}

const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: 'claude-sonnet-4-5-20250929',
    name: 'Claude 4.5 Sonnet',
    description: 'Balanced performance and intelligence for most tasks'
  },
  {
    id: 'claude-opus-4-5-20251101',
    name: 'Claude 4.5 Opus',
    description: 'Most capable model for complex analysis and reasoning'
  },
  {
    id: 'claude-haiku-4-0-20250129',
    name: 'Claude 4.0 Haiku',
    description: 'Fastest model for quick analysis and high throughput'
  }
];

type TabType = 'model' | 'theme' | 'instructions';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('model');
  const [selectedModel, setSelectedModel] = useState<string>('claude-sonnet-4-5-20250929');
  const [temperature, setTemperature] = useState<number>(0.0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);

      const [modelData, tempData] = await Promise.all([
        apiGet<{ setting_value: { model: string; display_name: string } }>('/api/admin/settings/default_model'),
        apiGet<{ setting_value: { temperature: number } }>('/api/admin/settings/default_temperature')
      ]);

      setSelectedModel(modelData.setting_value.model);
      setTemperature(tempData.setting_value.temperature);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const selectedModelOption = AVAILABLE_MODELS.find(m => m.id === selectedModel);
      if (!selectedModelOption) {
        throw new Error('Invalid model selected');
      }

      await Promise.all([
        apiPost('/api/admin/settings/default_model', {
          setting_value: {
            model: selectedModel,
            display_name: selectedModelOption.name
          }
        }),
        apiPost('/api/admin/settings/default_temperature', {
          setting_value: {
            temperature: temperature
          }
        })
      ]);

      setSuccessMessage('Settings saved successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading && activeTab === 'model') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-primary">Settings</h1>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-6 border-b border-border">
        <button
          onClick={() => setActiveTab('model')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'model'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted hover:text-secondary'
          }`}
        >
          Model
        </button>
        <button
          onClick={() => setActiveTab('instructions')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'instructions'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted hover:text-secondary'
          }`}
        >
          Instructions
        </button>
        <button
          onClick={() => setActiveTab('theme')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'theme'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted hover:text-secondary'
          }`}
        >
          Theme
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'model' && (
        <>
          {error && (
            <div className="mb-4 bg-red-50/20 border border-red-200 rounded-lg p-4" role="alert">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {successMessage && (
            <div className="mb-4 bg-green-50/20 border border-green-200 rounded-lg p-4" role="status">
              <p className="text-green-800">{successMessage}</p>
            </div>
          )}

          {/* Model Selection */}
          <div className="card p-6 mb-6">
            <h2 className="text-lg font-semibold text-primary mb-4">AI Model</h2>

            <div className="space-y-3">
              {AVAILABLE_MODELS.map((model) => (
                <label
                  key={model.id}
                  className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedModel === model.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border bg-card hover:border-primary/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="model"
                    value={model.id}
                    checked={selectedModel === model.id}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-primary">{model.name}</div>
                    <div className="text-sm text-muted mt-1">{model.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Temperature Setting */}
          <div className="card p-6 mb-6">
            <h2 className="text-lg font-semibold text-primary mb-4">Temperature</h2>
            <p className="text-sm text-muted mb-4">
              Controls randomness in the AI's responses.
              <br />
              Lower values (0.0) are more deterministic and focused, higher values (1.0) are more creative and varied.
              <br />
              For contract analysis, lower values are recommended.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Temperature: {temperature.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted mt-1">
                  <span>0.0 (Deterministic)</span>
                  <span>1.0 (Creative)</span>
                </div>
              </div>

              <div
                className="p-3 rounded-lg text-sm border"
                style={{
                  backgroundColor: temperature <= 0.3
                    ? 'var(--color-success-bg)'
                    : temperature <= 0.7
                    ? 'var(--color-warning-bg)'
                    : 'var(--color-error-bg)',
                  color: temperature <= 0.3
                    ? 'var(--color-success)'
                    : temperature <= 0.7
                    ? 'var(--color-warning)'
                    : 'var(--color-error)',
                  borderColor: temperature <= 0.3
                    ? 'var(--color-success)'
                    : temperature <= 0.7
                    ? 'var(--color-warning)'
                    : 'var(--color-error)'
                }}
              >
                {temperature <= 0.3 && '✓ Recommended for contract analysis - Consistent, focused responses'}
                {temperature > 0.3 && temperature <= 0.7 && '⚠ Moderate creativity - May vary between runs'}
                {temperature > 0.7 && '⚠ High creativity - Not recommended for legal analysis'}
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary"
              aria-busy={saving}
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>

          {/* Info Box */}
          <div className="mt-6 card p-4 bg-info-bg border border-info text-sm">
            <p className="font-medium mb-2">About Model Selection & Evaluation</p>
            <p className="text-muted">
              These settings determine which AI model and temperature will be used for all new contract analyses.
              The model name and temperature used for each analysis is automatically saved to the database,
              allowing you to evaluate performance differences between models over time.
            </p>
          </div>
        </>
      )}

      {activeTab === 'theme' && <ThemeSettings />}

      {activeTab === 'instructions' && <SystemInstructions />}
    </div>
  );
}
