-- Migration 030: Fix database functions to match actual schema
-- Description: Updates get_contract_stats and get_average_processing_time functions
-- Created: 2025-12-06

-- ============================================================================
-- Fix get_contract_stats function to use contract_analyses table and risk_level column
-- ============================================================================

CREATE OR REPLACE FUNCTION get_contract_stats(user_uuid UUID DEFAULT NULL)
RETURNS TABLE (
    total_contracts BIGINT,
    high_risk_count BIGINT,
    medium_risk_count BIGINT,
    low_risk_count BIGINT,
    pending_review_count BIGINT,
    human_review_required_count BIGINT,
    avg_risk_score NUMERIC,
    avg_confidence_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_contracts,
        COUNT(*) FILTER (WHERE ca.risk_level = 'high')::BIGINT as high_risk_count,
        COUNT(*) FILTER (WHERE ca.risk_level = 'medium')::BIGINT as medium_risk_count,
        COUNT(*) FILTER (WHERE ca.risk_level = 'low')::BIGINT as low_risk_count,
        COUNT(*) FILTER (WHERE ca.status = 'pending')::BIGINT as pending_review_count,
        0::BIGINT as human_review_required_count,  -- Column doesn't exist in contract_analyses
        ROUND(AVG(ca.risk_score), 2) as avg_risk_score,
        0::NUMERIC as avg_confidence_score  -- Column doesn't exist in contract_analyses
    FROM contract_analyses ca
    LEFT JOIN documents d ON ca.id = d.id  -- Assuming same ID if linked
    WHERE user_uuid IS NULL OR (d.id IS NOT NULL AND d.uploaded_by = user_uuid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_contract_stats(UUID) TO authenticated;

-- ============================================================================
-- Fix get_average_processing_time function to use correct column names
-- ============================================================================

CREATE OR REPLACE FUNCTION get_average_processing_time()
RETURNS TABLE (avg_minutes NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROUND(AVG(time_diff), 2) as avg_minutes
    FROM (
        SELECT
            EXTRACT(EPOCH FROM (MAX(pl.created_at) - MIN(pl.created_at))) / 60 as time_diff
        FROM contract_processing_logs pl
        WHERE pl.step_status = 'completed'
        GROUP BY pl.document_id
        HAVING MAX(pl.created_at) IS NOT NULL
        ORDER BY MAX(pl.created_at) DESC
        LIMIT 100  -- Average of last 100 completed documents
    ) AS subquery
    WHERE time_diff > 0;  -- Exclude zero or negative times
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_average_processing_time() TO authenticated;
