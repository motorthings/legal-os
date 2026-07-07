/**
 * Notion Integration API Client
 *
 * Handles communication with backend Notion endpoints
 */

import { apiGet, apiPost, apiDelete } from './api';

export interface NotionStatus {
  connected: boolean;
  workspace_name?: string;
  last_sync: string | null;
  document_count: number;
  error?: string;
}

export interface SyncResult {
  status: string;
  sync_log_id: string;
  documents_added: number;
  documents_updated: number;
  documents_skipped: number;
  errors?: Array<{
    page_title: string;
    error: string;
  }>;
}

export interface SyncLog {
  id: string;
  user_id: string;
  page_id: string | null;
  page_name: string | null;
  sync_type: string;
  documents_added: number;
  documents_updated: number;
  documents_skipped: number;
  status: string;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface SyncHistoryResponse {
  sync_logs: SyncLog[];
  count: number;
}

export interface NotionPage {
  id: string;
  title: string;
  url: string;
  icon: string | null;
  last_edited_time: string;
  created_time: string;
}

export interface NotionPagesResponse {
  pages: NotionPage[];
  count: number;
}

/**
 * Get Notion connection status for current user
 */
export async function getNotionStatus(): Promise<NotionStatus> {
  return await apiGet<NotionStatus>('/api/notion/status');
}

/**
 * Start Notion OAuth flow
 * Opens a popup window for user to authorize
 */
export async function connectNotion(): Promise<void> {
  const data = await apiGet<{ authorization_url: string }>('/api/notion/auth');
  const authUrl = data.authorization_url;

  // Open OAuth URL in popup window
  const width = 600;
  const height = 700;
  const left = window.screen.width / 2 - width / 2;
  const top = window.screen.height / 2 - height / 2;

  const popup = window.open(
    authUrl,
    'notion-oauth',
    `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
  );

  if (!popup) {
    throw new Error('Failed to open OAuth popup. Please allow popups for this site.');
  }

  // Poll for popup closure and check status
  // This handles cases where window.opener is lost during redirect
  const pollInterval = setInterval(() => {
    if (popup.closed) {
      clearInterval(pollInterval);
      // Trigger a status check in the parent window
      window.dispatchEvent(new CustomEvent('notion-oauth-complete'));
    }
  }, 500);

  // Timeout after 5 minutes
  setTimeout(() => {
    clearInterval(pollInterval);
    if (!popup.closed) {
      popup.close();
    }
  }, 5 * 60 * 1000);
}

/**
 * Trigger manual sync from Notion
 *
 * @param pageIds - List of Notion page IDs to sync
 */
export async function syncNotion(pageIds: string[]): Promise<SyncResult> {
  return await apiPost<SyncResult>('/api/notion/sync', {
    page_ids: pageIds
  });
}

/**
 * Disconnect Notion integration
 * Revokes tokens but doesn't delete synced documents
 */
export async function disconnectNotion(): Promise<void> {
  await apiDelete('/api/notion/disconnect');
}

/**
 * Get sync history for current user
 *
 * @param limit - Number of sync logs to return (max: 50)
 */
export async function getNotionSyncHistory(limit: number = 10): Promise<SyncHistoryResponse> {
  return await apiGet<SyncHistoryResponse>(`/api/notion/sync-history?limit=${limit}`);
}

/**
 * Get all accessible Notion pages for the current user
 *
 * Fetches pages from the user's Notion workspace that the integration has access to.
 */
export async function getNotionPages(): Promise<NotionPagesResponse> {
  return await apiGet<NotionPagesResponse>('/api/notion/pages');
}
