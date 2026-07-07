-- Migration 034: Add Team Feedback Columns
-- Date: 2025-12-06
-- Purpose: Add team feedback capability to capture human review feedback for AI improvement
-- Impact: Enables team members to provide structured feedback on AI analysis quality

-- ============================================================================
-- ADD TEAM FEEDBACK COLUMNS TO CONTRACT_ANALYSES
-- ============================================================================

-- Add team_feedback column to store feedback text
ALTER TABLE contract_analyses
ADD COLUMN IF NOT EXISTS team_feedback TEXT;

-- Add feedback_submitted_at timestamp
ALTER TABLE contract_analyses
ADD COLUMN IF NOT EXISTS feedback_submitted_at TIMESTAMP WITH TIME ZONE;

-- Add feedback_submitted_by to track who submitted the feedback
ALTER TABLE contract_analyses
ADD COLUMN IF NOT EXISTS feedback_submitted_by UUID REFERENCES users(id) ON DELETE SET NULL;

-- ============================================================================
-- ADD INDEX FOR FEEDBACK QUERIES
-- ============================================================================

-- Index for finding contracts with feedback
CREATE INDEX IF NOT EXISTS idx_contract_analyses_has_feedback
ON contract_analyses(feedback_submitted_at)
WHERE feedback_submitted_at IS NOT NULL;

-- Index for finding feedback by user
CREATE INDEX IF NOT EXISTS idx_contract_analyses_feedback_by_user
ON contract_analyses(feedback_submitted_by)
WHERE feedback_submitted_by IS NOT NULL;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON COLUMN contract_analyses.team_feedback IS
'Long-form feedback from human reviewers about AI analysis quality, missed items, and improvement suggestions';

COMMENT ON COLUMN contract_analyses.feedback_submitted_at IS
'Timestamp when team feedback was submitted';

COMMENT ON COLUMN contract_analyses.feedback_submitted_by IS
'User ID of team member who submitted the feedback';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    column_count INTEGER;
    index_count INTEGER;
BEGIN
    -- Count new columns
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'contract_analyses'
    AND column_name IN ('team_feedback', 'feedback_submitted_at', 'feedback_submitted_by');

    -- Count new indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = 'contract_analyses'
    AND indexname LIKE 'idx_contract_analyses_%feedback%';

    RAISE NOTICE 'Migration 034 Verification:';
    RAISE NOTICE '  - Columns added: % (expected: 3)', column_count;
    RAISE NOTICE '  - Indexes created: % (expected: 2)', index_count;

    IF column_count < 3 THEN
        RAISE EXCEPTION 'Migration 034 failed: Not all columns were added';
    END IF;
END $$;
