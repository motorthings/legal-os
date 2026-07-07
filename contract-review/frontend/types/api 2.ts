/**
 * Common API Response Types
 *
 * These type definitions provide type safety for API responses throughout the application.
 * Use these instead of `any` types when handling API calls.
 */

// ============================================================================
// Generic API Response Wrapper
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  limit: number;
  offset: number;
  hasMore?: boolean;
}

// ============================================================================
// Document Types
// ============================================================================

export interface Document {
  id: string;
  filename: string;
  file_type: string | null;
  file_size: number;
  client_id: string;
  user_id?: string;
  uploaded_at: string;
  uploaded_by?: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  processing_error?: string | null;
  chunk_count: number;
  access_count: number;
  storage_url?: string;
  source_platform?: 'upload' | 'google_drive' | 'notion';
  external_url?: string;
  google_drive_file_id?: string;
  notion_page_id?: string;
  sync_cadence?: 'manual' | 'daily' | 'weekly' | 'monthly';
  is_core_document?: boolean;
}

export interface DocumentWithRelations extends Document {
  clients?: { name: string };
  users?: { email: string };
}

export interface DocumentsResponse {
  success: boolean;
  documents: Document[];
}

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  name?: string | null;
  role: 'admin' | 'user';
  avatar_url?: string | null;
  client_id: string;
  created_at: string;
  storage_quota: number;
  storage_used: number;
}

export interface UserProfile extends User {
  // Add any additional profile-specific fields here
}

// ============================================================================
// Conversation Types
// ============================================================================

export interface Message {
  id?: string;
  conversation_id?: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  created_at?: string;
}

export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  client_id: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  in_knowledge_base?: boolean;
  added_to_kb_at?: string | null;
  archived?: boolean;
  archived_at?: string | null;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ConversationsResponse {
  success: boolean;
  conversations: Conversation[];
}

// ============================================================================
// Interview & Extraction Types
// ============================================================================

export interface InterviewSession {
  id: string;
  user_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  transcript?: string;
  agent_id: string;
  created_at: string;
  completed_at?: string;
  audio_file_url?: string;
}

export interface Extraction {
  id: string;
  client_id: string;
  user_id: string;
  interview_id?: string;
  extraction_data: Record<string, any>;
  status: 'pending' | 'approved' | 'rejected';
  approved_at?: string;
  approved_by?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Quick Prompts Types
// ============================================================================

export interface QuickPrompt {
  id: string;
  prompt_text: string;
  function_name?: string;
  usage_count: number;
  active: boolean;
  display_order?: number;
  created_at?: string;
}

export interface QuickPromptsResponse {
  success: boolean;
  prompts: QuickPrompt[];
}

// ============================================================================
// Integration Types (Google Drive, Notion)
// ============================================================================

export interface GoogleDriveStatus {
  connected: boolean;
  email?: string;
  folder_id?: string;
  folder_name?: string;
  document_count: number;
  last_sync?: string;
}

export interface GoogleDriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  modifiedTime?: string;
}

export interface NotionStatus {
  connected: boolean;
  workspace_name?: string;
  workspace_id?: string;
  document_count: number;
  last_sync?: string;
}

export interface NotionPage {
  id: string;
  title: string;
  url?: string;
  icon?: string;
  last_edited_time?: string;
}

// ============================================================================
// Storage Types
// ============================================================================

export interface StorageInfo {
  quota: number;
  used: number;
  remaining: number;
  percentage: number;
}

export interface StorageResponse {
  success: boolean;
  storage_quota: number;
  storage_used: number;
}

// ============================================================================
// Error Types
// ============================================================================

export interface ApiError {
  message: string;
  code?: string;
  statusCode?: number;
  details?: Record<string, any>;
}

// ============================================================================
// Streaming Response Types
// ============================================================================

export interface StreamingTokenData {
  type: 'token';
  token: string;
}

export interface StreamingContextData {
  type: 'context';
  count: number;
  chunks?: any[];
}

export interface StreamingDoneData {
  type: 'done';
  tokens?: number;
  cost?: number;
}

export interface StreamingErrorData {
  type: 'error';
  error: string;
}

export type StreamingData =
  | StreamingTokenData
  | StreamingContextData
  | StreamingDoneData
  | StreamingErrorData;

// ============================================================================
// Analytics & KPI Types
// ============================================================================

export interface KPI {
  ideation_velocity: number;
  correction_loop_rate: number;
  output_usefulness: number;
  calculated_at: string;
}

export interface UsageStats {
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  active_users: number;
}
