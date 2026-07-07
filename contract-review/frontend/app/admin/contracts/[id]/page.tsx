'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiGet } from '@/lib/api'
import { logger } from '@/lib/logger'
import LoadingSpinner from '@/components/LoadingSpinner'

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

interface RiskFactor {
  category: string
  severity: 'high' | 'medium' | 'low'
  description: string
  recommendation: string
}

interface ContractAnalysis {
  id: string
  document_id: string
  contract_type: string
  parties: string[]
  effective_date: string | null
  expiration_date: string | null
  total_value: number | null
  overall_risk_level: 'high' | 'medium' | 'low'
  risk_score: number
  human_review_required: boolean
  review_status: string
  executive_summary: string
  key_terms: any
  obligations: any
  risk_factors: RiskFactor[]
  full_analysis: {
    router_classification?: RouterClassification
    [key: string]: any
  }
  documents: {
    filename: string
    counterparty_name: string
    uploaded_by: string
    uploaded_at: string
    storage_url: string
  }
  team_feedback?: string
  feedback_submitted_at?: string
  created_at: string
  router_processing_seconds?: number
  analysis_processing_seconds?: number
}

type TabType = 'analysis' | 'router' | 'feedback'

export default function ContractDetailPage() {
  const params = useParams()
  const router = useRouter()
  const contractId = params?.id as string

  const [activeTab, setActiveTab] = useState<TabType>('analysis')
  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [teamFeedback, setTeamFeedback] = useState('')
  const [submittingFeedback, setSubmittingFeedback] = useState(false)

  useEffect(() => {
    if (contractId) {
      fetchContractAnalysis()
    }
  }, [contractId])

  const fetchContractAnalysis = async () => {
    try {
      setLoading(true)
      const data = await apiGet<{ success: boolean; analysis: ContractAnalysis }>(
        `/api/contracts/${contractId}`
      )

      if (data.success && data.analysis) {
        setAnalysis(data.analysis)
        setError(null)
      } else {
        setError('Contract analysis not found')
      }
    } catch (err) {
      logger.error('Error fetching contract analysis:', err)
      setError(err instanceof Error ? err.message : 'Failed to load contract')
    } finally {
      setLoading(false)
    }
  }

  const getRiskBadge = (riskLevel: string) => {
    const badges = {
      high: 'bg-red-100 text-red-800 border-red-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-green-100 text-green-800 border-green-300',
    }
    return badges[riskLevel as keyof typeof badges] || badges.medium
  }

  const getSeverityBadge = (severity: string) => {
    const badges = {
      high: 'bg-red-100 text-red-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-blue-100 text-blue-800',
    }
    return badges[severity as keyof typeof badges] || badges.medium
  }

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

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error || 'Contract not found'}</p>
        </div>
        <button
          onClick={() => router.push('/admin/contracts')}
          className="text-sm text-primary hover:underline"
        >
          ← Back to Contracts
        </button>
      </div>
    )
  }

  const routerClassification = analysis.full_analysis?.router_classification

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push('/admin/contracts')}
          className="text-sm text-secondary hover:text-primary mb-4 inline-flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Contracts
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-primary">{analysis.documents.filename}</h1>
            {analysis.documents.counterparty_name && (
              <p className="text-lg text-secondary mt-1">
                Counterparty: {analysis.documents.counterparty_name}
              </p>
            )}
          </div>

        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'analysis'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Analysis Report
          </button>
          <button
            onClick={() => setActiveTab('router')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'router'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Router Classification
          </button>
          <button
            onClick={() => setActiveTab('feedback')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'feedback'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Team Feedback
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'analysis' && (
        <div className="space-y-6">
          {/* Risk Indicators */}
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${getRiskBadge(
                analysis.overall_risk_level
              )}`}
            >
              {analysis.overall_risk_level.toUpperCase()} RISK
              <span className="text-xs opacity-75">({analysis.risk_score ?? 'N/A'})</span>
            </span>
            {analysis.human_review_required && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
                <span className="text-lg">⚠</span>
                Human Review Required
              </span>
            )}
          </div>

          {/* Executive Summary */}
          <div className="card p-6">
            <h2 className="text-xl font-semibold text-primary mb-4">Executive Summary</h2>
            {typeof analysis.executive_summary === 'string' && !analysis.executive_summary.trim().startsWith('{') ? (
              <p className="text-secondary leading-relaxed whitespace-pre-wrap">{analysis.executive_summary}</p>
            ) : (
              <div className="space-y-4">
                {(() => {
                  try {
                    const summary = typeof analysis.executive_summary === 'string'
                      ? JSON.parse(analysis.executive_summary)
                      : analysis.executive_summary;

                    return (
                      <>
                        {summary.contract_overview && (
                          <div>
                            <h3 className="text-sm font-semibold text-primary mb-2">Contract Overview</h3>
                            <p className="text-sm text-secondary">{summary.contract_overview}</p>
                          </div>
                        )}

                        {summary.key_findings && Array.isArray(summary.key_findings) && summary.key_findings.length > 0 && (
                          <div>
                            <h3 className="text-sm font-semibold text-primary mb-2">Key Findings</h3>
                            <ul className="space-y-2">
                              {summary.key_findings.map((finding: string, idx: number) => (
                                <li key={idx} className="text-sm text-secondary flex gap-2">
                                  <span className="text-primary flex-shrink-0">•</span>
                                  <span>{finding}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {summary.recommendation && (
                          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
                            <h3 className="text-sm font-semibold text-primary mb-2">Recommendation</h3>
                            <p className="text-sm text-secondary">{summary.recommendation}</p>
                          </div>
                        )}
                      </>
                    );
                  } catch (e) {
                    return <p className="text-secondary leading-relaxed whitespace-pre-wrap">{String(analysis.executive_summary)}</p>;
                  }
                })()}
              </div>
            )}
          </div>

          {/* Contract Details */}
          <div className="card p-6">
            <h2 className="text-xl font-semibold text-primary mb-4">Contract Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-secondary">Type</p>
                <p className="text-primary capitalize">{analysis.contract_type}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-secondary">Total Value</p>
                <p className="text-primary">
                  {analysis.total_value ? `$${analysis.total_value.toLocaleString()}` : '—'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-secondary">Effective Date</p>
                <p className="text-primary">
                  {analysis.effective_date
                    ? new Date(analysis.effective_date).toLocaleDateString()
                    : '—'}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-secondary">Expiration Date</p>
                <p className="text-primary">
                  {analysis.expiration_date
                    ? new Date(analysis.expiration_date).toLocaleDateString()
                    : '—'}
                </p>
              </div>
            </div>

            {analysis.parties && Array.isArray(analysis.parties) && analysis.parties.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-secondary mb-2">Parties</p>
                <ul className="list-disc list-inside space-y-1">
                  {analysis.parties.map((party, index) => (
                    <li key={index} className="text-primary">
                      {party}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Risk Factors */}
          {analysis.risk_factors && Array.isArray(analysis.risk_factors) && analysis.risk_factors.length > 0 && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold text-primary mb-4">Risk Factors</h2>
              <div className="space-y-4">
                {analysis.risk_factors.map((risk, index) => (
                  <div
                    key={index}
                    className="border border-border rounded-lg p-4 hover:bg-hover transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-primary">{risk.category}</h3>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getSeverityBadge(
                          risk.severity
                        )}`}
                      >
                        {risk.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-secondary mb-2">{risk.description}</p>
                    <div className="bg-blue-50 border border-blue-200 rounded p-3 mt-2">
                      <p className="text-sm text-blue-900">
                        <span className="font-medium">Recommendation:</span> {risk.recommendation}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="card p-6">
            <h2 className="text-xl font-semibold text-primary mb-4">Metadata</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-medium text-secondary">Uploaded At</p>
                <p className="text-primary">
                  {new Date(analysis.documents.uploaded_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="font-medium text-secondary">Analyzed At</p>
                <p className="text-primary">{new Date(analysis.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p className="font-medium text-secondary">Review Status</p>
                <p className="text-primary capitalize">{analysis.review_status}</p>
              </div>
              <div>
                <p className="font-medium text-secondary">Document ID</p>
                <p className="text-primary font-mono text-xs">{analysis.document_id}</p>
              </div>
              {analysis.router_processing_seconds && (
                <div>
                  <p className="font-medium text-secondary">Routing</p>
                  <p className="text-primary">{analysis.router_processing_seconds}s</p>
                </div>
              )}
              {analysis.analysis_processing_seconds && (
                <div>
                  <p className="font-medium text-secondary">Analysis</p>
                  <p className="text-primary">{analysis.analysis_processing_seconds}s</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'router' && (
        <div className="space-y-6">
          {!routerClassification ? (
            <div className="card p-6">
              <div className="text-center py-12">
                <div className="mb-4">
                  <svg className="w-16 h-16 mx-auto text-secondary opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-primary mb-2">No Router Classification Data</h3>
                <p className="text-secondary">
                  This contract was analyzed before router classification was implemented.
                </p>
              </div>
            </div>
          ) : (
            /* Classification Overview */
            <div className="card p-6">
            <h2 className="text-xl font-semibold text-primary mb-6">Router Classification</h2>

            <div className="space-y-4">
              {/* Classification Type and Confidence */}
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-sm font-medium text-secondary mb-1">Contract Type</p>
                  <p
                    className={`text-2xl font-bold capitalize ${getClassificationColor(
                      routerClassification.classification
                    )}`}
                  >
                    {routerClassification.classification}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-secondary mb-1">Confidence</p>
                  <span
                    className={`inline-flex items-center gap-1 px-4 py-2 rounded-full text-lg font-bold border ${getConfidenceBadge(
                      routerClassification.confidence_score
                    )}`}
                  >
                    {routerClassification.confidence_score}%
                  </span>
                </div>
              </div>

              {/* Reasoning */}
              <div>
                <h3 className="text-sm font-semibold text-primary mb-2">Reasoning</h3>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="text-secondary leading-relaxed">{routerClassification.reasoning}</p>
                </div>
              </div>

              {/* Key Signals */}
              {routerClassification.key_signals && routerClassification.key_signals.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-primary mb-2">Key Signals</h3>
                  <ul className="space-y-2">
                    {routerClassification.key_signals.map((signal, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-secondary bg-green-50 rounded p-3 border border-green-200"
                      >
                        <span className="text-green-600 mt-0.5 text-lg">•</span>
                        <span>{signal}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Alternative Classification */}
              {routerClassification.alternative_classification && (
                <div>
                  <h3 className="text-sm font-semibold text-primary mb-2">
                    Alternative Classification
                  </h3>
                  <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                    <p className="text-secondary">
                      If confidence was lower, this would be classified as:{' '}
                      <span
                        className={`font-semibold capitalize ${getClassificationColor(
                          routerClassification.alternative_classification
                        )}`}
                      >
                        {routerClassification.alternative_classification}
                      </span>
                    </p>
                  </div>
                </div>
              )}

              {/* Document Metadata */}
              {routerClassification.document_metadata &&
                Object.keys(routerClassification.document_metadata).length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-primary mb-2">Document Metadata</h3>
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-2">
                      {routerClassification.document_metadata.has_title !== undefined && (
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-secondary">Has Title:</span>
                          <span className="text-primary">
                            {routerClassification.document_metadata.has_title ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {routerClassification.document_metadata.apparent_counterparty && (
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-secondary">Counterparty:</span>
                          <span className="text-primary">
                            {routerClassification.document_metadata.apparent_counterparty}
                          </span>
                        </div>
                      )}
                      {routerClassification.document_metadata.document_length && (
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-secondary">Length:</span>
                          <span className="text-primary">
                            {routerClassification.document_metadata.document_length}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
            </div>
          </div>
          )}
        </div>
      )}

      {activeTab === 'feedback' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="text-xl font-semibold text-primary mb-4">Team Feedback</h2>
            <p className="text-secondary mb-6">
              Provide feedback on the AI analysis quality to help improve future contract reviews.
              Share what the analysis did well, what it missed, and why these details are important.
            </p>

            {/* Existing Feedback Display */}
            {analysis.team_feedback && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-semibold text-primary">Previous Feedback</h3>
                  {analysis.feedback_submitted_at && (
                    <span className="text-xs text-secondary">
                      {new Date(analysis.feedback_submitted_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="text-sm text-secondary whitespace-pre-wrap">{analysis.team_feedback}</p>
              </div>
            )}

            {/* Feedback Form */}
            <div>
              <label htmlFor="team-feedback" className="block text-sm font-medium text-secondary mb-2">
                Your Feedback
              </label>
              <textarea
                id="team-feedback"
                value={teamFeedback}
                onChange={(e) => setTeamFeedback(e.target.value)}
                rows={8}
                className="w-full px-4 py-3 border border-border rounded-md bg-background text-primary focus:ring-2 focus:ring-primary focus:outline-none"
                placeholder="Example:&#10;&#10;What the AI did well:&#10;- Correctly identified all key liability terms&#10;- Accurately assessed the overall risk level&#10;&#10;What the AI missed:&#10;- Failed to flag the auto-renewal clause which is a critical issue&#10;- Did not catch the data retention period of 10 years&#10;&#10;Why this matters:&#10;- Auto-renewal clauses often lock clients into unfavorable long-term commitments&#10;- Extended data retention increases compliance and security risks"
              />
              <p className="text-xs text-secondary mt-2">
                Be specific about missed items and explain their business impact. Detailed feedback helps us evaluate model performance and capture best practices to improve future AI analysis.
              </p>
            </div>

            {/* Submit Button */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={async () => {
                  if (!teamFeedback.trim()) {
                    alert('Please enter feedback before submitting')
                    return
                  }

                  try {
                    setSubmittingFeedback(true)
                    const { apiPatch } = await import('@/lib/api')

                    await apiPatch(`/api/contracts/${contractId}/feedback`, {
                      team_feedback: teamFeedback
                    })

                    alert('Feedback submitted successfully!')
                    setTeamFeedback('')
                    fetchContractAnalysis() // Refresh to show updated feedback
                  } catch (error) {
                    alert('Failed to submit feedback. Please try again.')
                  } finally {
                    setSubmittingFeedback(false)
                  }
                }}
                disabled={submittingFeedback || !teamFeedback.trim()}
                className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submittingFeedback ? 'Submitting...' : 'Submit Feedback'}
              </button>
              <button
                onClick={() => setTeamFeedback('')}
                className="px-6 py-2 border border-border rounded-md hover:bg-muted transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
