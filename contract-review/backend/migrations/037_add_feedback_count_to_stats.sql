-- Migration 037: Add Feedback Count to Contract Stats
-- Date: 2025-12-06
-- Purpose: Add count of contracts with expert feedback to dashboard stats
-- Impact: Enables tracking of human review engagement

-- ============================================================================
-- UPDATE GET_CONTRACT_STATS FUNCTION
-- ============================================================================

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS get_contract_stats();

CREATE OR REPLACE FUNCTION get_contract_stats()
RETURNS TABLE (
    contracts_pending_review BIGINT,
    contracts_high_risk BIGINT,
    contracts_completed_week BIGINT,
    average_review_time_minutes NUMERIC,
    avg_confidence_score NUMERIC,
    contracts_with_feedback BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        -- Contracts pending review
        (SELECT COUNT(*)
         FROM contract_analysis
         WHERE processing_status = 'completed'
         AND team_review_status IN ('pending', 'in_review')
        )::BIGINT,

        -- High risk contracts
        (SELECT COUNT(*)
         FROM contract_analysis
         WHERE overall_risk_level = 'High'
        )::BIGINT,

        -- Contracts completed in last 7 days
        (SELECT COUNT(*)
         FROM contract_analysis
         WHERE processing_status = 'completed'
         AND created_at >= NOW() - INTERVAL '7 days'
        )::BIGINT,

        -- Average review time in minutes
        (SELECT COALESCE(AVG(processing_time_seconds) / 60, 0)
         FROM contract_analysis
         WHERE processing_time_seconds IS NOT NULL
         AND processing_status = 'completed'
        )::NUMERIC,

        -- Average confidence score
        (SELECT COALESCE(AVG(confidence_score), 0)
         FROM contract_analysis
         WHERE confidence_score IS NOT NULL
         AND processing_status = 'completed'
        )::NUMERIC,

        -- NEW: Count of contracts with expert feedback
        (SELECT COUNT(*)
         FROM contract_analysis
         WHERE team_feedback IS NOT NULL
         AND team_feedback != ''
        )::BIGINT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    result_record RECORD;
BEGIN
    -- Test the function
    SELECT * INTO result_record FROM get_contract_stats();

    RAISE NOTICE 'Migration 037 Verification:';
    RAISE NOTICE '  - Function updated successfully';
    RAISE NOTICE '  - Contracts with feedback: %', result_record.contracts_with_feedback;

    IF result_record.contracts_with_feedback IS NULL THEN
        RAISE EXCEPTION 'Migration 037 failed: feedback count is NULL';
    END IF;
END $$;
