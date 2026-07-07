-- Migration 029: Contract Analysis System
-- Creates tables and functions for contract review workflow

-- ============================================================================
-- Contract Analysis Results Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS contract_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Contract Metadata
    contract_type TEXT,
    parties JSONB, -- Array of party names
    effective_date DATE,
    term_length TEXT,
    total_value NUMERIC(15,2),

    -- Key Terms (stored as JSONB for flexibility)
    ip_rights JSONB,
    liability_terms JSONB,
    termination_terms JSONB,
    data_handling JSONB,
    payment_terms JSONB,

    -- Risk Assessment
    overall_risk_level TEXT CHECK (overall_risk_level IN ('high', 'medium', 'low')),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    red_flags JSONB DEFAULT '[]'::jsonb, -- Array of critical issues
    yellow_flags JSONB DEFAULT '[]'::jsonb, -- Array of moderate concerns

    -- Human Review Flags
    human_review_required BOOLEAN DEFAULT false,
    human_review_reasons JSONB DEFAULT '[]'::jsonb,
    human_review_questions JSONB DEFAULT '[]'::jsonb,
    human_review_priority TEXT CHECK (human_review_priority IN ('urgent', 'high', 'normal')),

    -- Review Decision (filled in by human reviewer)
    review_status TEXT DEFAULT 'pending' CHECK (review_status IN ('pending', 'approved', 'approved_with_conditions', 'negotiation_required', 'rejected')),
    reviewer_notes TEXT,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,

    -- Summary and Recommendations
    executive_summary TEXT,
    recommendations JSONB DEFAULT '[]'::jsonb,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),

    -- Full Analysis (complete JSON response from Claude)
    full_analysis JSONB,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes for common queries
    CONSTRAINT unique_document_analysis UNIQUE(document_id)
);

-- Create indexes for performance
CREATE INDEX idx_contract_analysis_document_id ON contract_analysis(document_id);
CREATE INDEX idx_contract_analysis_risk_level ON contract_analysis(overall_risk_level);
CREATE INDEX idx_contract_analysis_review_status ON contract_analysis(review_status);
CREATE INDEX idx_contract_analysis_human_review ON contract_analysis(human_review_required);
CREATE INDEX idx_contract_analysis_created_at ON contract_analysis(created_at DESC);

-- ============================================================================
-- Contract Chat History Table
-- For human-in-the-loop conversations about specific contracts
-- ============================================================================

CREATE TABLE IF NOT EXISTS contract_chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_analysis_id UUID NOT NULL REFERENCES contract_analysis(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),

    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contract_chat_analysis_id ON contract_chat_history(contract_analysis_id);
CREATE INDEX idx_contract_chat_created_at ON contract_chat_history(created_at DESC);

-- ============================================================================
-- Update documents table to support contract-specific fields
-- ============================================================================

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS contract_type TEXT,
ADD COLUMN IF NOT EXISTS counterparty_name TEXT,
ADD COLUMN IF NOT EXISTS contract_value NUMERIC(15,2);

-- ============================================================================
-- RLS Policies for contract_analysis
-- ============================================================================

-- Enable RLS
ALTER TABLE contract_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_chat_history ENABLE ROW LEVEL SECURITY;

-- Users can view their own contract analyses
CREATE POLICY contract_analysis_user_view ON contract_analysis
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = contract_analysis.document_id
            AND d.uploaded_by = auth.uid()
        )
    );

-- Users can update review decisions on their own contracts
CREATE POLICY contract_analysis_user_update ON contract_analysis
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = contract_analysis.document_id
            AND d.uploaded_by = auth.uid()
        )
    );

-- Admins can view and update all analyses
CREATE POLICY contract_analysis_admin_all ON contract_analysis
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

-- Chat history policies (users can view/insert for their contracts)
CREATE POLICY contract_chat_user_view ON contract_chat_history
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY contract_chat_user_insert ON contract_chat_history
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get contract analysis summary stats
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
    JOIN documents d ON ca.document_id = d.id
    WHERE user_uuid IS NULL OR d.uploaded_by = user_uuid;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update contract analysis (trigger for updated_at)
CREATE OR REPLACE FUNCTION update_contract_analysis_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_contract_analysis_timestamp
    BEFORE UPDATE ON contract_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_contract_analysis_timestamp();

-- ============================================================================
-- Sample Data for Testing (commented out for production)
-- ============================================================================

-- Uncomment to seed test data:
-- INSERT INTO documents (filename, uploaded_by, client_id, contract_type, counterparty_name, contract_value)
-- VALUES ('test_vendor_agreement.pdf', 'user-uuid-here', 'client-uuid-here', 'Vendor Agreement', 'Acme Corp', 150000.00);

COMMENT ON TABLE contract_analysis IS 'Stores AI-generated contract analysis results with risk assessments';
COMMENT ON TABLE contract_chat_history IS 'Stores human-in-the-loop chat conversations about specific contracts';
COMMENT ON COLUMN contract_analysis.full_analysis IS 'Complete JSON response from Claude API for audit trail';
COMMENT ON COLUMN contract_analysis.human_review_required IS 'Flags contracts that require mandatory human expert review';
COMMENT ON FUNCTION get_contract_stats IS 'Returns summary statistics for contract portfolio (filterable by user)';
