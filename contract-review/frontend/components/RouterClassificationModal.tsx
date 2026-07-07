'use client'

import { useEffect } from 'react'

interface RouterClassification {
  classification: string
  confidence_score: number
  reasoning: string
  key_signals?: string[]
  alternative_classification?: string | null
  document_metadata?: {
    has_title?: boolean
    apparent_counterparty?: string
    document_length?: string
  }
}

interface RouterClassificationModalProps {
  open: boolean
  classification: RouterClassification | null
  onClose: () => void
}

export default function RouterClassificationModal({
  open,
  classification,
  onClose
}: RouterClassificationModalProps) {
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose()
      }
    }

    if (open) {
      document.addEventListener('keydown', handleEscape)
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [open, onClose])

  if (!open || !classification) return null

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 90) {
      return 'bg-green-100 text-green-800 border-green-300'
    } else if (confidence >= 70) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    } else {
      return 'bg-red-100 text-red-800 border-red-300'
    }
  }

  const getClassificationColor = (type: string) => {
    const colors: Record<string, string> = {
      vendor: 'text-blue-700',
      customer: 'text-purple-700',
      employment: 'text-orange-700',
      dpa: 'text-red-700',
      general: 'text-gray-700',
      other: 'text-teal-700',
    }
    return colors[type] || 'text-gray-700'
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            id="modal-title"
            className="text-xl font-semibold text-gray-900"
          >
            Router Classification
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Classification Type and Confidence */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-sm font-medium text-gray-600">Contract Type:</span>
            <span className={`text-lg font-bold capitalize ${getClassificationColor(classification.classification)}`}>
              {classification.classification}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-600">Confidence:</span>
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${getConfidenceBadge(classification.confidence_score)}`}
            >
              {classification.confidence_score}%
            </span>
          </div>
        </div>

        {/* Reasoning */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Reasoning</h3>
          <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 border border-gray-200">
            {classification.reasoning}
          </p>
        </div>

        {/* Key Signals */}
        {classification.key_signals && classification.key_signals.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Key Signals</h3>
            <ul className="space-y-2">
              {classification.key_signals.map((signal, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span>{signal}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Alternative Classification */}
        {classification.alternative_classification && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Alternative Classification</h3>
            <p className="text-sm text-gray-700">
              If confidence was lower, this would be classified as:{' '}
              <span className={`font-semibold capitalize ${getClassificationColor(classification.alternative_classification)}`}>
                {classification.alternative_classification}
              </span>
            </p>
          </div>
        )}

        {/* Document Metadata */}
        {classification.document_metadata && Object.keys(classification.document_metadata).length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Document Metadata</h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-2">
              {classification.document_metadata.has_title !== undefined && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-gray-600">Has Title:</span>
                  <span className="text-gray-700">{classification.document_metadata.has_title ? 'Yes' : 'No'}</span>
                </div>
              )}
              {classification.document_metadata.apparent_counterparty && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-gray-600">Counterparty:</span>
                  <span className="text-gray-700">{classification.document_metadata.apparent_counterparty}</span>
                </div>
              )}
              {classification.document_metadata.document_length && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-gray-600">Length:</span>
                  <span className="text-gray-700">{classification.document_metadata.document_length}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Close Button */}
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-md hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
