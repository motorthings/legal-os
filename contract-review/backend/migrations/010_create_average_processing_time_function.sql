-- Migration: Create function to calculate average contract processing time
-- Description: Returns average time in minutes from contract creation to completion
-- Created: 2025-12-06

CREATE OR REPLACE FUNCTION get_average_processing_time()
RETURNS TABLE (avg_minutes NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROUND(EXTRACT(EPOCH FROM (MAX(pl.timestamp) - MIN(pl.timestamp))) / 60, 2) as avg_minutes
    FROM contract_processing_logs pl
    INNER JOIN contract_analyses c ON pl.contract_id = c.id
    WHERE pl.step = 'completed'
    GROUP BY pl.contract_id
    HAVING MAX(pl.timestamp) IS NOT NULL
    ORDER BY MAX(pl.timestamp) DESC
    LIMIT 100;  -- Average of last 100 completed contracts
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_average_processing_time() TO authenticated;
