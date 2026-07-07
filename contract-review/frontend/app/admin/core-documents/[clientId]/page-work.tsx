'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiGet, apiPost } from '@/lib/api';
import { logger } from '@/lib/logger';
import Link from 'next/link';

interface Document {
  id: string;
  filename: string;
  uploaded_at: string;
  file_size?: number;
  is_core_document?: boolean;
}

interface MappedDocument {
  mapping_id: string;
  document_id: string;
  filename: string;
  uploaded_at: string;
  file_size?: number;
  display_order: number;
}

interface TemplateSlot {
  key: string;
  label: string;
  description: string;
}

const TEMPLATE_SLOTS: TemplateSlot[] = [
  {
    key: 'pm_models_ref',
    label: 'Project Management Models',
    description: 'Frameworks like Agile, OKRs, Eisenhower Matrix'
  },
  {
    key: 'domain_specific_models_ref',
    label: 'Domain-Specific Models',
    description: 'Industry or field-specific frameworks'
  },
  {
    key: 'language_guideline_ref',
    label: 'Language Guidelines',
    description: 'Writing style and communication preferences'
  },
  {
    key: 'knowledge_base_ref_4',
    label: 'Team Capability Profiles',
    description: 'Team member skills and growth areas'
  },
  {
    key: 'client_gold_standard_example',
    label: 'Gold Standard Examples',
    description: 'Example documents to emulate'
  }
];

