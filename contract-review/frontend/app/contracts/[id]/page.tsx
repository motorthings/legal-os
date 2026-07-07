'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import LoadingSpinner from '@/components/LoadingSpinner';
import { apiGet, apiPatch } from '@/lib/api';
import { logger } from '@/lib/logger';

interface ContractAnalysis {
  id: string;
  document_id: string;
  contract_type: string;
  parties: string[];
  effective_date: string;
  term_length: string;
  total_value: number;

  overall_risk_level: 'high' | 'medium' | 'low';
  risk_score: number;

  ip_rights: {
    summary: string;
    concerns: string[];
    extracted_text: string;
  };
  liability_terms: {
    liability_cap: string;
    unlimited_carveouts: string[];
    indemnification: string;
    concerns: string[];
    extracted_text: string;
  };
  termination_terms: {
    convenience_termination: boolean;
    notice_period: string;
    auto_renewal: boolean;
    concerns: string[];
    extracted_text: string;
  };
  data_handling: {
    data_types: string[];
    compliance_standards: string[];
    cross_border_transfers: string;
    concerns: string[];
    extracted_text: string;
  };
  payment_terms: {
    summary: string;
    concerns: string[];
    extracted_text: string;
  };

  red_flags: Array<{
    category: string;
    issue: string;
    severity: string;
    recommendation: string;
  }>;
  yellow_flags: Array<{
    category: string;
    issue: string;
    recommendation: string;
  }>;

  human_review_required: boolean;
  human_review_reasons: string[];
  human_review_questions: string[];
  human_review_priority: string;

  review_status: string;
  reviewer_notes: string;
  reviewed_by: string;
  reviewed_at: string;

  executive_summary: string;
  recommendations: string[];
  confidence_score: number;

  created_at: string;

