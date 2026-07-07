'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import LoadingSpinner from '@/components/LoadingSpinner';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';

interface Conversation {
  id: string;
  title: string;
  client_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  users: {
    name: string;
    email: string;
  };
  clients: {
    name: string;
  };
}

interface Client {
  id: string;
  name: string;
}

export default function ConversationsPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [clientFilter, setClientFilter] = useState('');

  useEffect(() => {
    fetchClients();
    fetchConversations();
  }, [clientFilter]);

  async function fetchClients() {
    try {
      const data = await apiGet<{ clients: any[] }>('/api/admin/clients');
      setClients(data.clients || []);
    } catch (err) {
      // Silently fail - client dropdown is optional enhancement
      logger.error('Failed to load clients:', err);
    }
  }

  async function fetchConversations() {
    try {
      setLoading(true);
      setError(null);

      let endpoint = `/api/admin/conversations?limit=100`;
      if (clientFilter) {
        endpoint += `&client_id=${clientFilter}`;
      }

      const data = await apiGet<{ conversations: any[] }>(endpoint);
      setConversations(data.conversations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(conversationId: string, format: 'json' | 'txt') {
    try {
      // Fetch conversation messages
      const data = await apiGet<{ messages: any[] }>(`/api/conversations/${conversationId}/messages`);
      const conversation = conversations.find(c => c.id === conversationId);

      if (format === 'json') {
        // Export as JSON
        const jsonData = JSON.stringify({
          conversation_id: conversationId,
          title: conversation?.title,
          client: conversation?.clients?.name || 'Unknown',
          user: conversation?.users?.name || 'Unknown',
          messages: data.messages
        }, null, 2);

        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation-${conversationId}.json`;
        a.click();
      } else {
        // Export as TXT
        let txtData = `Conversation: ${conversation?.title}\n`;
        txtData += `Client: ${conversation?.clients?.name || 'Unknown'}\n`;
        txtData += `User: ${conversation?.users?.name || 'Unknown'}\n`;
        txtData += `Date: ${new Date(conversation?.created_at || '').toLocaleDateString()}\n`;
        txtData += `\n${'='.repeat(50)}\n\n`;

        data.messages.forEach((msg: any) => {
          txtData += `[${msg.role.toUpperCase()}] ${new Date(msg.timestamp).toLocaleString()}\n`;
          txtData += `${msg.content}\n\n`;
        });

        const blob = new Blob([txtData], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation-${conversationId}.txt`;
        a.click();
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to export conversation');
    }
  }

  // Filter conversations by search query
  const filteredConversations = conversations.filter(conv => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      conv.title.toLowerCase().includes(query) ||
      conv.users?.name?.toLowerCase().includes(query) ||
      conv.users?.email?.toLowerCase().includes(query)
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="heading-1">All Conversations</h1>
        <p className="text-muted mt-1">
          View and manage all conversations
        </p>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-6">
        {/* Search */}
        <div>
          <label className="label">
            Search
          </label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title or user..."
            className="input-field"
          />
        </div>

        {searchQuery && (
          <div className="mt-3 text-sm text-muted">
            Showing {filteredConversations.length} of {conversations.length} conversations
          </div>
        )}
      </div>

      {/* Conversations List */}
      {error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      ) : filteredConversations.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-muted mb-4">
            {searchQuery ? 'No conversations match your search' : 'No conversations yet'}
          </p>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="link text-sm font-medium"
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        <div className="card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-page border-b border-default">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                    Conversation
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                    Messages
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                    Last Updated
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-muted uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-default">
                {filteredConversations.map((conv) => (
                  <tr key={conv.id} className="hover:bg-hover transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-primary">
                          {conv.title}
                        </div>
                        <div className="text-xs text-muted mt-1">
                          {conv.id.slice(0, 8)}...
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm text-primary">
                          {conv.users?.name || 'Unknown User'}
                        </div>
                        <div className="text-xs text-muted">
                          {conv.users?.email || 'N/A'}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-primary">
                        {conv.message_count || 0}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-muted">
                        {new Date(conv.updated_at).toLocaleDateString()}
                      </div>
                      <div className="text-xs text-muted">
                        {new Date(conv.updated_at).toLocaleTimeString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right text-sm space-x-2">
                      <Link
                        href={`/admin/conversations/${conv.id}`}
                        className="link font-medium"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => handleExport(conv.id, 'json')}
                        className="link font-medium"
                        title="Download conversation as JSON"
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {!error && conversations.length > 0 && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="text-sm text-muted mb-1">Total Conversations</div>
            <div className="text-2xl font-bold text-primary">{conversations.length}</div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-muted mb-1">Total Messages</div>
            <div className="text-2xl font-bold text-primary">
              {conversations.reduce((sum, conv) => sum + (conv.message_count || 0), 0)}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-muted mb-1">Active Users</div>
            <div className="text-2xl font-bold text-primary">
              {new Set(conversations.map(c => c.user_id)).size}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
