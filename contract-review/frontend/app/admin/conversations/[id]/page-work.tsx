'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiGet, apiDelete } from '@/lib/api';
import ConfirmModal from '@/components/ConfirmModal';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  client_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export default function ConversationViewerPage() {
  const params = useParams();
  const router = useRouter();
  const conversationId = params.id as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    if (conversationId) {
      fetchConversation();
    }
  }, [conversationId]);

  const fetchConversation = async () => {
    try {
      setLoading(true);

      // Fetch messages with authentication
      const data = await apiGet<{ messages: Message[] }>(`/api/conversations/${conversationId}/messages`);
      setMessages(data.messages || []);

      // We could fetch conversation details here if we had an endpoint for it
      // For now, we'll use the conversation_id
      setConversation({
        id: conversationId,
        title: 'Conversation',
        client_id: '',
        user_id: '',
        created_at: '',
        updated_at: ''
      });

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleExportJSON = () => {
    const exportData = {
      conversation_id: conversationId,
      exported_at: new Date().toISOString(),
      message_count: messages.length,
      messages: messages.map((m: Message) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${conversationId.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleExportText = () => {
    let text = `Conversation Export\n`;
    text += `ID: ${conversationId}\n`;
    text += `Exported: ${new Date().toLocaleString()}\n`;
    text += `Messages: ${messages.length}\n`;
    text += `\n${'='.repeat(80)}\n\n`;

    messages.forEach((message: Message, index: number) => {
      text += `[${formatTime(message.timestamp)}] ${message.role.toUpperCase()}\n`;
      text += `${message.content}\n`;
      if (index < messages.length - 1) {
        text += `\n${'-'.repeat(80)}\n\n`;
      }
    });

    const blob = new Blob([text], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${conversationId.slice(0, 8)}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleDelete = () => {
    setConfirmModal({
      open: true,
      title: 'Delete Conversation',
      message: 'Are you sure you want to delete this conversation? This action cannot be undone.',
      onConfirm: async () => {
        await deleteConversation();
      }
    });
  };

  const deleteConversation = async () => {
    try{
      const data = await apiDelete<{ message: string }>(`/api/conversations/${conversationId}`);
      alert(data.message || 'Conversation deleted successfully');

      // Redirect back to conversations list
      router.push('/admin/conversations');
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to delete conversation');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-muted">Loading conversation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Link href="/admin/conversations" className="text-sm text-primary-500 hover:text-primary-600 mb-4 inline-block">
          ← Back to Conversations
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/admin/conversations" className="text-sm text-primary-500 hover:text-primary-600 mb-2 inline-block">
          ← Back to Conversations
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-primary">Conversation</h1>
            <p className="text-muted mt-1">
              {messages.length} messages • {conversationId}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative group">
              <button className="text-muted hover:text-primary text-sm flex items-center gap-1">
                Export
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div className="hidden group-hover:block absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-default py-1 z-10">
                <button
                  onClick={handleExportJSON}
                  className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-hover transition-colors"
                >
                  Export as JSON
                </button>
                <button
                  onClick={handleExportText}
                  className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-hover transition-colors"
                >
                  Export as Text
                </button>
              </div>
            </div>
            <button
              onClick={handleDelete}
              className="text-red-600 hover:text-red-800 text-sm font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="bg-white rounded-lg shadow-sm border border-default">
        {messages.length === 0 ? (
          <div className="p-12 text-center text-muted">
            No messages in this conversation
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {messages.map((message: Message) => (
              <div
                key={message.id}
                className={`p-6 ${
                  message.role === 'assistant' ? 'bg-hover' : 'bg-white'
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold ${
                    message.role === 'assistant' ? 'avatar-primary' : 'avatar-secondary'
                  }`}>
                    {message.role === 'assistant' ? 'AI' : 'U'}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-primary capitalize">
                        {message.role}
                      </span>
                      <span className="text-xs text-muted">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>
                    <div className="text-primary whitespace-pre-wrap break-words">
                      {message.content}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata */}
      {messages.length > 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Conversation Metrics</p>
              <ul className="space-y-1 text-blue-700">
                <li>Total messages: {messages.length}</li>
                <li>User messages: {messages.filter(m => m.role === 'user').length}</li>
                <li>Assistant responses: {messages.filter(m => m.role === 'assistant').length}</li>
                <li>First message: {messages[0] ? formatTime(messages[0].timestamp) : 'N/A'}</li>
                <li>Last message: {messages[messages.length - 1] ? formatTime(messages[messages.length - 1].timestamp) : 'N/A'}</li>
              </ul>
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
