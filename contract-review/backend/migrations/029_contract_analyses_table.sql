-- Migration 029: Contract Analyses Table
-- Date: 2025-12-04
-- Purpose: Create table for storing contract upload and analysis data
-- Impact: Enables contract review workflow with AI analysis results

-- ============================================================================
-- CONTRACT_ANALYSES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS contract_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- File metadata
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL, -- Supabase Storage path
    file_size BIGINT, -- bytes

    -- Contract classification
    contract_type TEXT NOT NULL CHECK (contract_type IN ('vendor', 'customer', 'employment', 'dpa', 'general')),

    -- Analysis results
    analysis_result JSONB, -- Structured JSON output from Claude API
    risk_level TEXT CHECK (risk_level IN ('high', 'medium', 'low')),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),

    -- Processing status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'analyzing', 'completed', 'failed', 'approved', 'rejected')),

    -- Timestamps
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,

    -- User tracking
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Standard audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR COMMON QUERIES
-- ============================================================================

-- Index for filtering by status (admin dashboard, processing queue)
-- Query pattern: SELECT * FROM contract_analyses WHERE status = 'pending'
CREATE INDEX IF NOT EXISTS idx_contract_analyses_status
ON contract_analyses(status);

-- Index for filtering by risk level (admin dashboard high-risk contracts)
-- Query pattern: SELECT * FROM contract_analyses WHERE risk_level = 'high'
CREATE INDEX IF NOT EXISTS idx_contract_analyses_risk_level
ON contract_analyses(risk_level)
WHERE risk_level IS NOT NULL;

-- Index for filtering by contract type (analytics by type)
-- Query pattern: SELECT * FROM contract_analyses WHERE contract_type = 'vendor'
CREATE INDEX IF NOT EXISTS idx_contract_analyses_contract_type
ON contract_analyses(contract_type);

-- Composite index for date range queries (analytics dashboard)
-- Query pattern: SELECT * FROM contract_analyses WHERE uploaded_at >= ? AND uploaded_at <= ?
CREATE INDEX IF NOT EXISTS idx_contract_analyses_uploaded_at
ON contract_analyses(uploaded_at DESC);

-- Index for user's contracts
-- Query pattern: SELECT * FROM contract_analyses WHERE uploaded_by = ?
CREATE INDEX IF NOT EXISTS idx_contract_analyses_uploaded_by
ON contract_analyses(uploaded_by)
WHERE uploaded_by IS NOT NULL;

-- Composite index for filtering by status and uploaded date (processing queue)
-- Query pattern: SELECT * FROM contract_analyses WHERE status = 'pending' ORDER BY uploaded_at
CREATE INDEX IF NOT EXISTS idx_contract_analyses_status_uploaded
ON contract_analyses(status, uploaded_at DESC);

-- ============================================================================
-- UPDATED_AT TRIGGER
-- ============================================================================

-- Create trigger function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_contract_analyses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_contract_analyses_updated_at ON contract_analyses;
CREATE TRIGGER trigger_contract_analyses_updated_at
    BEFORE UPDATE ON contract_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_contract_analyses_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS
ALTER TABLE contract_analyses ENABLE ROW LEVEL SECURITY;

-- Policy: Admins can see all contracts
CREATE POLICY contract_analyses_admin_all
ON contract_analyses
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.role = 'admin'
    )
);

-- Policy: Users can see their own contracts
CREATE POLICY contract_analyses_user_own
ON contract_analyses
FOR SELECT
TO authenticated
USING (uploaded_by = auth.uid());

-- Policy: Users can insert their own contracts
CREATE POLICY contract_analyses_user_insert
ON contract_analyses
FOR INSERT
TO authenticated
WITH CHECK (uploaded_by = auth.uid());

-- ============================================================================
-- STATS FUNCTION FOR ADMIN DASHBOARD
-- ============================================================================

CREATE OR REPLACE FUNCTION get_contract_stats()
RETURNS TABLE (
    contracts_pending_review BIGINT,
    contracts_high_risk BIGINT,
    contracts_completed_week BIGINT,
    average_review_days NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        -- Pending review: status is pending or analyzing
        (SELECT COUNT(*) FROM contract_analyses WHERE status IN ('pending', 'analyzing'))::BIGINT,

        -- High risk: risk_level is high
        (SELECT COUNT(*) FROM contract_analyses WHERE risk_level = 'high')::BIGINT,

        -- Completed in last 7 days
        (SELECT COUNT(*) FROM contract_analyses
         WHERE status = 'completed'
         AND analyzed_at >= NOW() - INTERVAL '7 days')::BIGINT,

        -- Average days from upload to analysis completion
        (SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (analyzed_at - uploaded_at)) / 86400), 0)
         FROM contract_analyses
         WHERE status = 'completed'
         AND analyzed_at IS NOT NULL)::NUMERIC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Check table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'contract_analyses'
    ) INTO table_exists;

    -- Count indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = 'contract_analyses';

    -- Count policies
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename = 'contract_analyses';

    RAISE NOTICE 'Migration 029 Verification:';
    RAISE NOTICE '  - Table exists: %', table_exists;
    RAISE NOTICE '  - Indexes created: %', index_count;
    RAISE NOTICE '  - RLS policies created: %', policy_count;

    IF NOT table_exists THEN
        RAISE EXCEPTION 'Migration 029 failed: contract_analyses table not created';
    END IF;
END $$;
