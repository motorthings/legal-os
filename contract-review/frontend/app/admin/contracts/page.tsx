'use client';

import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Link from 'next/link';
import { apiGet, apiPost, apiPostFormData, apiDelete } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from '@/components/LoadingSpinner';
import RouterClassificationModal from '@/components/RouterClassificationModal';

interface RouterClassification {
  classification: string;
  confidence_score: number;
  reasoning: string;
  key_signals?: string[];
  alternative_classification?: string | null;
  document_metadata?: {
    has_title?: boolean;
    apparent_counterparty?: string;
    document_length?: string;
  };
}

interface Contract {
  id: string;
  document_id: string;
  filename: string;
  counterparty_name?: string;
  contract_type: string;
  total_value?: number | null;
  risk_level: 'high' | 'medium' | 'low' | null;
  risk_score: number | null;
  human_review_required?: boolean;
  status: 'routing' | 'final_analysis' | 'completed' | 'failed' | 'approved' | 'rejected';
  uploaded_at: string;
  router_classification?: RouterClassification | null;
  error_message?: string | null;
}

// Backend response type (what API actually returns)
interface BackendContract {
  id: string | null;
  document_id: string;
  filename: string;
  counterparty_name?: string;
  contract_type?: string | null;
  total_value?: number | null;
  overall_risk_level?: 'high' | 'medium' | 'low' | null;
  risk_score?: number | null;
  human_review_required?: boolean;
  review_status?: string;
  uploaded_at: string;
  processing: boolean;
  full_analysis?: any; // JSONB field containing router_classification
  error_message?: string | null;
}

interface UploadFile {
  file: File;
  id: string;
  status: 'queued' | 'uploading' | 'analyzing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  contractId?: string;
}

