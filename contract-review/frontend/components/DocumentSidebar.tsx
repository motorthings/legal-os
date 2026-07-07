'use client'

import { useState, useEffect } from 'react'
import { authenticatedFetch, apiGet } from '@/lib/api'
import { logger } from '@/lib/logger'
import LoadingSpinner from './LoadingSpinner'
import { API_BASE_URL } from '@/lib/config'

interface Document {
  id: string
  filename: string
  uploaded_at: string
  processed: boolean
  is_core_document?: boolean
}

interface DocumentSidebarProps {
  clientId?: string  // Optional - backend auto-assigns default client
  apiBaseUrl?: string
  className?: string
}

export default function DocumentSidebar({
  clientId,
  apiBaseUrl = API_BASE_URL,
  className = ''
}: DocumentSidebarProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  useEffect(() => {
    loadDocuments(true)
  }, [])

  // Auto-refresh when there are unprocessed documents
  useEffect(() => {
    const hasUnprocessedDocs = documents.some(doc => !doc.processed)

    if (hasUnprocessedDocs) {
      const intervalId = setInterval(() => {
        loadDocuments()
      }, 3000)  // Poll every 3 seconds

      return () => clearInterval(intervalId)
    }
  }, [documents])

  async function loadDocuments(showLoading = false) {
    try {
      if (showLoading) {
        setLoading(true)
      }
      // Use new user-based endpoint - users only see their own documents
      const data = await apiGet<{ documents: Document[] }>(`/api/users/me/documents`)
      setDocuments(data.documents || [])
    } catch (err) {
      logger.error('Error loading documents:', err)
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setUploading(true)
      setUploadProgress(30)

      const formData = new FormData()
      formData.append('file', file)
      if (clientId) {
        formData.append('client_id', clientId)
      }

      const uploadResponse = await authenticatedFetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      })

      if (!uploadResponse.ok) throw new Error('Upload failed')

      const uploadData = await uploadResponse.json()
      setUploadProgress(60)

      // Process document
      const processResponse = await authenticatedFetch(
        `/api/documents/${uploadData.document_id}/process`,
        { method: 'POST' }
      )

      if (!processResponse.ok) throw new Error('Processing failed')

      setUploadProgress(100)

      // Reload documents
      await loadDocuments()

      // Reset
      e.target.value = ''
      setTimeout(() => {
        setUploadProgress(0)
        setUploading(false)
      }, 1000)
    } catch (err) {
      logger.error('Upload error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Upload failed'
      alert(`Failed to upload document: ${errorMessage}`)
      setUploading(false)
      setUploadProgress(0)
      e.target.value = ''
    }
  }

  return (
    <div className={`flex flex-col h-full bg-card border-l border-default ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-default">
        <h2 className="heading-3 mb-3">Documents</h2>

        {/* Upload Button */}
        <label className={`btn-primary block text-sm text-center cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.csv,.txt"
            onChange={handleFileUpload}
            disabled={uploading}
            className="hidden"
          />
          {uploading ? 'Uploading...' : '+ Upload File'}
        </label>

        {/* Progress Bar */}
        {uploading && (
          <div className="mt-2">
            <div className="progress-bar-container">
              <div
                className="progress-bar-fill"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <div className="text-center py-8 text-muted">
            <div className="flex justify-center mb-2">
              <LoadingSpinner size="sm" />
            </div>
            <div className="text-xs">Loading...</div>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 text-sm text-muted">
            No documents yet
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="p-3 rounded-lg transition-all hover:opacity-80 bg-hover"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-primary truncate">
                      {doc.filename}
                    </div>
                    {doc.is_core_document && (
                      <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                        ⭐ Core Document
                      </div>
                    )}
                  </div>
                  <div>
                    {doc.processed ? (
                      <span className="badge-primary">✓</span>
                    ) : (
                      <span className="badge-secondary">⏳</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {documents.length > 0 && (
        <div className="p-3 border-t border-default">
          <div className="text-xs text-muted">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
          </div>
        </div>
      )}
    </div>
  )
}
