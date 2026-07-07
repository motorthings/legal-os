'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import VoiceInterview from '@/components/VoiceInterview';

interface InterviewSession {
  id: string;
  client_id: string;
  agent_id: string;
  session_id: string;
  status: string;
  metadata: {
    user_name?: string;
    client_name?: string;
    user_email?: string;
  };
}

export default function InterviewPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  const fetchSession = async () => {
    try {
      setLoading(true);

      // Fetch session details - use direct fetch for public endpoint
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://superassistant-mvp-production.up.railway.app';
      const response = await fetch(`${backendUrl}/api/interview-session/${sessionId}`);

      if (!response.ok) {
        throw new Error('Interview session not found');
      }

      const data = await response.json();
      setSession(data.session);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load interview');
    } finally {
      setLoading(false);
    }
  };

  const handleInterviewComplete = () => {
    // Refresh the session to get updated status
    fetchSession();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-teal-200 border-t-teal-500 mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg">Loading your interview...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mb-2">Interview Not Found</h1>
          <p className="text-slate-600 mb-6">{error || 'This interview session is not available.'}</p>
          <p className="text-sm text-slate-500">
            Please contact your Contract Review administrator if you believe this is an error.
          </p>
        </div>
      </div>
    );
  }

  if (session.status === 'completed') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mb-2">Interview Complete!</h1>
          <p className="text-slate-600 mb-6">
            Thank you for completing your discovery interview. We're processing your responses and will be in touch soon.
          </p>
          <p className="text-sm text-slate-500">
            You can now close this page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl flex items-center justify-center shadow-lg shadow-teal-500/20">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">Contract Review Discovery</h1>
              <p className="text-sm text-slate-500">Voice Interview Experience</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {session.agent_id ? (
          <VoiceInterview
            agentId={session.agent_id}
            userName={session.metadata?.user_name || session.metadata?.client_name}
            onComplete={handleInterviewComplete}
          />
        ) : (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-200 border-t-teal-500 mx-auto mb-4"></div>
            <p className="text-slate-600">Preparing your interview experience...</p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-sm border-t border-slate-200 py-3">
        <div className="text-center">
          <p className="text-xs text-slate-400">
            Powered by Contract Review &amp; ElevenLabs Conversational AI
          </p>
        </div>
      </footer>
    </div>
  );
}