export default function ContractsPage() {
  const [activeTab, setActiveTab] = useState<'upload' | 'all'>('all');
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [uploadQueue, setUploadQueue] = useState<UploadFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedContracts, setSelectedContracts] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [showRouterModal, setShowRouterModal] = useState<RouterClassification | null>(null);
  const [redact, setRedact] = useState(false);

  // Sort and filter state
  const [sortField, setSortField] = useState<'uploaded_at' | 'risk_level' | 'contract_type' | 'status'>('uploaded_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterRiskLevel, setFilterRiskLevel] = useState<string>('all');
  const [filterContractType, setFilterContractType] = useState<string>('all');
  const [filterReview, setFilterReview] = useState<string>('all');
  const [isReprocessing, setIsReprocessing] = useState(false);

  useEffect(() => {
    fetchContracts();
  }, []);

  // Auto-refresh only when All Contracts tab is active AND there are processing contracts
  useEffect(() => {
    if (activeTab !== 'all') return;

    // Check if any contracts are still being analyzed
    const hasProcessingContracts = contracts.some(c => c.status === 'routing' || c.status === 'final_analysis');

    if (!hasProcessingContracts) return; // No need to refresh if nothing is processing

    const interval = setInterval(() => {
      // Only refresh if not already loading to prevent overlapping requests
      if (!loading) {
        fetchContracts();
      }
    }, 20000); // Refresh every 20 seconds (instead of 5)

    return () => clearInterval(interval);
  }, [activeTab, loading, contracts]);

  const fetchContracts = async () => {
    try {
      setLoading(true);
      // Use longer timeout since contract processing can be slow
      const data = await apiGet<{ contracts: BackendContract[] }>('/api/contracts');

      // Transform backend response to match frontend Contract interface
      const transformedContracts: Contract[] = (data.contracts || []).map((contract) => {
        // Map backend review_status to frontend status
        // Backend values: 'routing', 'final_analysis', 'completed', 'failed'
        let status: Contract['status'] = 'routing';

        if (contract.review_status === 'failed') {
          status = 'failed';
        } else if (contract.review_status === 'routing') {
          status = 'routing';
        } else if (contract.review_status === 'final_analysis') {
          status = 'final_analysis';
        } else if (contract.review_status === 'completed') {
          status = 'completed';
        } else if (contract.review_status === 'approved') {
          status = 'approved';
        } else if (contract.review_status === 'rejected') {
          status = 'rejected';
        }

        return {
          id: contract.id || contract.document_id,
          document_id: contract.document_id,
          filename: contract.filename,
          counterparty_name: contract.counterparty_name,
          contract_type: contract.contract_type || 'unknown',
          total_value: contract.total_value,
          risk_level: contract.overall_risk_level || null,
          risk_score: contract.risk_score || null,
          human_review_required: contract.human_review_required || false,
          status: status,
          uploaded_at: contract.uploaded_at,
          router_classification: contract.full_analysis?.router_classification || null,
          error_message: contract.error_message,
        };
      });

      setContracts(transformedContracts);
      setError(null);
    } catch (err) {
      logger.error('Error fetching contracts:', err);
      setError(err instanceof Error ? err.message : 'Failed to load contracts');
    } finally {
      setLoading(false);
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newUploads: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substring(7),
      status: 'queued',
      progress: 0,
    }));

    setUploadQueue((prev) => [...prev, ...newUploads]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const uploadContracts = async () => {
    const queuedFiles = uploadQueue.filter((u) => u.status === 'queued');

    for (const upload of queuedFiles) {
      try {
        // Update status to uploading
        setUploadQueue((prev) =>
          prev.map((u) =>
            u.id === upload.id ? { ...u, status: 'uploading', progress: 50 } : u
          )
        );

        // Create form data (no contract_type - AI will auto-detect)
        const formData = new FormData();
        formData.append('file', upload.file);
        formData.append('redact', redact.toString());

        // Upload file using API helper (uses Railway backend URL)
        const result = await apiPostFormData<{
          success: boolean;
          document_id: string;
          filename: string;
          message: string;
        }>('/api/contracts/upload', formData);

        // Upload complete! Mark as completed and remove from queue
        setUploadQueue((prev) =>
          prev.map((u) =>
            u.id === upload.id
              ? {
                  ...u,
                  status: 'completed',
                  progress: 100,
                  contractId: result.document_id,
                }
              : u
          )
        );

        // Immediately refresh All Contracts tab to show the processing contract
        fetchContracts();

        // Auto-remove from queue after 2 seconds
        setTimeout(() => {
          setUploadQueue((prev) => prev.filter((u) => u.id !== upload.id));
        }, 2000);

      } catch (err) {
        logger.error('Upload error:', err);
        setUploadQueue((prev) =>
          prev.map((u) =>
            u.id === upload.id
              ? {
                  ...u,
                  status: 'failed',
                  error: err instanceof Error ? err.message : 'Upload failed',
                }
              : u
          )
        );
      }
    }
  };

  const clearCompleted = () => {
    setUploadQueue((prev) => prev.filter((u) => u.status !== 'completed'));
  };

  const toggleSelectContract = (documentId: string) => {
    setSelectedContracts((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(documentId)) {
        newSet.delete(documentId);
      } else {
        newSet.add(documentId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    const filteredContracts = getFilteredAndSortedContracts();
    if (selectedContracts.size === filteredContracts.length && filteredContracts.length > 0) {
      setSelectedContracts(new Set());
    } else {
      setSelectedContracts(new Set(filteredContracts.map((c) => c.document_id)));
    }
  };

  const deleteSelectedContracts = async () => {
    if (selectedContracts.size === 0) return;

    const confirmMessage =
      selectedContracts.size === 1
        ? 'Are you sure you want to delete this contract?'
        : `Are you sure you want to delete ${selectedContracts.size} contracts?`;

    if (!confirm(confirmMessage)) return;

    try {
      setIsDeleting(true);
      const idsArray = Array.from(selectedContracts);

      // Build query string with multiple document_ids parameters
      const queryString = idsArray.map((id) => `document_ids=${id}`).join('&');

      // Use apiDelete helper which automatically handles token refresh
      await apiDelete(`/api/contracts?${queryString}`);

      // Refresh the list and clear selection
      await fetchContracts();
      setSelectedContracts(new Set());
      setError(null);
    } catch (err) {
      logger.error('Error deleting contracts:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete contracts');
    } finally {
      setIsDeleting(false);
    }
  };

  const reprocessSelectedContracts = async () => {
    if (selectedContracts.size === 0) return;

    const confirmMessage =
      selectedContracts.size === 1
        ? 'Are you sure you want to reprocess this contract?'
        : `Are you sure you want to reprocess ${selectedContracts.size} contracts?`;

    if (!confirm(confirmMessage)) return;

    try {
      setIsReprocessing(true);
      const idsArray = Array.from(selectedContracts);

      // Call reprocess endpoint for each selected contract
      await Promise.all(
        idsArray.map((documentId) =>
          apiPost(`/api/contracts/${documentId}/reprocess`, {})
        )
      );

      // Refresh the list and clear selection
      await fetchContracts();
      setSelectedContracts(new Set());
      setError(null);
    } catch (err) {
      logger.error('Error reprocessing contracts:', err);
      setError(err instanceof Error ? err.message : 'Failed to reprocess contracts');
    } finally {
      setIsReprocessing(false);
    }
  };

  // Filter and sort contracts
  const getFilteredAndSortedContracts = () => {
    let filtered = [...contracts];

    // Apply filters
    if (filterStatus !== 'all') {
      filtered = filtered.filter((c) => c.status === filterStatus);
    }
    if (filterRiskLevel !== 'all') {
      filtered = filtered.filter((c) => c.risk_level === filterRiskLevel);
    }
    if (filterContractType !== 'all') {
      filtered = filtered.filter((c) => c.contract_type === filterContractType);
    }
    if (filterReview !== 'all') {
      if (filterReview === 'required') {
        filtered = filtered.filter((c) => c.human_review_required === true);
      } else if (filterReview === 'not_required') {
        filtered = filtered.filter((c) => c.human_review_required === false);
      }
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal, bVal;

      switch (sortField) {
        case 'uploaded_at':
          aVal = new Date(a.uploaded_at).getTime();
          bVal = new Date(b.uploaded_at).getTime();
          break;
        case 'risk_level':
          const riskOrder: Record<string, number> = { high: 3, medium: 2, low: 1 };
          aVal = a.risk_level ? (riskOrder[a.risk_level] || 0) : 0;
          bVal = b.risk_level ? (riskOrder[b.risk_level] || 0) : 0;
          break;
        case 'contract_type':
          aVal = a.contract_type || '';
          bVal = b.contract_type || '';
          break;
        case 'status':
          aVal = a.status || '';
          bVal = b.status || '';
          break;
        default:
          return 0;
      }

      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
      }
    });

    return filtered;
  };

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getRiskBadge = (riskLevel: string) => {
    const badges = {
      high: 'bg-red-100 text-red-800 border-red-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-green-100 text-green-800 border-green-300',
    };
    return badges[riskLevel as keyof typeof badges] || badges.medium;
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      routing: 'bg-blue-100 text-blue-800',
      final_analysis: 'bg-purple-100 text-purple-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return badges[status as keyof typeof badges] || badges.routing;
  };

  const getStatusLabel = (status: string) => {
    const labels = {
      routing: 'Routing',
      final_analysis: 'Analyzing',
      completed: 'Completed',
      failed: 'Failed',
      approved: 'Approved',
      rejected: 'Rejected',
    };
    return labels[status as keyof typeof labels] || 'Unknown';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-primary">Contract Upload & Review</h1>
      </div>

      {error && (
        <div className="bg-red-50/20 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'all'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          All Contracts ({contracts.length})
        </button>
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'upload'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          Upload
        </button>
      </div>

      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-4">Upload Contracts</h2>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary bg-primary-50'
                : 'border-border hover:border-primary-400 hover:bg-hover'
            }`}
          >
            <input {...getInputProps()} />
            <div className="text-4xl mb-3">📄</div>
            {isDragActive ? (
              <p className="text-primary font-medium">Drop contracts here...</p>
            ) : (
              <>
                <p className="text-primary font-medium mb-2">
                  Drop contracts here or click to browse
                </p>
                <p className="text-sm text-muted">
                  Supported: PDF, DOCX, TXT • Max size: 10MB per file
                </p>
                <p className="text-sm text-muted mt-1">
                  AI will automatically detect contract type
                </p>
              </>
            )}
          </div>

          {/* Redact Toggle */}
          <div className="mt-4 flex items-center justify-between p-4 border rounded-lg" style={{ borderColor: 'var(--color-border-default)', backgroundColor: 'var(--color-bg-card)' }}>
            <div className="flex-1">
              <label htmlFor="redact-toggle" className="block text-sm font-medium mb-1 cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                Redact Confidential Information
              </label>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                id="redact-toggle"
                checked={redact}
                onChange={(e) => setRedact(e.target.checked)}
                className="sr-only peer"
              />
              <div
                className="w-11 h-6 rounded-full peer peer-focus:outline-none peer-focus:ring-4 transition-colors"
                style={{
                  backgroundColor: redact ? 'var(--color-primary)' : '#e5e7eb',
                  boxShadow: redact ? '0 0 0 4px rgba(20, 184, 166, 0.2)' : 'none'
                }}
              >
                <div
                  className="absolute top-[2px] left-[2px] bg-white border border-gray-300 rounded-full h-5 w-5 transition-transform"
                  style={{
                    transform: redact ? 'translateX(20px)' : 'translateX(0)'
                  }}
                ></div>
              </div>
            </label>
          </div>

          {/* Upload Queue */}
          {uploadQueue.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-primary">Upload Queue</h3>
                <button
                  onClick={clearCompleted}
                  className="text-xs text-muted hover:text-primary"
                >
                  Clear Completed
                </button>
              </div>
              <div className="space-y-2">
                {uploadQueue
                  .filter((upload) => upload.status !== 'completed')
                  .map((upload) => (
                    <div
                      key={upload.id}
                      className="flex items-center justify-between p-3 bg-hover rounded-lg"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-primary truncate">
                          {upload.file.name}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${getStatusBadge(
                              upload.status
                            )}`}
                          >
                            {upload.status.charAt(0).toUpperCase() + upload.status.slice(1)}
                          </span>
                          {upload.error && (
                            <span className="text-xs text-red-600">{upload.error}</span>
                          )}
                        </div>
                      </div>
                      <div className="ml-4">
                        {upload.status === 'failed' ? (
                          <span className="text-red-600 text-xl">✗</span>
                        ) : (
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all"
                              style={{ width: `${upload.progress}%` }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Upload Button */}
          {uploadQueue.some((u) => u.status === 'queued') && (
            <div className="mt-4">
              <button onClick={uploadContracts} className="btn-primary">
                Upload & Analyze ({uploadQueue.filter((u) => u.status === 'queued').length}{' '}
                {uploadQueue.filter((u) => u.status === 'queued').length === 1
                  ? 'contract'
                  : 'contracts'}
                )
              </button>
            </div>
          )}
        </div>
      )}

      {/* All Contracts Tab */}
      {activeTab === 'all' && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-primary">All Contracts</h2>

            {selectedContracts.size > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-secondary">
                  {selectedContracts.size} selected
                </span>
                <button
                  onClick={reprocessSelectedContracts}
                  disabled={isReprocessing}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                  {isReprocessing ? 'Reprocessing...' : 'Reprocess Selected'}
                </button>
                <button
                  onClick={deleteSelectedContracts}
                  disabled={isDeleting}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                >
                  {isDeleting ? 'Deleting...' : 'Delete Selected'}
                </button>
              </div>
            )}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4 mb-4 pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-secondary">Status:</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-3 py-1.5 rounded border border-border bg-card text-primary text-sm"
              >
                <option value="all">All</option>
                <option value="routing">Routing</option>
                <option value="final_analysis">Analyzing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-secondary">Risk:</label>
              <select
                value={filterRiskLevel}
                onChange={(e) => setFilterRiskLevel(e.target.value)}
                className="px-3 py-1.5 rounded border border-border bg-card text-primary text-sm"
              >
                <option value="all">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-secondary">Type:</label>
              <select
                value={filterContractType}
                onChange={(e) => setFilterContractType(e.target.value)}
                className="px-3 py-1.5 rounded border border-border bg-card text-primary text-sm"
              >
                <option value="all">All</option>
                {Array.from(new Set(contracts.map(c => c.contract_type).filter(Boolean))).sort().map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-secondary">Review:</label>
              <select
                value={filterReview}
                onChange={(e) => setFilterReview(e.target.value)}
                className="px-3 py-1.5 rounded border border-border bg-card text-primary text-sm"
              >
                <option value="all">All</option>
                <option value="required">Required</option>
                <option value="not_required">Not Required</option>
              </select>
            </div>

            <button
              onClick={() => {
                setFilterStatus('all');
                setFilterRiskLevel('all');
                setFilterContractType('all');
                setFilterReview('all');
              }}
              className="ml-auto text-sm text-primary hover:underline"
            >
              Clear Filters
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="md" />
            </div>
          ) : contracts.length === 0 ? (
            <div className="text-center py-8 text-muted">
              No contracts uploaded yet. Upload your first contract to get started.
            </div>
          ) : (
            <div>
              <table className="w-full table-fixed">
                <thead>
                  <tr className="border-b border-border">
                    <th className="w-10 py-3 px-2">
                      <input
                        type="checkbox"
                        checked={selectedContracts.size === getFilteredAndSortedContracts().length && getFilteredAndSortedContracts().length > 0}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                      />
                    </th>
                    <th className="w-[25%] text-left py-3 px-2 text-base font-bold text-secondary">
                      Contract Name
                    </th>
                    <th className="w-[20%] text-left py-3 px-2 text-base font-bold text-secondary">
                      Counterparty
                    </th>
                    <th
                      className="w-[10%] text-left py-3 px-2 text-base font-bold text-secondary cursor-pointer hover:text-primary"
                      onClick={() => handleSort('contract_type')}
                    >
                      <div className="flex items-center gap-1">
                        Type
                        {sortField === 'contract_type' && (
                          <span className="text-xs">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </div>
                    </th>
                    <th className="w-[9%] text-left py-3 px-2 text-base font-bold text-secondary">
                      Value
                    </th>
                    <th
                      className="w-[7%] text-left py-3 px-2 text-base font-bold text-secondary cursor-pointer hover:text-primary"
                      onClick={() => handleSort('risk_level')}
                    >
                      <div className="flex items-center gap-1">
                        Risk
                        {sortField === 'risk_level' && (
                          <span className="text-xs">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </div>
                    </th>
                    <th className="w-[5%] text-left py-3 px-2 text-base font-bold text-secondary">
                      Review
                    </th>
                    <th
                      className="w-[9%] text-left py-3 px-2 pl-6 text-base font-bold text-secondary cursor-pointer hover:text-primary"
                      onClick={() => handleSort('status')}
                    >
                      <div className="flex items-center gap-1">
                        Status
                        {sortField === 'status' && (
                          <span className="text-xs">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </div>
                    </th>
                    <th className="w-[8%] text-center py-3 px-2 text-base font-bold text-secondary">
                      Uploaded
                    </th>
                    <th className="w-[7%] text-left py-3 px-2 text-base font-bold text-secondary">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {getFilteredAndSortedContracts().map((contract) => (
                    <tr key={contract.id} className="border-b border-border hover:bg-hover">
                      <td className="py-3 px-2">
                        <input
                          type="checkbox"
                          checked={selectedContracts.has(contract.document_id)}
                          onChange={() => toggleSelectContract(contract.document_id)}
                          className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-2 text-sm text-primary font-medium break-words">
                        {contract.filename}
                      </td>
                      <td className="py-3 px-2 text-sm text-secondary break-words">
                        {contract.counterparty_name || '—'}
                      </td>
                      <td className="py-3 px-2 text-sm text-secondary capitalize break-words">
                        {contract.router_classification ? (
                          <button
                            onClick={() => setShowRouterModal(contract.router_classification!)}
                            className="text-xs px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors capitalize font-medium"
                            title={`${contract.router_classification.confidence_score}% confidence - Click for details`}
                          >
                            {contract.router_classification.classification === 'employment'
                              ? 'employ'
                              : contract.router_classification.classification}
                          </button>
                        ) : (
                          contract.contract_type || '—'
                        )}
                      </td>
                      <td className="py-3 px-2 text-sm text-secondary">
                        {contract.status === 'routing' || contract.status === 'final_analysis' ? (
                          <span className="italic text-muted">—</span>
                        ) : contract.total_value ? (
                          `$${contract.total_value.toLocaleString()}`
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-3 px-2">
                        {contract.status === 'routing' || contract.status === 'final_analysis' ? (
                          <span className="text-xs text-secondary italic">
                            Pending...
                          </span>
                        ) : contract.status === 'failed' ? (
                          <span className="text-xs text-secondary italic">—</span>
                        ) : contract.status === 'completed' && contract.risk_level ? (
                          <span
                            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium border ${getRiskBadge(
                              contract.risk_level
                            )}`}
                          >
                            {contract.risk_level.toUpperCase()}
                            <span className="text-[10px] opacity-75">
                              ({contract.risk_score ?? 'N/A'})
                            </span>
                          </span>
                        ) : (
                          <span className="text-xs text-secondary italic">—</span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-center">
                        {contract.status === 'routing' || contract.status === 'final_analysis' || contract.status === 'failed' ? (
                          <span className="text-xs text-secondary italic">—</span>
                        ) : contract.human_review_required ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 bg-yellow-100 text-yellow-800 rounded-full text-xs font-bold">
                            !
                          </span>
                        ) : (
                          <span className="text-xs text-muted">—</span>
                        )}
                      </td>
                      <td className="py-3 px-2 pl-6">
                        {contract.status === 'routing' || contract.status === 'final_analysis' ? (
                          <span
                            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${getStatusBadge(
                              contract.status
                            )}`}
                          >
                            <span className="animate-spin">⟳</span>
                            {getStatusLabel(contract.status)}
                          </span>
                        ) : (
                          <span
                            className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${getStatusBadge(
                              contract.status
                            )}`}
                          >
                            {getStatusLabel(contract.status)}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-xs text-secondary text-center">
                        {new Date(contract.uploaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </td>
                      <td className="py-3 px-2">
                        {contract.status === 'routing' || contract.status === 'final_analysis' ? (
                          <span className="text-sm text-secondary">—</span>
                        ) : contract.status === 'failed' ? (
                          <span className="text-sm text-red-600 italic" title={contract.error_message || 'Unknown error'}>
                            {contract.error_message ? (
                              <details className="cursor-pointer">
                                <summary className="hover:underline">Processing failed (click for details)</summary>
                                <div className="mt-2 p-2 bg-red-50 rounded text-xs max-w-md">
                                  {contract.error_message}
                                </div>
                              </details>
                            ) : (
                              'Processing failed'
                            )}
                          </span>
                        ) : contract.status === 'completed' || contract.status === 'approved' || contract.status === 'rejected' ? (
                          <Link
                            href={`/admin/contracts/${contract.document_id}`}
                            className="text-sm text-primary hover:underline"
                          >
                            View Report
                          </Link>
                        ) : (
                          <span className="text-sm text-secondary">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Router Classification Modal */}
      <RouterClassificationModal
        open={showRouterModal !== null}
        classification={showRouterModal}
        onClose={() => setShowRouterModal(null)}
      />
    </div>
  );
}
