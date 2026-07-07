'use client';

import { useState, useEffect, useMemo } from 'react';
import { apiGet, apiDelete, apiPost } from '@/lib/api';
import ConfirmModal from '@/components/ConfirmModal';
import { logger } from '@/lib/logger';

interface Document {
  id: string;
  filename: string;
  file_type: string | null;
  file_size: number;
  client_id: string;
  uploaded_at: string;
  uploaded_by?: string;
  processing_status: string;
  chunk_count: number;
  access_count: number;
  clients?: { name: string };
  users?: { email: string };
}

interface DocumentDetails extends Document {
  client_name?: string;
  uploaded_by_email?: string;
  conversations?: Array<{ id: string; title: string }>;
}

export default function DocumentsPage() {
  // State
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClient, setSelectedClient] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [dateRange, setDateRange] = useState<string>('all');

  // Pagination
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);

  // Sorting
  const [sortBy, setSortBy] = useState<string>('uploaded_at');
  const [sortOrder, setSortOrder] = useState<string>('desc');

  // Selection
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());

  // Detail modal
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [documentDetails, setDocumentDetails] = useState<DocumentDetails | null>(null);

  // Confirm modal
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {}
  });

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setOffset(0); // Reset to first page when search changes
      loadDocuments();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedClient, selectedType, selectedStatus, dateRange, sortBy, sortOrder]);

  // Load on pagination change
  useEffect(() => {
    loadDocuments();
  }, [offset, limit]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      if (searchQuery) params.set('search', searchQuery);
      if (selectedClient) params.set('client_id', selectedClient);
      if (selectedType) params.set('file_type', selectedType);
      if (selectedStatus) params.set('status', selectedStatus);
      if (sortBy) params.set('sort_by', sortBy);
      if (sortOrder) params.set('sort_order', sortOrder);
      params.set('limit', limit.toString());
      params.set('offset', offset.toString());

      // Date range
      if (dateRange !== 'all') {
        const now = new Date();
        const dateFrom = new Date();

        switch (dateRange) {
          case 'week':
            dateFrom.setDate(now.getDate() - 7);
            break;
          case 'month':
            dateFrom.setMonth(now.getMonth() - 1);
            break;
          case 'quarter':
            dateFrom.setMonth(now.getMonth() - 3);
            break;
        }

        params.set('date_from', dateFrom.toISOString());
      }

      const data = await apiGet<{ documents: Document[]; total: number }>(`/api/documents?${params.toString()}`);
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = () => {
    if (selectedDocuments.size === documents.length) {
      setSelectedDocuments(new Set());
    } else {
      setSelectedDocuments(new Set(documents.map(d => d.id)));
    }
  };

  const handleSelectDocument = (docId: string) => {
    const newSelected = new Set(selectedDocuments);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocuments(newSelected);
  };

  const handleDelete = (documentId: string) => {
    setConfirmModal({
      open: true,
      title: 'Delete Document',
      message: 'Are you sure you want to delete this document? This action cannot be undone.',
      onConfirm: async () => {
        await deleteDocument(documentId);
      }
    });
  };

  const deleteDocument = async (documentId: string) => {
    try {
      await apiDelete(`/api/documents/${documentId}`);

      // Optimistic update
      setDocuments(prev => prev.filter(d => d.id !== documentId));
      setTotal(prev => prev - 1);
    } catch (err) {
      logger.error('Delete error:', err);
      alert('Failed to delete document');
      loadDocuments(); // Reload on error
    }
  };

  const handleBulkDelete = () => {
    if (selectedDocuments.size === 0) return;

    setConfirmModal({
      open: true,
      title: 'Delete Documents',
      message: `Are you sure you want to delete ${selectedDocuments.size} document(s)? This action cannot be undone.`,
      onConfirm: async () => {
        await bulkDelete();
      }
    });
  };

  const bulkDelete = async () => {
    try {
      const documentIds = Array.from(selectedDocuments);
      const data = await apiDelete<{ deleted: number }>('/api/documents/bulk', { document_ids: documentIds });

      alert(`Successfully deleted ${data.deleted} document(s)`);
      setSelectedDocuments(new Set());
      loadDocuments();
    } catch (err) {
      logger.error('Bulk delete error:', err);
      alert('Failed to delete documents');
    }
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const handleViewDetails = async (document: Document) => {
    setSelectedDocument(document);
    setShowDetailModal(true);
    setDetailLoading(true);

    try {
      const data = await apiGet<{ document: DocumentDetails }>(`/api/documents/${document.id}/details`);
      setDocumentDetails(data.document);
    } catch (err) {
      logger.error('Error loading details:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDownload = async (documentId: string, filename: string) => {
    try {
      const data = await apiGet<{ download_url: string }>(`/api/documents/${documentId}/download`);
      // Open download URL in new tab
      window.open(data.download_url, '_blank');
    } catch (err) {
      logger.error('Download error:', err);
      alert('Failed to download document');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileTypeDisplay = (mimeType: string | null): string => {
    if (!mimeType) return 'Unknown';
    if (mimeType.includes('pdf')) return 'PDF';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'DOCX';
    if (mimeType.includes('csv')) return 'CSV';
    if (mimeType.includes('text')) return 'TXT';
    return mimeType.split('/')[1]?.toUpperCase() || 'Unknown';
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
      completed: { bg: 'bg-green-100', text: 'text-green-800', label: 'Processed' },
      processing: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Processing' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      failed: { bg: 'bg-red-100', text: 'text-red-800', label: 'Failed' },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  if (loading && documents.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted">Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary">Documents</h1>
          <p className="text-muted mt-1">
            Manage all documents across clients
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-default p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Search */}
          <input
            type="text"
            placeholder="Search by filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 border border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14b8a6]"
          />

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-4 py-2 border border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14b8a6]"
          >
            <option value="">All Types</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="csv">CSV</option>
            <option value="txt">TXT</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-4 py-2 border border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14b8a6]"
          >
            <option value="">All Statuses</option>
            <option value="completed">Processed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>

          {/* Date Range */}
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14b8a6]"
          >
            <option value="all">All Time</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
            <option value="quarter">Last 90 Days</option>
          </select>

          {/* Results per page */}
          <select
            value={limit}
            onChange={(e) => {
              setLimit(Number(e.target.value));
              setOffset(0);
            }}
            className="px-4 py-2 border border-default rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14b8a6]"
          >
            <option value="20">20 per page</option>
            <option value="50">50 per page</option>
            <option value="100">100 per page</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedDocuments.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <p className="text-blue-800 font-medium">
              {selectedDocuments.size} document(s) selected
            </p>
            <button
              onClick={handleBulkDelete}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Delete Selected
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">Error: {error}</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg border border-default overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-hover">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedDocuments.size === documents.length && documents.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('filename')}
                >
                  Filename {sortBy === 'filename' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Client
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Type
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('file_size')}
                >
                  Size {sortBy === 'file_size' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Chunks
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500 cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('uploaded_at')}
                >
                  Uploaded {sortBy === 'uploaded_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {documents.map((doc, index) => (
                <tr
                  key={doc.id}
                  className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-100 transition-colors`}
                >
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedDocuments.has(doc.id)}
                      onChange={() => handleSelectDocument(doc.id)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => handleViewDetails(doc)}
                      className="text-primary hover:underline font-medium text-sm truncate max-w-xs block"
                      title={doc.filename}
                    >
                      {doc.filename}
                    </button>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {doc.clients?.name || 'Unknown'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {getFileTypeDisplay(doc.file_type)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {formatFileSize(doc.file_size)}
                  </td>
                  <td className="px-6 py-4">
                    {getStatusBadge(doc.processing_status)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {doc.chunk_count || 0}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {formatDate(doc.uploaded_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleDownload(doc.id, doc.filename)}
                        className="p-1 text-muted hover:text-primary transition-colors"
                        title="Download"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1 text-muted hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {documents.length === 0 && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-600 font-medium">No documents found</p>
            <p className="text-gray-500 text-sm mt-1">Try adjusting your filters</p>
          </div>
        )}

        {/* Pagination */}
        {documents.length > 0 && (
          <div className="bg-hover px-6 py-4 flex items-center justify-between border-t border-default">
            <div className="text-sm text-gray-600">
              Showing {offset + 1}-{Math.min(offset + limit, total)} of {total} documents
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 id="modal-title" className="text-xl font-bold text-gray-900">Document Details</h2>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
                aria-label="Close modal"
              >
                ×
              </button>
            </div>

            {/* Modal Content */}
            <div className="px-6 py-4">
              {detailLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                </div>
              ) : documentDetails ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-medium uppercase text-gray-500">Filename</label>
                    <p className="text-sm text-gray-900 mt-1">{documentDetails.filename}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase text-gray-500">Client</label>
                    <p className="text-sm text-gray-900 mt-1">{documentDetails.client_name || 'Unknown'}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Type</label>
                      <p className="text-sm text-gray-900 mt-1">{getFileTypeDisplay(documentDetails.file_type)}</p>
                    </div>
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Size</label>
                      <p className="text-sm text-gray-900 mt-1">{formatFileSize(documentDetails.file_size)}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Status</label>
                      <div className="mt-1">{getStatusBadge(documentDetails.processing_status)}</div>
                    </div>
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Chunks</label>
                      <p className="text-sm text-gray-900 mt-1">{documentDetails.chunk_count || 0}</p>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium uppercase text-gray-500">Uploaded</label>
                    <p className="text-sm text-gray-900 mt-1">{formatDate(documentDetails.uploaded_at)}</p>
                  </div>
                  {documentDetails.uploaded_by_email && (
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Uploaded By</label>
                      <p className="text-sm text-gray-900 mt-1">{documentDetails.uploaded_by_email}</p>
                    </div>
                  )}
                  {documentDetails.conversations && documentDetails.conversations.length > 0 && (
                    <div>
                      <label className="text-xs font-medium uppercase text-gray-500">Related Conversations</label>
                      <div className="mt-2 space-y-2">
                        {documentDetails.conversations.slice(0, 5).map((conv) => (
                          <div key={conv.id} className="text-sm text-gray-700 border-l-2 border-gray-300 pl-2">
                            {conv.title || 'Untitled'}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Modal Actions */}
            <div className="sticky bottom-0 bg-gray-50 px-6 py-4 flex items-center justify-end gap-2 border-t border-gray-200">
              <button
                onClick={() => handleDownload(selectedDocument.id, selectedDocument.filename)}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90"
              >
                Download
              </button>
              <button
                onClick={() => {
                  setShowDetailModal(false);
                  handleDelete(selectedDocument.id);
                }}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Delete
              </button>
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Modal */}
      <ConfirmModal
        open={confirmModal.open}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, open: false })}
      />
    </div>
  );
}