  documents: {
    filename: string;
    counterparty_name: string;
    uploaded_at: string;
    storage_url: string;
  };
}

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const contractId = params.id as string;

  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingReview, setSavingReview] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<string>('');
  const [reviewerNotes, setReviewerNotes] = useState('');

  useEffect(() => {
    fetchContractAnalysis();
  }, [contractId]);

  const fetchContractAnalysis = async () => {
    try {
      setLoading(true);
      const data = await apiGet<{ success: boolean; analysis: ContractAnalysis }>(
        `/api/contracts/${contractId}`
      );
      setAnalysis(data.analysis);
      setReviewDecision(data.analysis.review_status);
      setReviewerNotes(data.analysis.reviewer_notes || '');
    } catch (error) {
      logger.error('Error fetching contract analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveReview = async () => {
    if (!reviewDecision || reviewDecision === 'pending') {
      alert('Please select a review decision');
      return;
    }

    try {
      setSavingReview(true);
      await apiPatch(
        `/api/contracts/${contractId}/review?review_status=${reviewDecision}`,
        { reviewer_notes: reviewerNotes }
      );
      alert('Review decision saved successfully');
      fetchContractAnalysis(); // Refresh
    } catch (error) {
      logger.error('Error saving review:', error);
      alert('Failed to save review decision');
    } finally {
      setSavingReview(false);
    }
  };

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-500';
      case 'high': return 'text-orange-500';
      case 'medium': return 'text-yellow-500';
      default: return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-secondary">Contract analysis not found</p>
        <Link href="/contracts" className="text-primary hover:underline mt-4 inline-block">
          ← Back to Contracts
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/contracts" className="text-sm text-primary hover:underline mb-2 inline-block">
          ← Back to Contracts
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-primary mb-2">
              {analysis.documents.filename}
            </h1>
            <div className="flex gap-4 text-sm text-secondary">
              <span>Counterparty: {analysis.documents.counterparty_name || 'Not specified'}</span>
              <span>•</span>
              <span>Type: {analysis.contract_type || 'Not specified'}</span>
              <span>•</span>
              <span>Uploaded: {new Date(analysis.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <span className={`px-4 py-2 rounded-lg text-lg font-bold border-2 ${getRiskBadgeColor(analysis.overall_risk_level)}`}>
              {analysis.overall_risk_level.toUpperCase()} RISK
            </span>
            <span className="text-sm text-secondary">Risk Score: {analysis.risk_score}/100</span>
            <span className="text-sm text-secondary">Confidence: {analysis.confidence_score}%</span>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="card p-6 mb-6 bg-muted/30">
        <h2 className="text-lg font-semibold text-primary mb-3">Executive Summary</h2>
        {typeof analysis.executive_summary === 'string' && !analysis.executive_summary.trim().startsWith('{') ? (
          <p className="text-primary leading-relaxed whitespace-pre-wrap">{analysis.executive_summary}</p>
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
                return <p className="text-primary leading-relaxed whitespace-pre-wrap">{String(analysis.executive_summary)}</p>;
              }
            })()}
          </div>
        )}
      </div>

      {/* Human Review Alert */}
      {analysis.human_review_required && (
        <div className="card p-6 mb-6 bg-orange-500/10 border-orange-500/30">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-orange-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-orange-400 mb-2">Human Review Required</h3>
              <p className="text-sm text-secondary mb-3">Priority: {analysis.human_review_priority}</p>

              <div className="mb-3">
                <p className="text-sm font-medium text-primary mb-2">Reasons:</p>
                <ul className="list-disc list-inside space-y-1">
                  {analysis.human_review_reasons.map((reason, idx) => (
                    <li key={idx} className="text-sm text-secondary">{reason}</li>
                  ))}
                </ul>
              </div>

              {analysis.human_review_questions && analysis.human_review_questions.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-primary mb-2">Questions for Review:</p>
                  <ul className="list-disc list-inside space-y-1">
                    {analysis.human_review_questions.map((question, idx) => (
                      <li key={idx} className="text-sm text-secondary">{question}</li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                onClick={() => alert('Chat functionality coming soon')}
                className="mt-4 px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 transition-colors text-sm"
              >
                Open Chat Assistant
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Risk Flags */}
      {(analysis.red_flags.length > 0 || analysis.yellow_flags.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Red Flags */}
          {analysis.red_flags.length > 0 && (
            <div className="card p-6 border-red-500/30">
              <h2 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                Critical Issues ({analysis.red_flags.length})
              </h2>
              <div className="space-y-4">
                {analysis.red_flags.map((flag, idx) => (
                  <div key={idx} className="p-4 bg-red-500/5 rounded-lg border border-red-500/20">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-semibold text-sm text-red-400">{flag.category}</span>
                      <span className={`text-xs font-medium ${getSeverityColor(flag.severity)}`}>
                        {flag.severity}
                      </span>
                    </div>
                    <p className="text-sm text-primary mb-2">{flag.issue}</p>
                    <p className="text-xs text-secondary italic">→ {flag.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Yellow Flags */}
          {analysis.yellow_flags.length > 0 && (
            <div className="card p-6 border-yellow-500/30">
              <h2 className="text-lg font-semibold text-yellow-400 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Moderate Concerns ({analysis.yellow_flags.length})
              </h2>
              <div className="space-y-4">
                {analysis.yellow_flags.map((flag, idx) => (
                  <div key={idx} className="p-4 bg-yellow-500/5 rounded-lg border border-yellow-500/20">
                    <span className="font-semibold text-sm text-yellow-400 block mb-2">{flag.category}</span>
                    <p className="text-sm text-primary mb-2">{flag.issue}</p>
                    <p className="text-xs text-secondary italic">→ {flag.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Key Terms Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* IP Rights */}
        <div className="card p-6">
          <h3 className="text-md font-semibold text-primary mb-3">Intellectual Property Rights</h3>
          <p className="text-sm text-primary mb-3">{analysis.ip_rights.summary}</p>
          {analysis.ip_rights.concerns && analysis.ip_rights.concerns.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-secondary mb-1">Concerns:</p>
              <ul className="list-disc list-inside space-y-1">
                {analysis.ip_rights.concerns.map((concern, idx) => (
                  <li key={idx} className="text-xs text-red-400">{concern}</li>
                ))}
              </ul>
            </div>
          )}
          {analysis.ip_rights.extracted_text && (
            <details className="mt-3">
              <summary className="text-xs text-secondary cursor-pointer hover:text-primary">
                View extracted text
              </summary>
              <p className="text-xs text-secondary mt-2 p-2 bg-muted rounded italic">
                {analysis.ip_rights.extracted_text}
              </p>
            </details>
          )}
        </div>

        {/* Liability */}
        <div className="card p-6">
          <h3 className="text-md font-semibold text-primary mb-3">Liability & Indemnification</h3>
          <div className="space-y-2 mb-3">
            <p className="text-sm"><span className="font-medium">Cap:</span> {analysis.liability_terms.liability_cap}</p>
            {analysis.liability_terms.unlimited_carveouts && analysis.liability_terms.unlimited_carveouts.length > 0 && (
              <div>
                <p className="text-sm font-medium">Unlimited liability for:</p>
                <ul className="list-disc list-inside ml-2">
                  {analysis.liability_terms.unlimited_carveouts.map((item, idx) => (
                    <li key={idx} className="text-xs text-secondary">{item}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-sm">{analysis.liability_terms.indemnification}</p>
          </div>
          {analysis.liability_terms.concerns && analysis.liability_terms.concerns.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-secondary mb-1">Concerns:</p>
              <ul className="list-disc list-inside space-y-1">
                {analysis.liability_terms.concerns.map((concern, idx) => (
                  <li key={idx} className="text-xs text-red-400">{concern}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Termination */}
        <div className="card p-6">
          <h3 className="text-md font-semibold text-primary mb-3">Termination Rights</h3>
          <div className="space-y-2 mb-3">
            <p className="text-sm">
              <span className="font-medium">For Convenience:</span> {analysis.termination_terms.convenience_termination ? 'Yes' : 'No'}
            </p>
            <p className="text-sm">
              <span className="font-medium">Notice Period:</span> {analysis.termination_terms.notice_period}
            </p>
            <p className="text-sm">
              <span className="font-medium">Auto-Renewal:</span> {analysis.termination_terms.auto_renewal ? 'Yes' : 'No'}
            </p>
          </div>
          {analysis.termination_terms.concerns && analysis.termination_terms.concerns.length > 0 && (
            <div>
              <p className="text-xs font-medium text-secondary mb-1">Concerns:</p>
              <ul className="list-disc list-inside space-y-1">
                {analysis.termination_terms.concerns.map((concern, idx) => (
                  <li key={idx} className="text-xs text-red-400">{concern}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Data Handling */}
        <div className="card p-6">
          <h3 className="text-md font-semibold text-primary mb-3">Data Handling & Privacy</h3>
          <div className="space-y-2 mb-3">
            {analysis.data_handling.data_types && analysis.data_handling.data_types.length > 0 && (
              <div>
                <p className="text-sm font-medium">Data Types:</p>
                <ul className="list-disc list-inside ml-2">
                  {analysis.data_handling.data_types.map((type, idx) => (
                    <li key={idx} className="text-xs text-secondary">{type}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.data_handling.compliance_standards && analysis.data_handling.compliance_standards.length > 0 && (
              <div>
                <p className="text-sm font-medium">Compliance:</p>
                <p className="text-xs text-secondary">{analysis.data_handling.compliance_standards.join(', ')}</p>
              </div>
            )}
            <p className="text-sm">
              <span className="font-medium">Cross-Border:</span> {analysis.data_handling.cross_border_transfers}
            </p>
          </div>
          {analysis.data_handling.concerns && analysis.data_handling.concerns.length > 0 && (
            <div>
              <p className="text-xs font-medium text-secondary mb-1">Concerns:</p>
              <ul className="list-disc list-inside space-y-1">
                {analysis.data_handling.concerns.map((concern, idx) => (
                  <li key={idx} className="text-xs text-red-400">{concern}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Review Decision Panel */}
      <div className="card p-6 bg-muted/30">
        <h2 className="text-lg font-semibold text-primary mb-4">Review Decision</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary mb-2">Decision</label>
            <select
              value={reviewDecision}
              onChange={(e) => setReviewDecision(e.target.value)}
              className="w-full px-4 py-2 border border-border rounded-md bg-background text-primary"
            >
              <option value="pending">Pending Review</option>
              <option value="approved">Approve - Standard Risk Acceptable</option>
              <option value="approved_with_conditions">Approve with Conditions - Minor Issues Noted</option>
              <option value="negotiation_required">Request Negotiation - Unacceptable Terms</option>
              <option value="rejected">Reject - Critical Issues, Do Not Proceed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary mb-2">Reviewer Notes</label>
            <textarea
              value={reviewerNotes}
              onChange={(e) => setReviewerNotes(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-border rounded-md bg-background text-primary"
              placeholder="Add notes about your decision..."
            />
          </div>

          <button
            onClick={handleSaveReview}
            disabled={savingReview}
            className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {savingReview ? 'Saving...' : 'Save Review Decision'}
          </button>
        </div>
      </div>
    </div>
  );
}
