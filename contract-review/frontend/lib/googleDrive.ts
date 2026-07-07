/**
 * Google Drive Integration API Client
 *
 * Handles communication with backend Google Drive endpoints
 */

import { apiGet, apiPost, apiDelete } from './api';

export interface GoogleDriveStatus {
  connected: boolean;
  last_sync: string | null;
  document_count: number;
  folder_id?: string;
  folder_name?: string;
  error?: string;
}

export interface SyncResult {
  status: string;
  sync_log_id: string;
  documents_added: number;
  documents_updated: number;
  documents_skipped: number;
  errors?: Array<{
    file_name: string;
    error: string;
  }>;
}

export interface SyncLog {
  id: string;
  user_id: string;
  folder_id: string | null;
  folder_name: string | null;
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

export interface GoogleDriveFile {
  id: string;
  name: string;
  mimeType: string;
  webViewLink?: string;
  size?: string;
  iconLink?: string;
  thumbnailLink?: string;
}

/**
 * Get Google Drive connection status for current user
 */
export async function getGoogleDriveStatus(): Promise<GoogleDriveStatus> {
  return await apiGet<GoogleDriveStatus>('/api/google-drive/status');
}

/**
 * Start Google OAuth flow
 * Opens a popup window for user to authorize
 */
export async function connectGoogleDrive(): Promise<void> {
  const data = await apiGet<{ authorization_url: string }>('/api/google-drive/auth');
  const authUrl = data.authorization_url;

  // Open OAuth URL in popup window
  const width = 600;
  const height = 700;
  const left = window.screen.width / 2 - width / 2;
  const top = window.screen.height / 2 - height / 2;

  const popup = window.open(
    authUrl,
    'google-oauth',
    `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
  );

  if (!popup) {
    throw new Error('Failed to open OAuth popup. Please allow popups for this site.');
  }

  // Note: The OAuth callback will redirect to /documents?google_drive=connected
  // The parent window should listen for this and refresh the status
}

/**
 * List files in a Google Drive folder
 *
 * @param folderId - Google Drive folder ID
 */
export async function listFolderFiles(folderId: string): Promise<GoogleDriveFile[]> {
  const response = await apiGet<{ files?: GoogleDriveFile[] }>(`/api/google-drive/files/${folderId}`);
  return response.files || [];
}

/**
 * Sync selected files from Google Drive
 *
 * @param fileIds - Array of Google Drive file IDs to sync
 */
export async function syncGoogleDriveFiles(fileIds: string[]): Promise<SyncResult> {
  return await apiPost<SyncResult>('/api/google-drive/sync', {
    file_ids: fileIds
  });
}

/**
 * Trigger manual sync from Google Drive (legacy folder-based sync)
 *
 * @param folderId - Optional folder ID to sync (null = root folder)
 * @param folderName - Optional folder name for logging
 * @deprecated Use syncGoogleDriveFiles instead for better control
 */
export async function syncGoogleDrive(
  folderId?: string | null,
  folderName?: string | null
): Promise<SyncResult> {
  return await apiPost<SyncResult>('/api/google-drive/sync', {
    folder_id: folderId,
    folder_name: folderName
  });
}

/**
 * Disconnect Google Drive
 * Revokes OAuth tokens (doesn't delete synced documents)
 */
export async function disconnectGoogleDrive(): Promise<void> {
  await apiDelete('/api/google-drive/disconnect');
}

/**
 * Get sync history for current user
 *
 * @param limit - Number of sync logs to fetch (default: 10, max: 50)
 */
export async function getSyncHistory(limit: number = 10): Promise<SyncHistoryResponse> {
  return await apiGet<SyncHistoryResponse>(`/api/google-drive/sync-history?limit=${limit}`);
}

/**
 * Format sync status for display
 */
export function formatSyncStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'pending': 'Pending',
    'running': 'In Progress',
    'completed': 'Completed',
    'failed': 'Failed'
  };

  return statusMap[status] || status;
}

/**
 * Format last sync time for display
 */
export function formatLastSync(lastSync: string | null): string {
  if (!lastSync) return 'Never';

  const date = new Date(lastSync);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
}
