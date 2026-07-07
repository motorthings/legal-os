-- Migration 032: Fix get_contract_stats function to use contract_analysis table
-- Description: The actual data is in contract_analysis (singular), not contract_analyses (plural)
-- The columns are overall_risk_level and review_status, not risk_level and status
-- Created: 2025-12-06

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
        COUNT(*) FILTER (WHERE ca.overall_risk_level = 'high')::BIGINT as high_risk_count,
        COUNT(*) FILTER (WHERE ca.overall_risk_level = 'medium')::BIGINT as medium_risk_count,
        COUNT(*) FILTER (WHERE ca.overall_risk_level = 'low')::BIGINT as low_risk_count,
        COUNT(*) FILTER (WHERE ca.review_status = 'pending')::BIGINT as pending_review_count,
        COUNT(*) FILTER (WHERE ca.human_review_required = true)::BIGINT as human_review_required_count,
        ROUND(AVG(ca.risk_score), 2) as avg_risk_score,
        ROUND(AVG(ca.confidence_score), 2) as avg_confidence_score
    FROM contract_analysis ca
    LEFT JOIN documents d ON ca.document_id = d.id
    WHERE user_uuid IS NULL OR d.uploaded_by = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_contract_stats(UUID) TO authenticated;

COMMENT ON FUNCTION get_contract_stats IS 'Get contract analysis statistics including risk levels and pending reviews from contract_analysis table';