export default function CoreDocumentsPage() {
  const params = useParams();
  const router = useRouter();
  const clientId = params.clientId as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [clientName, setClientName] = useState<string>('');
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([]);
  const [currentMappings, setCurrentMappings] = useState<Record<string, MappedDocument[]>>({});
  const [docMappings, setDocMappings] = useState<Record<string, string[]>>({});
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [clientId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load client info, documents, and current mappings
      const [clientResponse, docsResponse, mappingsResponse] = await Promise.all([
        apiGet<{ client: any }>(`/api/clients/${clientId}`),
        apiGet<{ documents: any[] }>(`/api/clients/${clientId}/documents`),
        apiGet<{ mappings: any }>(`/api/clients/${clientId}/document-mappings`)
      ]);

      setClientName(clientResponse.client?.name || 'Client');
      setAvailableDocuments(docsResponse.documents || []);

      const mappings = mappingsResponse.mappings || {};
      setCurrentMappings(mappings);

      // Convert to selection format
      const selections: Record<string, string[]> = {};
      Object.entries(mappings).forEach(([slot, docs]: [string, any]) => {
        selections[slot] = docs.map((d: MappedDocument) => d.document_id);
      });
      setDocMappings(selections);

      // Get last updated time (use most recent mapping)
      let mostRecent: string | null = null;
      (Object.values(mappings) as MappedDocument[][]).forEach((docs) => {
        docs.forEach((doc) => {
          if (!mostRecent || new Date(doc.uploaded_at) > new Date(mostRecent)) {
            mostRecent = doc.uploaded_at;
          }
        });
      });
      setLastUpdated(mostRecent);

    } catch (err) {
      logger.error('Load error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleDocument = (slotKey: string, documentId: string) => {
    setDocMappings(prev => {
      const current = prev[slotKey] || [];
      if (current.includes(documentId)) {
        return { ...prev, [slotKey]: current.filter(id => id !== documentId) };
      } else {
        return { ...prev, [slotKey]: [...current, documentId] };
      }
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const mappings = TEMPLATE_SLOTS.map(slot => ({
        template_slot: slot.key,
        document_ids: docMappings[slot.key] || []
      })).filter(m => m.document_ids.length > 0);

      await apiPost(`/api/clients/${clientId}/document-mappings`, {
        mappings
      });

      setSuccessMessage('Document mappings saved successfully!');
      await loadData(); // Reload to show updated mappings
    } catch (err) {
      logger.error('Save error:', err);
      setError(err instanceof Error ? err.message : 'Failed to save document mappings');
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerateInstructions = async () => {
    setRegenerating(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await apiPost(`/api/clients/${clientId}/regenerate-instructions`, {});
      setSuccessMessage('System instructions regenerated successfully!');
    } catch (err) {
      logger.error('Regenerate error:', err);
      setError(err instanceof Error ? err.message : 'Failed to regenerate instructions');
    } finally {
      setRegenerating(false);
    }
  };

  const hasChanges = () => {
    // Check if current selections differ from saved mappings
    for (const slot of TEMPLATE_SLOTS) {
      const current = (docMappings[slot.key] || []).sort();
      const saved = (currentMappings[slot.key] || []).map(d => d.document_id).sort();

      if (current.length !== saved.length) return true;
      if (!current.every((id, idx) => id === saved[idx])) return true;
    }
    return false;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link href="/admin/documents" className="text-teal-600 hover:text-teal-700 text-sm font-medium mb-2 inline-block">
            ← Back to Documents
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Link Reference Documents</h1>
              <p className="text-gray-600 mt-1">Map uploaded documents to AI instruction templates for {clientName}</p>
              {lastUpdated && (
                <p className="text-sm text-gray-500 mt-1">
                  Last updated: {new Date(lastUpdated).toLocaleString()}
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges()}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {saving ? 'Saving...' : 'Save Mappings'}
              </button>
              <button
                onClick={handleRegenerateInstructions}
                disabled={regenerating}
                className="px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-700 disabled:opacity-50 font-medium"
              >
                {regenerating ? 'Regenerating...' : 'Regenerate Instructions'}
              </button>
            </div>
          </div>
        </div>

        {/* Success/Error Messages */}
        {successMessage && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">{successMessage}</p>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Info Box */}
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-blue-900">How This Works</h3>
              <p className="text-sm text-blue-800 mt-1">
                Select which uploaded documents the AI should reference for each category below. When you save and regenerate,
                the AI's instructions will be updated to reference these documents by name (e.g., "Follow the framework in leadership-guide.pdf").
              </p>
            </div>
          </div>
        </div>

        {/* Document Mapping Sections */}
        <div className="space-y-6">
          {TEMPLATE_SLOTS.map((slot) => {
            const mappedDocs = currentMappings[slot.key] || [];
            const selectedCount = (docMappings[slot.key] || []).length;

            return (
              <div key={slot.key} className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-6">
                  {/* Slot Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h2 className="text-lg font-semibold text-gray-900">{slot.label}</h2>
                      <p className="text-sm text-gray-600 mt-1">{slot.description}</p>
                      {selectedCount > 0 && (
                        <p className="text-xs font-medium text-purple-700 mt-2">
                          {selectedCount} document{selectedCount !== 1 ? 's' : ''} selected
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Currently Mapped */}
                  {mappedDocs.length > 0 && (
                    <div className="mb-4 p-3 bg-gray-50 rounded-md">
                      <p className="text-xs font-medium text-gray-700 mb-2">Currently Mapped:</p>
                      <div className="space-y-1">
                        {mappedDocs.map((doc) => (
                          <div key={doc.document_id} className="text-sm text-gray-900">
                            • {doc.filename}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Available Documents */}
                  {availableDocuments.length === 0 ? (
                    <div className="text-center py-8 bg-gray-50 rounded-md">
                      <p className="text-gray-600">No processed documents available.</p>
                      <Link href="/documents" className="text-teal-600 hover:text-teal-700 text-sm font-medium mt-2 inline-block">
                        Upload documents →
                      </Link>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-3 max-h-60 overflow-y-auto">
                      {availableDocuments.map((doc) => {
                        const isSelected = (docMappings[slot.key] || []).includes(doc.id);
                        return (
                          <label
                            key={doc.id}
                            className={`flex items-start gap-3 p-3 rounded-md border-2 cursor-pointer transition-colors ${
                              isSelected
                                ? 'border-purple-500 bg-purple-50'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleDocument(slot.key, doc.id)}
                              className="mt-0.5 h-4 w-4 text-purple-600 rounded focus:ring-purple-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-gray-900 truncate">
                                {doc.filename}
                              </div>
                              <div className="text-xs text-gray-500">
                                {new Date(doc.uploaded_at).toLocaleDateString()}
                                {doc.file_size && ` • ${(doc.file_size / 1024).toFixed(1)} KB`}
                              </div>
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div className="mt-8 flex items-center justify-between p-6 bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-600">
            {hasChanges() ? (
              <span className="text-amber-600 font-medium">⚠️ You have unsaved changes</span>
            ) : (
              <span className="text-green-600">✓ All changes saved</span>
            )}
          </div>
          <div className="flex gap-3">
            <Link
              href="/admin/solomon-review"
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 font-medium"
            >
              Cancel
            </Link>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges()}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {saving ? 'Saving...' : 'Save Mappings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
