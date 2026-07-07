-- Migration: Add Performance Optimization Indexes
-- Description: Add composite indexes for common query patterns to improve performance

-- Index for contract list queries (most common pattern)
-- Covers: uploaded_by filter + ordering by uploaded_at
CREATE INDEX IF NOT EXISTS idx_documents_user_uploaded_id
ON documents(uploaded_by, uploaded_at DESC, id);

-- Composite index for contract_analysis joins
-- Speeds up joins with documents table
CREATE INDEX IF NOT EXISTS idx_contract_analysis_document_fields
ON contract_analysis(document_id, overall_risk_level, risk_score, review_status);

-- Composite index for filtered list queries
-- Covers: risk_level + review_status filtering + ordering
CREATE INDEX IF NOT EXISTS idx_contract_analysis_risk_review
ON contract_analysis(overall_risk_level, review_status, created_at DESC);

-- Partial index for high-priority tab (human_review_required = true)
-- Only indexes rows where human review is required (smaller, faster)
CREATE INDEX IF NOT EXISTS idx_contract_analysis_high_priority
ON contract_analysis(overall_risk_level, created_at DESC)
WHERE human_review_required = true;

-- Index for legal standards client filtering (default standards)
CREATE INDEX IF NOT EXISTS idx_legal_standards_default
ON legal_standards(contract_type, category, is_active)
WHERE client_id IS NULL;

-- Index for legal standards client filtering (client-specific)
CREATE INDEX IF NOT EXISTS idx_legal_standards_client
ON legal_standards(client_id, contract_type, category, is_active)
WHERE client_id IS NOT NULL;

-- Index for documents processing status queries
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_processed
ON documents(uploaded_by, processed, uploaded_at DESC);
