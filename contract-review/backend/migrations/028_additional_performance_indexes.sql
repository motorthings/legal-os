-- Migration 028: Additional Performance Indexes
-- Date: 2025-12-04
-- Purpose: Add indexes identified during performance analysis
-- Impact: Improves analytics queries and document processing status lookups

-- ============================================================================
-- DOCUMENTS TABLE - Processing Status Index
-- ============================================================================

-- Index for documents by processing status (used in admin views and monitoring)
-- Query pattern: SELECT * FROM documents WHERE processing_status = 'processing'
CREATE INDEX IF NOT EXISTS idx_documents_processing_status
ON documents(processing_status)
WHERE processing_status IS NOT NULL;

-- ============================================================================
-- CONVERSATIONS TABLE - Client Analytics Index
-- ============================================================================

-- Composite index for client conversations by created_at (used in analytics)
-- Query pattern: SELECT * FROM conversations WHERE client_id = ? AND created_at >= ?
CREATE INDEX IF NOT EXISTS idx_conversations_client_created
ON conversations(client_id, created_at DESC);

-- ============================================================================
-- MESSAGES TABLE - Timestamp Range Index
-- ============================================================================

-- Index for messages by timestamp (used in analytics date range queries)
-- Query pattern: SELECT * FROM messages WHERE timestamp >= ? AND timestamp <= ?
CREATE INDEX IF NOT EXISTS idx_messages_timestamp_range
ON messages(timestamp);

-- ============================================================================
-- DOCUMENTS TABLE - Upload Date Range Index
-- ============================================================================

-- Index for documents by upload date (used in analytics)
-- Query pattern: SELECT * FROM documents WHERE uploaded_at >= ? AND uploaded_at <= ?
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at_range
ON documents(uploaded_at);

-- ============================================================================
-- USERS TABLE - Created At Index
-- ============================================================================

-- Index for users by created_at (used in analytics cumulative user counts)
-- Query pattern: SELECT * FROM users WHERE created_at <= ?
CREATE INDEX IF NOT EXISTS idx_users_created_at
ON users(created_at);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname IN (
        'idx_documents_processing_status',
        'idx_conversations_client_created',
        'idx_messages_timestamp_range',
        'idx_documents_uploaded_at_range',
        'idx_users_created_at'
    );

    RAISE NOTICE 'Migration 028: Created % of 5 performance indexes', idx_count;
END $$;
