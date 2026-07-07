'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiGet, apiPost, apiPut, apiDelete } from '@/lib/api';
import ConfirmModal from '@/components/ConfirmModal';
import { logger } from '@/lib/logger';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  client_id: string;
  created_at: string;
}

interface Prompt {
  id: string;
  user_id: string;
  title: string;
  prompt_text: string;
  display_order: number;
  created_at: string;
  updated_at: string;
  is_auto_generated?: boolean;
  metadata?: {
    function?: string;
    category?: string;
    generated_at?: string;
  };
}

interface InterviewSession {
  id: string;
  session_id: string;
  session_url: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  agent_id: string;
}

interface InterviewExtraction {
  id: string;
  status: string;
  completeness_score: number | null;
  processed_at: string | null;
  error_message: string | null;
}

type TabType = 'overview' | 'prompts' | 'history' | 'interview';

export default function UserDetailPage() {
  const params = useParams();
  const userId = params.userId as string;

  const [user, setUser] = useState<User | null>(null);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  // Export state
  const [exportingHistory, setExportingHistory] = useState(false);

  // Interview state
  const [interviewSession, setInterviewSession] = useState<InterviewSession | null>(null);
  const [interviewExtraction, setInterviewExtraction] = useState<InterviewExtraction | null>(null);
  const [interviewHistory, setInterviewHistory] = useState<Array<{session: InterviewSession, extraction: InterviewExtraction | null}>>([]);
  const [schedulingInterview, setSchedulingInterview] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

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

  useEffect(() => {
    if (userId) {
      fetchUserData();
    }
  }, [userId]);

  useEffect(() => {
    if (userId && activeTab === 'interview') {
      fetchInterviewData();
    }
  }, [userId, activeTab]);

  const fetchUserData = async () => {
    try {
      setLoading(true);

      // Fetch all users and find the one we need
      const usersData = await apiGet<{ users: User[] }>('/api/users');
      const foundUser = usersData.users?.find((u: User) => u.id === userId);

      if (!foundUser) throw new Error('User not found');
      setUser(foundUser);

      // Fetch user prompts
      try {
        const promptsData = await apiGet<{ prompts: Prompt[] }>(`/api/users/${userId}/prompts`);
        setPrompts(promptsData.prompts || []);
      } catch (err) {
        // Prompts fetch is optional, don't fail the whole page
        logger.error('Failed to fetch prompts:', err);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchInterviewData = async () => {
    try {
      // Fetch current interview status
      const data = await apiGet<{ interview_session: InterviewSession | null; extraction: InterviewExtraction | null }>(`/api/interview-status/${userId}`);
      setInterviewSession(data.interview_session || null);
      setInterviewExtraction(data.extraction || null);

      // Fetch all interview history
      const historyData = await apiGet<{ interviews: Array<{session: InterviewSession, extraction: InterviewExtraction | null}> }>(`/api/interview-history/${userId}`);
      setInterviewHistory(historyData.interviews || []);
    } catch (error) {
      logger.error('Failed to fetch interview data:', error);
    }
  };

  const handleScheduleInterview = async () => {
    if (!user) return;

    try {
      setSchedulingInterview(true);

      const data = await apiPost<{ session_id: string; session_url: string; status: string; agent_id: string }>('/api/onboarding/start-interview', {
        user_id: userId,
        client_id: user.client_id,
        user_email: user.email,
        user_name: user.name
      });

      // Backend returns session data directly (not nested under interview_session)
      const sessionData = {
        id: data.session_id,
        session_id: data.session_id,
        session_url: data.session_url,
        status: data.status,
        agent_id: data.agent_id,
        created_at: new Date().toISOString(),
        completed_at: null
      };

      setInterviewSession(sessionData);

      alert(`Interview scheduled! Session URL: ${data.session_url}`);
    } catch (error) {
      logger.error('Schedule interview error:', error);
      alert('Failed to schedule interview');
    } finally {
      setSchedulingInterview(false);
    }
  };

  const handleCopyUrl = () => {
    if (interviewSession?.session_url) {
      navigator.clipboard.writeText(interviewSession.session_url);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handleExportChatHistory = async () => {
    if (!user) return;

    try {
      setExportingHistory(true);

      const data = await apiGet<{ export_metadata: { total_conversations: number; total_messages: number }; [key: string]: any }>(`/api/users/${userId}/chat-history/export`);

      // Create filename with user name and date
      const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      const filename = `chat-history-${user.name.replace(/\s+/g, '-')}-${date}.json`;

      // Create blob and download
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert(`Exported ${data.export_metadata.total_conversations} conversations with ${data.export_metadata.total_messages} messages`);
    } catch (error) {
      logger.error('Export error:', error);
      alert('Failed to export chat history');
    } finally {
      setExportingHistory(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-muted">Loading user details...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="bg-red-50/20 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error || 'User not found'}</p>
        <Link href="/admin/users" className="mt-2 text-sm text-red-600 hover:text-red-800 underline">
          Back to Users
        </Link>
      </div>
    );
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getExtractionStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'badge-primary';
      case 'pending_review':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="heading-1">{user.name}</h1>
            <span className={user.role === 'admin' ? 'badge-primary' : 'badge-secondary'}>
              {user.role}
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-default mb-6">
        <nav className="flex gap-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 px-1 border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('prompts')}
            className={`pb-3 px-1 border-b-2 transition-colors ${
              activeTab === 'prompts'
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            Prompts
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`pb-3 px-1 border-b-2 transition-colors ${
              activeTab === 'history'
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            Chat History
          </button>
          <button
            onClick={() => setActiveTab('interview')}
            className={`pb-3 px-1 border-b-2 transition-colors ${
              activeTab === 'interview'
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            Interview
          </button>
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="heading-3 mb-4">User Information</h2>
            <div className="space-y-3">
              <div>
                <span className="text-sm text-muted">Email:</span>
                <p className="text-primary">{user.email}</p>
              </div>
              <div>
                <span className="text-sm text-muted">Role:</span>
                <p className="text-primary capitalize">{user.role}</p>
              </div>
              <div>
                <span className="text-sm text-muted">User ID:</span>
                <p className="text-primary font-mono text-sm">{user.id}</p>
              </div>
              <div>
                <span className="text-sm text-muted">Client ID:</span>
                <p className="text-primary font-mono text-sm">{user.client_id}</p>
              </div>
              {user.created_at && (
                <div>
                  <span className="text-sm text-muted">Created:</span>
                  <p className="text-primary">{new Date(user.created_at).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>

          {/* Core Documents Configuration */}
          <div className="card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="heading-3 mb-2">Core Document Mappings</h2>
                <p className="text-sm text-muted">
                  Configure which documents are referenced in system instructions template placeholders
                </p>
              </div>
            </div>
            <Link
              href={`/admin/core-documents/${user.client_id}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Manage Core Documents
            </Link>
            <p className="text-xs text-muted mt-3">
              Map documents to template slots like {'{pm_models_ref}'}, {'{domain_specific_models_ref}'}, and others
            </p>
          </div>
        </div>
      )}

      {/* Prompts Tab */}
      {activeTab === 'prompts' && (
        <div>
          {/* Quick Prompt Templates Section */}
          <div className="card p-6 mb-6">
            <div className="mb-4">
              <h2 className="heading-3 mb-2">Quick Prompt Templates</h2>
              <p className="text-sm text-muted">
                These prompts are automatically selected during the initial setup process based on the user's interview responses.
                They appear in the user's chat sidebar for quick access to common tasks.
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="text-sm font-semibold text-blue-900 mb-1">Automated Selection</h4>
                  <p className="text-sm text-blue-800">
                    Five prompts are automatically chosen from a curated library of 10-15 options during the onboarding interview process.
                    This ensures prompts are tailored to each user's role, strategic focus, and needs.
                  </p>
                </div>
              </div>
            </div>

            {/* Prompts List (Read-Only) */}
            {prompts.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed border-default rounded-lg">
                <svg className="w-12 h-12 text-muted mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-muted mb-2">No prompts configured yet</p>
                <p className="text-sm text-muted">Prompts will be automatically assigned when the user completes their voice interview.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {prompts.map((prompt, index) => (
                  <div
                    key={prompt.id}
                    className="border border-default rounded-lg p-4 bg-gray-50"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-semibold text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-primary">{prompt.title}</h3>
                          {prompt.is_auto_generated && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-teal-100 text-teal-800 text-xs font-medium rounded-full">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M13 7H7v6h6V7z" />
                                <path fillRule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clipRule="evenodd" />
                              </svg>
                              Auto-generated
                            </span>
                          )}
                          {prompt.metadata?.category && (
                            <span className="text-xs text-muted">
                              [{prompt.metadata.category}]
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted whitespace-pre-wrap">{prompt.prompt_text}</p>
                        {prompt.metadata?.function && (
                          <p className="text-xs text-muted mt-2 italic">
                            Function: {prompt.metadata.function.replace(/_/g, ' ')}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat History Tab */}
      {activeTab === 'history' && (
        <div className="card p-6">
          <h2 className="heading-3 mb-2">Chat History Export</h2>
          <p className="text-sm text-muted mb-4">
            Download all chat messages for this user in JSON format
          </p>
          <button
            onClick={handleExportChatHistory}
            disabled={exportingHistory}
            className="btn-primary "
          >
            {exportingHistory ? 'Exporting...' : 'Export Chat History (JSON)'}
          </button>
        </div>
      )}

      {/* Interview Tab */}
      {activeTab === 'interview' && (
        <div className="space-y-6">
          {/* Interview Status Card */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="heading-3">Voice Interview</h2>
              {!interviewSession && (
                <button
                  onClick={handleScheduleInterview}
                  disabled={schedulingInterview}
                  className="btn-primary "
                >
                  {schedulingInterview ? 'Scheduling...' : 'Schedule Interview'}
                </button>
              )}
            </div>

            {!interviewSession ? (
              <div className="text-center py-8 border-2 border-dashed border-default rounded-lg">
                <p className="text-muted mb-2">No interview scheduled yet</p>
                <p className="text-sm text-muted">
                  Click "Schedule Interview" to create a voice interview session for this user
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Session URL */}
                <div>
                  <span className="text-sm text-muted">Interview URL:</span>
                  <div className="mt-1 flex items-center gap-2">
                    <input
                      type="text"
                      value={interviewSession.session_url}
                      readOnly
                      className="flex-1 input-field text-sm font-mono"
                    />
                    <button
                      onClick={handleCopyUrl}
                      className="btn-primary whitespace-nowrap"
                    >
                      {copiedUrl ? 'Copied!' : 'Copy URL'}
                    </button>
                  </div>
                  <p className="form-helper">
                    Share this URL with the user to start their voice interview
                  </p>
                </div>

                {/* Timestamps */}
                {interviewSession.completed_at && (
                  <div>
                    <span className="text-sm text-muted">Completed:</span>
                    <p className="text-primary">{new Date(interviewSession.completed_at).toLocaleString()}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Extraction Results Card */}
          {interviewExtraction && (
            <div className="card p-6">
              <h2 className="heading-3 mb-4">Extraction Results</h2>
              <div className="space-y-4">
                {/* Extraction Status */}
                <div>
                  <span className="text-sm text-muted">Extraction Status:</span>
                  <div className="mt-1">
                    <span className={`inline-block px-3 py-1 text-sm font-semibold rounded-full ${getExtractionStatusBadge(interviewExtraction.status)}`}>
                      {interviewExtraction.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Completeness Score */}
                {interviewExtraction.completeness_score !== null && (
                  <div>
                    <span className="text-sm text-muted">Completeness Score:</span>
                    <div className="mt-2">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 progress-bar-container h-3">
                          <div
                            className="progress-bar-fill"
                            style={{ width: `${interviewExtraction.completeness_score}%` }}
                          ></div>
                        </div>
                        <span className="text-primary font-semibold">{interviewExtraction.completeness_score}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Processed At */}
                {interviewExtraction.processed_at && (
                  <div>
                    <span className="text-sm text-muted">Processed:</span>
                    <p className="text-primary">{new Date(interviewExtraction.processed_at).toLocaleString()}</p>
                  </div>
                )}

                {/* Error Message */}
                {interviewExtraction.error_message && (
                  <div className="bg-red-50/20 border border-red-200 rounded-lg p-4">
                    <span className="text-sm text-red-800 font-medium">Error:</span>
                    <p className="text-sm text-red-700 mt-1">{interviewExtraction.error_message}</p>
                  </div>
                )}

                {/* View Details Link */}
                {interviewExtraction.status === 'completed' && (
                  <div className="pt-4 border-t border-default">
                    <Link
                      href={`/admin/users/${userId}`}
                      className="text-primary hover:text-primary-600 font-medium underline"
                    >
                      View Full Details →
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Previous Interviews */}
          {interviewHistory.length > 0 && (
            <div className="card p-6">
              <h2 className="heading-3 mb-4">Interview History</h2>
              <p className="text-sm text-muted mb-4">
                All previous interview sessions and extractions for this user ({interviewHistory.length} total)
              </p>
              <div className="space-y-3">
                {interviewHistory.map((interview, index) => (
                  <div key={interview.session.session_id} className="border border-default rounded-lg p-4 hover:bg-hover transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="badge-secondary font-mono text-xs">
                            {index === 0 ? 'Most Recent' : `Interview ${interviewHistory.length - index}`}
                          </span>
                          <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadgeColor(interview.session.status)}`}>
                            {interview.session.status.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm text-muted">
                          Created: {new Date(interview.session.created_at).toLocaleString()}
                        </p>
                        {interview.session.completed_at && (
                          <p className="text-sm text-muted">
                            Completed: {new Date(interview.session.completed_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Extraction Info */}
                    {interview.extraction && (
                      <div className="mt-3 pt-3 border-t border-default">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${getExtractionStatusBadge(interview.extraction.status)}`}>
                              {interview.extraction.status.replace('_', ' ').toUpperCase()}
                            </span>
                            {interview.extraction.completeness_score !== null && (
                              <span className="text-sm text-muted">
                                Completeness: {interview.extraction.completeness_score}%
                              </span>
                            )}
                          </div>
                          {interview.extraction.status === 'completed' && (
                            <Link
                              href={`/admin/users/${userId}`}
                              className="text-xs text-primary hover:text-primary-600 font-medium underline"
                            >
                              View Details →
                            </Link>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Session URL */}
                    <div className="mt-3 pt-3 border-t border-default">
                      <p className="text-xs text-muted mb-1">Interview URL:</p>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={interview.session.session_url}
                          readOnly
                          className="flex-1 text-xs font-mono px-2 py-1 border border-default rounded bg-background"
                        />
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(interview.session.session_url);
                          }}
                          className="text-xs px-2 py-1 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
                        >
                          Copy
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Info Card */}
          <div className="bg-hover border border-default rounded-lg p-4">
            <h3 className="text-sm font-semibold text-primary mb-2">About Voice Interviews</h3>
            <ul className="text-sm text-muted space-y-1">
              <li>• Voice interviews are conducted through ElevenLabs Conversational AI</li>
              <li>• After completion, AI automatically extracts structured data</li>
              <li>• Extraction results are reviewed before deployment to production</li>
              <li>• Interview transcripts and configurations are securely stored</li>
            </ul>
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
