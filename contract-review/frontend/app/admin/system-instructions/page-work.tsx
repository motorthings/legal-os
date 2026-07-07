'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiGet, apiPost } from '@/lib/api';

interface ContractType {
  value: string;
  label: string;
  description: string;
}

const CONTRACT_TYPES: ContractType[] = [
  {
    value: 'vendor',
    label: 'Vendor/Supplier Agreement',
    description: 'Contracts with vendors, suppliers, and service providers'
  },
  {
    value: 'customer',
    label: 'Customer Contract',
    description: 'Sales agreements, terms of service, and customer contracts'
  },
  {
    value: 'employment',
    label: 'Employment & HR',
    description: 'Employment agreements, NDAs, and HR-related contracts'
  },
  {
    value: 'dpa',
    label: 'Data Processing Agreement',
    description: 'GDPR/privacy compliance and data processing agreements'
  },
  {
    value: 'general',
    label: 'General/Other',
    description: 'General contracts and agreements not covered by other types'
  },
  {
    value: 'other',
    label: 'Other Contract Types',
    description: 'Fallback instructions for uncategorized contract types'
  }
];

export default function SystemInstructionsPage() {
  const [selectedType, setSelectedType] = useState<string>('');
  const [instructions, setInstructions] = useState<string>('');
  const [originalInstructions, setOriginalInstructions] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const fetchInstructions = async (contractType: string) => {
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      const data = await apiGet<{ instructions: string }>(`/api/system-instructions/contract-types/${contractType}`);
      setInstructions(data.instructions || '');
      setOriginalInstructions(data.instructions || '');
      setShowPreview(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setInstructions('');
      setOriginalInstructions('');
    } finally {
      setLoading(false);
    }
  };

  const handleTypeSelect = (contractType: string) => {
    setSelectedType(contractType);
    if (contractType) {
      fetchInstructions(contractType);
    } else {
      setInstructions('');
      setOriginalInstructions('');
    }
  };

  const handleSave = async () => {
    if (!selectedType) return;

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      await apiPost(`/api/system-instructions/contract-types/${selectedType}`, {
        instructions: instructions
      });

      setOriginalInstructions(instructions);
      setSuccessMessage('System instructions saved successfully!');

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const selectedContractType = CONTRACT_TYPES.find(t => t.value === selectedType);
  const hasChanges = instructions !== originalInstructions;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-primary">System Instructions</h1>
      </div>

      {error && (
        <div className="mb-4 bg-red-50/20 border border-red-200 rounded-lg p-4" role="alert" aria-live="polite">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 bg-green-50/20 border border-green-200 rounded-lg p-4" role="status" aria-live="polite">
          <p className="text-green-800">{successMessage}</p>
        </div>
      )}

      {/* Contract Type Selection */}
      <div className="mb-6 card p-4">
        <h2 className="text-lg font-semibold text-primary mb-3">Select Contract Type</h2>

        <select
          value={selectedType}
          onChange={(e) => handleTypeSelect(e.target.value)}
          className="input-field"
        >
          <option value="">-- Select a contract type --</option>
          {CONTRACT_TYPES.map(type => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>


      {/* Editor */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary">
            {showPreview ? 'Preview' : 'System Instructions Editor'}
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPreview(!showPreview)}
              disabled={!selectedType || !instructions}
              className="px-4 py-2 text-sm font-medium rounded-lg border transition-colors bg-card hover:bg-hover text-primary border-border disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {showPreview ? 'Edit' : 'Preview'}
            </button>
          </div>
        </div>

        {!selectedType ? (
          <div className="text-center py-12 text-muted">
            Select a contract type to view and edit its system instructions
          </div>
        ) : loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
            <p className="text-muted">Loading instructions...</p>
          </div>
        ) : showPreview ? (
          <div className="bg-hover rounded-lg p-4 min-h-[400px] whitespace-pre-wrap text-sm text-primary font-mono">
            {instructions}
          </div>
        ) : (
          <>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              className="textarea-field min-h-[400px] font-mono text-sm resize-y"
              placeholder={`Enter system instructions for ${selectedContractType?.label || 'this contract type'}...\n\nExample:\nYou are analyzing ${selectedContractType?.label?.toLowerCase() || 'contracts'}. Focus on:\n1. Key risk areas specific to this contract type\n2. Required clauses and standard terms\n3. Red flags and negotiation points\n4. Compliance requirements\n\nProvide analysis in structured JSON format with risk_score, key_terms, red_flags, and recommendations.`}
              aria-label="System instructions editor"
            />

            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-muted" id="unsaved-changes-status">
                {hasChanges && '• Unsaved changes'}
              </div>
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges || !instructions.trim()}
                className="btn-primary"
                aria-busy={saving}
                aria-describedby="unsaved-changes-status"
              >
                {saving ? 'Saving...' : 'Save Instructions'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
