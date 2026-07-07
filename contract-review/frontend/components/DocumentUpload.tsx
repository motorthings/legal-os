'use client'

import { useState, useRef } from 'react'
import { API_BASE_URL } from '@/lib/config'
import { authenticatedFetch } from '@/lib/api'

interface DocumentUploadProps {
  clientId?: string  // Optional - backend auto-assigns default client
  apiBaseUrl?: string
  onUploadComplete?: () => void
}

interface UploadStatus {
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error'
  message: string
  progress?: number
}

export default function DocumentUpload({
  clientId,
  apiBaseUrl = API_BASE_URL,
  onUploadComplete
}: DocumentUploadProps) {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    message: ''
  })
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setUploadStatus({ status: 'idle', message: '' })
    }
  }

  async function handleUpload() {
    if (!selectedFile) return

    // Check if file is empty
    if (selectedFile.size === 0) {
      setUploadStatus({
        status: 'error',
        message: 'Error: File is empty. Please select a file with content.',
        progress: 0
      })
      return
    }

    try {
      // Step 1: Upload file
      setUploadStatus({
        status: 'uploading',
        message: `Uploading ${selectedFile.name}...`,
        progress: 0
      })

      const formData = new FormData()
      formData.append('file', selectedFile)

      const uploadResponse = await authenticatedFetch(`${apiBaseUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData
      })

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`)
      }

      const uploadData = await uploadResponse.json()
      const documentId = uploadData.document_id

      setUploadStatus({
        status: 'uploading',
        message: 'Upload complete! Processing document...',
        progress: 50
      })

      // Step 2: Process document (chunk and embed)
      setUploadStatus({
        status: 'processing',
        message: 'Chunking text and generating embeddings...',
        progress: 60
      })

      const processResponse = await authenticatedFetch(
        `${apiBaseUrl}/api/documents/${documentId}/process`,
        {
          method: 'POST'
        }
      )

      if (!processResponse.ok) {
        throw new Error(`Processing failed: ${processResponse.statusText}`)
      }

      const processData = await processResponse.json()

      setUploadStatus({
        status: 'complete',
        message: `Success! Created ${processData.chunks_created} searchable chunks`,
        progress: 100
      })

      // Clear the file input after successful upload
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete()
      }

      // Reset after 3 seconds
      setTimeout(() => {
        setUploadStatus({ status: 'idle', message: '' })
      }, 3000)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setUploadStatus({
        status: 'error',
        message: `Error: ${errorMessage}`,
        progress: 0
      })
    }
  }

  return (
    <div>
      {/* File Input */}
      <div className="mb-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.docx,.doc,.csv,.json,.xml"
          onChange={handleFileSelect}
          disabled={uploadStatus.status === 'uploading' || uploadStatus.status === 'processing'}
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-teal-500 file:text-white hover:file:bg-teal-600"
        />
        {selectedFile && (
          <p className="text-sm text-gray-600 mt-2">
            Selected: <span className="font-medium">{selectedFile.name}</span> ({(selectedFile.size / 1024).toFixed(1)} KB)
          </p>
        )}
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploadStatus.status === 'uploading' || uploadStatus.status === 'processing'}
        className="w-full btn-primary"
      >
        {uploadStatus.status === 'uploading' ? 'Uploading...' :
         uploadStatus.status === 'processing' ? 'Processing...' :
         'Upload & Process'}
      </button>

      {/* Progress Bar */}
      {(uploadStatus.status === 'uploading' || uploadStatus.status === 'processing') && uploadStatus.progress !== undefined && (
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-teal-400 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadStatus.progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Status Message */}
      {uploadStatus.message && (
        <div className={`mt-4 p-3 rounded-lg text-sm ${
          uploadStatus.status === 'complete' ? 'bg-teal-50 text-teal-700' :
          uploadStatus.status === 'error' ? 'bg-red-50 text-red-800' :
          'bg-teal-100 text-teal-700'
        }`}>
          {uploadStatus.message}
        </div>
      )}

      {/* Supported Formats */}
      <div className="mt-4 text-xs text-gray-500">
        <p className="font-semibold mb-1">Supported formats:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>Plain text (.txt, .md)</li>
          <li>Word documents (.docx, .doc)</li>
          <li>Structured data (.csv, .json, .xml)</li>
          <li>Any UTF-8 text file</li>
        </ul>
      </div>
    </div>
  )
}
