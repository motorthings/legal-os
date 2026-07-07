'use client';

import { useState, useCallback, useEffect } from 'react';
import { useConversation } from '@elevenlabs/react';

interface VoiceInterviewProps {
  agentId: string;
  userName?: string;
  onComplete?: () => void;
}

type ConversationStatus = 'idle' | 'connecting' | 'connected' | 'disconnecting' | 'error';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
  isFinal: boolean;
}

// Maximum pause duration before warning (3 minutes)
const PAUSE_WARNING_THRESHOLD = 3 * 60 * 1000;
// Maximum pause duration before auto-resume warning (5 minutes)
const PAUSE_TIMEOUT_THRESHOLD = 5 * 60 * 1000;

export default function VoiceInterview({ agentId, userName, onComplete }: VoiceInterviewProps) {
  const [status, setStatus] = useState<ConversationStatus>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [micPermission, setMicPermission] = useState<'granted' | 'denied' | 'prompt'>('prompt');
  const [isPaused, setIsPaused] = useState(false);
  const [pauseStartTime, setPauseStartTime] = useState<number | null>(null);
  const [pauseDuration, setPauseDuration] = useState(0);
  const [pauseWarning, setPauseWarning] = useState<string | null>(null);

  const conversation = useConversation({
    onConnect: () => {
      setStatus('connected');
      setError(null);
    },
    onDisconnect: () => {
      setStatus('idle');
      if (hasStarted) {
        onComplete?.();
      }
    },
    onMessage: (message) => {
      // Handle different message types from ElevenLabs
      if (message.source === 'user' || message.source === 'ai') {
        const newMessage: Message = {
          id: `${Date.now()}-${Math.random()}`,
          role: message.source === 'user' ? 'user' : 'agent',
          content: message.message || '',
          timestamp: new Date(),
          isFinal: message.source === 'ai' || !('isFinal' in message) || message.isFinal === true,
        };

        setMessages(prev => {
          // For user messages that are transcriptions, update the last user message if not final
          if (message.source === 'user' && !newMessage.isFinal) {
            const lastUserIdx = prev.findLastIndex(m => m.role === 'user' && !m.isFinal);
            if (lastUserIdx >= 0) {
              const updated = [...prev];
              updated[lastUserIdx] = newMessage;
              return updated;
            }
          }
          return [...prev, newMessage];
        });
      }
    },
    onError: (error) => {
      console.error('Conversation error:', error);
      const errorMessage = typeof error === 'string' ? error : (error as Error)?.message || 'An error occurred during the conversation';
      setError(errorMessage);
      setStatus('error');
    },
  });

  // Check microphone permission on mount
  useEffect(() => {
    const checkMicPermission = async () => {
      try {
        const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
        setMicPermission(result.state as 'granted' | 'denied' | 'prompt');

        result.addEventListener('change', () => {
          setMicPermission(result.state as 'granted' | 'denied' | 'prompt');
        });
      } catch {
        // Permissions API not supported, will check when starting
        setMicPermission('prompt');
      }
    };

    checkMicPermission();
  }, []);

  // Track pause duration and show warnings
  useEffect(() => {
    if (!isPaused) {
      setPauseStartTime(null);
      setPauseDuration(0);
      setPauseWarning(null);
      return;
    }

    // Set pause start time
    if (!pauseStartTime) {
      setPauseStartTime(Date.now());
    }

    // Update pause duration every second
    const interval = setInterval(() => {
      if (pauseStartTime) {
        const duration = Date.now() - pauseStartTime;
        setPauseDuration(duration);

        // Show warnings based on duration
        if (duration >= PAUSE_TIMEOUT_THRESHOLD) {
          setPauseWarning('The session may timeout soon. Please resume to continue your interview.');
        } else if (duration >= PAUSE_WARNING_THRESHOLD) {
          setPauseWarning('You\'ve been paused for a while. Resume soon to avoid session timeout.');
        } else {
          setPauseWarning(null);
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isPaused, pauseStartTime]);

  const requestMicPermission = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop all tracks after getting permission
      stream.getTracks().forEach(track => track.stop());
      setMicPermission('granted');
      return true;
    } catch (err) {
      console.error('Microphone permission denied:', err);
      setMicPermission('denied');
      setError('Microphone access is required for the voice interview. Please allow microphone access and try again.');
      return false;
    }
  };

  const startConversation = useCallback(async () => {
    setError(null);
    setStatus('connecting');

    // Request microphone permission first
    const hasPermission = await requestMicPermission();
    if (!hasPermission) {
      setStatus('idle');
      return;
    }

    try {
      await conversation.startSession({
        agentId,
        connectionType: 'webrtc',
      });
      setHasStarted(true);
    } catch (err) {
      console.error('Failed to start conversation:', err);
      setError(err instanceof Error ? err.message : 'Failed to start the interview');
      setStatus('error');
    }
  }, [agentId, conversation]);

  const endConversation = useCallback(async () => {
    setStatus('disconnecting');
    try {
      await conversation.endSession();
    } catch (err) {
      console.error('Failed to end conversation:', err);
      setStatus('idle');
    }
  }, [conversation]);

  const togglePause = useCallback(async () => {
    if (isPaused) {
      // Resume - set volume back to normal
      try {
        await conversation.setVolume({ volume: 1 });
        setIsPaused(false);
        setPauseStartTime(null);
        setPauseDuration(0);
        setPauseWarning(null);
      } catch (err) {
        console.error('Failed to resume:', err);
      }
    } else {
      // Pause - mute the conversation
      try {
        await conversation.setVolume({ volume: 0 });
        setIsPaused(true);
        setPauseStartTime(Date.now());
      } catch (err) {
        console.error('Failed to pause:', err);
      }
    }
  }, [isPaused, conversation]);

  // Format pause duration as MM:SS
  const formatPauseDuration = (ms: number): string => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getStatusText = () => {
    if (isPaused) {
      return 'Interview paused';
    }
    switch (status) {
      case 'idle':
        return hasStarted ? 'Interview ended' : 'Ready to begin';
      case 'connecting':
        return 'Connecting...';
      case 'connected':
        return conversation.isSpeaking ? 'AI is speaking...' : 'Listening to you...';
      case 'disconnecting':
        return 'Ending interview...';
      case 'error':
        return 'Connection error';
      default:
        return 'Ready';
    }
  };

  const getStatusColor = () => {
    if (isPaused) {
      return 'text-slate-500';
    }
    switch (status) {
      case 'connected':
        return conversation.isSpeaking ? 'text-teal-500' : 'text-teal-600';
      case 'connecting':
      case 'disconnecting':
        return 'text-teal-400';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-slate-600';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Main Interview Card */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-500 to-teal-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-white text-lg font-semibold">Voice Interview</h2>
              {userName && (
                <p className="text-teal-100 text-sm">Welcome, {userName}</p>
              )}
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              status === 'connected'
                ? 'bg-green-400/20 text-green-100'
                : 'bg-white/20 text-white'
            }`}>
              {status === 'connected' ? 'Live' : 'Ready'}
            </div>
          </div>
        </div>

        {/* Visualization Area */}
        <div className="relative px-6 py-8 bg-gradient-to-b from-gray-50 to-white">
          {/* Animated Orb */}
          <div className="flex justify-center mb-6">
            <div className={`relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${
              isPaused
                ? 'bg-slate-400 shadow-lg shadow-slate-400/50'
                : status === 'connected'
                  ? conversation.isSpeaking
                    ? 'bg-teal-400 shadow-lg shadow-teal-400/50'
                    : 'bg-teal-500 shadow-lg shadow-teal-500/50'
                  : status === 'connecting'
                    ? 'bg-teal-300 shadow-lg shadow-teal-300/50'
                    : 'bg-slate-300'
            }`}>
              {/* Pulse animation rings */}
              {status === 'connected' && !isPaused && (
                <>
                  <div className={`absolute inset-0 rounded-full animate-ping opacity-20 ${
                    conversation.isSpeaking ? 'bg-teal-400' : 'bg-teal-500'
                  }`} style={{ animationDuration: '2s' }} />
                  <div className={`absolute inset-2 rounded-full animate-pulse opacity-30 ${
                    conversation.isSpeaking ? 'bg-teal-300' : 'bg-teal-400'
                  }`} />
                </>
              )}
              {status === 'connecting' && (
                <div className="absolute inset-0 rounded-full animate-pulse bg-teal-200 opacity-30" />
              )}
              {isPaused && (
                <div className="absolute inset-0 rounded-full animate-pulse bg-slate-300 opacity-30" style={{ animationDuration: '3s' }} />
              )}

              {/* Inner icon */}
              <div className="relative z-10">
                {isPaused ? (
                  // Paused icon
                  <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                  </svg>
                ) : status === 'connected' ? (
                  conversation.isSpeaking ? (
                    // Speaking icon (sound waves)
                    <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    </svg>
                  ) : (
                    // Listening icon (microphone)
                    <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  )
                ) : status === 'connecting' || status === 'disconnecting' ? (
                  // Loading spinner
                  <svg className="w-12 h-12 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  // Idle microphone icon
                  <svg className="w-12 h-12 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                )}
              </div>
            </div>
          </div>

          {/* Status Text */}
          <div className="text-center mb-6">
            <p className={`text-lg font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </p>
            {status === 'connected' && (
              <>
                <p className="text-sm text-gray-500 mt-1">
                  {isPaused
                    ? 'Take your time. Click Resume when ready to continue.'
                    : conversation.isSpeaking
                      ? 'Please wait while the AI responds'
                      : 'Speak naturally - the AI is listening'}
                </p>
                {/* Pause duration display */}
                {isPaused && pauseDuration > 0 && (
                  <p className="text-sm text-slate-500 mt-2 font-medium">
                    Paused for {formatPauseDuration(pauseDuration)}
                  </p>
                )}
              </>
            )}
          </div>

          {/* Pause Warning */}
          {pauseWarning && (
            <div className="mb-6 p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm text-slate-600">{pauseWarning}</p>
                  <button
                    onClick={togglePause}
                    className="mt-2 text-sm text-teal-600 hover:text-teal-700 underline hover:no-underline font-medium"
                  >
                    Click here to resume
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm text-red-700">{error}</p>
                  {micPermission === 'denied' && (
                    <p className="text-xs text-red-600 mt-1">
                      To enable microphone access, click the camera icon in your browser's address bar.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Control Buttons */}
          <div className="flex justify-center gap-4">
            {status === 'idle' || status === 'error' ? (
              <button
                onClick={startConversation}
                disabled={hasStarted && status === 'idle'}
                className={`px-8 py-4 rounded-xl font-semibold text-lg transition-all transform hover:scale-105 ${
                  hasStarted && status === 'idle'
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-teal-500 hover:bg-teal-600 text-white shadow-lg hover:shadow-xl'
                }`}
              >
                {hasStarted ? 'Interview Complete' : 'Start Interview'}
              </button>
            ) : status === 'connected' ? (
              <>
                {/* Pause/Resume Button */}
                <button
                  onClick={togglePause}
                  className={`px-5 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
                    isPaused
                      ? 'bg-teal-500 hover:bg-teal-600 text-white shadow-md'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300'
                  }`}
                >
                  {isPaused ? (
                    <>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      Resume
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                      </svg>
                      Pause
                    </>
                  )}
                </button>

                {/* End Interview Button */}
                <button
                  onClick={endConversation}
                  className="px-5 py-3 bg-slate-100 hover:bg-red-50 text-slate-600 hover:text-red-600 border border-slate-300 hover:border-red-200 rounded-lg font-medium transition-all flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  End Interview
                </button>
              </>
            ) : (
              <button
                disabled
                className="px-8 py-4 bg-gray-300 text-gray-500 rounded-xl font-semibold text-lg cursor-not-allowed"
              >
                {status === 'connecting' ? 'Connecting...' : 'Ending...'}
              </button>
            )}
          </div>
        </div>

        {/* Live Transcript (when connected) */}
        {messages.length > 0 && (
          <div className="border-t border-gray-200">
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
              <h3 className="text-sm font-medium text-gray-700">Conversation</h3>
            </div>
            <div className="max-h-64 overflow-y-auto p-4 space-y-3">
              {messages.filter(m => m.isFinal && m.content).slice(-6).map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
                      message.role === 'user'
                        ? 'bg-teal-500 text-white rounded-br-md'
                        : 'bg-gray-100 text-gray-800 rounded-bl-md'
                    }`}
                  >
                    {message.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Instructions Card (below main card) */}
      {status === 'idle' && !hasStarted && (
        <div className="mt-6 bg-teal-50 rounded-xl border border-teal-200 p-5">
          <h3 className="text-sm font-semibold text-teal-900 mb-3 flex items-center gap-2">
            <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Before you begin
          </h3>
          <ul className="space-y-2 text-sm text-teal-800">
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              This interview takes about <strong>15-20 minutes</strong>
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Find a <strong>quiet space</strong> with minimal background noise
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              You'll need to <strong>allow microphone access</strong>
            </li>
            <li className="flex items-center gap-2">
              <svg className="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Speak naturally and take your time
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
