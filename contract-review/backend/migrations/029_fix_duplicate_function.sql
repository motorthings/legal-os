-- Migration 029 Fix: Remove duplicate get_contract_stats functions
-- Date: 2025-12-04
-- Purpose: Drop all existing get_contract_stats functions and create the correct one

-- ============================================================================
-- DROP ALL EXISTING get_contract_stats FUNCTIONS
-- ============================================================================

-- Drop all versions of the function (handles different signatures)
DROP FUNCTION IF EXISTS get_contract_stats();
DROP FUNCTION IF EXISTS get_contract_stats(uuid);
DROP FUNCTION IF EXISTS get_contract_stats(user_uuid uuid);

-- ============================================================================
-- CREATE THE CORRECT get_contract_stats FUNCTION
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
    function_count INTEGER;
BEGIN
    -- Count how many get_contract_stats functions exist
    SELECT COUNT(*) INTO function_count
    FROM pg_proc
    WHERE proname = 'get_contract_stats';

    RAISE NOTICE 'Migration 029 Fix Verification:';
    RAISE NOTICE '  - get_contract_stats functions found: %', function_count;

    IF function_count = 0 THEN
        RAISE EXCEPTION 'Migration 029 fix failed: get_contract_stats function not created';
    ELSIF function_count > 1 THEN
        RAISE WARNING 'Multiple get_contract_stats functions still exist: %', function_count;
    ELSE
        RAISE NOTICE '  ✅ Exactly one get_contract_stats function exists';
    END IF;
END $$;

-- Test the function
SELECT * FROM get_contract_stats();
