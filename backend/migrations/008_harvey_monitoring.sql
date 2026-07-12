-- Harvey Agent Monitoring Layer
-- Agent registry + evaluation history for independent Harvey output scoring
-- Run via Supabase SQL editor or local migration tool

-- 1. Harvey Agent Registry
CREATE TABLE IF NOT EXISTS harvey_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    agent_type TEXT NOT NULL CHECK (agent_type IN (
        'contract_review', 'due_diligence', 'legal_research',
        'document_drafting', 'regulatory_monitor', 'litigation_support',
        'knowledge_management', 'general_assistant'
    )),
    harvey_agent_id TEXT,
    system_prompt TEXT,
    evaluation_schedule TEXT DEFAULT 'weekly' CHECK (evaluation_schedule IN (
        'daily', 'weekly', 'biweekly', 'monthly', 'per_invocation'
    )),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'retired')),
    baseline_snapshot_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_harvey_agents_client ON harvey_agents(client_id);
CREATE INDEX IF NOT EXISTS idx_harvey_agents_status ON harvey_agents(status);
CREATE INDEX IF NOT EXISTS idx_harvey_agents_type ON harvey_agents(agent_type);

-- 2. Harvey Evaluation Runs
CREATE TABLE IF NOT EXISTS harvey_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    harvey_agent_id UUID NOT NULL REFERENCES harvey_agents(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,

    -- Input: what was evaluated
    user_prompt TEXT,
    harvey_response TEXT,
    evaluation_context TEXT,          -- additional context (jurisdiction, practice area, etc.)

    -- 4-dimension scores (from AESOP scoring engine)
    accuracy_score NUMERIC CHECK (accuracy_score >= 0 AND accuracy_score <= 100),
    safety_score NUMERIC CHECK (safety_score >= 0 AND safety_score <= 100),
    bias_score NUMERIC CHECK (bias_score >= 0 AND bias_score <= 100),
    compliance_score NUMERIC CHECK (compliance_score >= 0 AND compliance_score <= 100),

    -- Weighted final
    final_score NUMERIC CHECK (final_score >= 0 AND final_score <= 100),
    certification_level TEXT CHECK (certification_level IS NULL OR certification_level IN (
        'Platinum', 'Gold', 'Silver', 'Bronze'
    )),
    veto_triggered BOOLEAN DEFAULT false,

    -- Full evaluation reports (per dimension)
    accuracy_report TEXT,
    safety_report TEXT,
    bias_report TEXT,
    compliance_report TEXT,
    synthesis_report TEXT,

    -- Cost tracking
    evaluation_cost_usd NUMERIC DEFAULT 0,
    evaluation_time_ms INTEGER DEFAULT 0,

    -- Drift detection
    is_drift_check BOOLEAN DEFAULT false,
    drift_score NUMERIC,              -- 0-100, higher = more drift
    drift_details JSONB,

    -- Meta
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    )),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_harvey_evals_agent ON harvey_evaluations(harvey_agent_id);
CREATE INDEX IF NOT EXISTS idx_harvey_evals_status ON harvey_evaluations(status);
CREATE INDEX IF NOT EXISTS idx_harvey_evals_created ON harvey_evaluations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_harvey_evals_drift ON harvey_evaluations(harvey_agent_id, is_drift_check, created_at DESC);

-- 3. Drift Alerts
CREATE TABLE IF NOT EXISTS harvey_drift_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    harvey_agent_id UUID NOT NULL REFERENCES harvey_agents(id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES harvey_evaluations(id) ON DELETE SET NULL,

    drift_score NUMERIC NOT NULL,     -- 0-100
    severity TEXT NOT NULL DEFAULT 'low' CHECK (severity IN ('low', 'moderate', 'high', 'critical')),
    eroded_dimensions TEXT[],         -- which dimensions degraded
    summary TEXT,
    recommendations TEXT[],

    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_harvey_drift_alerts_agent ON harvey_drift_alerts(harvey_agent_id);
CREATE INDEX IF NOT EXISTS idx_harvey_drift_alerts_severity ON harvey_drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_harvey_drift_alerts_created ON harvey_drift_alerts(created_at DESC);

-- 4. RLS (respect existing client isolation pattern)
ALTER TABLE harvey_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvey_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvey_drift_alerts ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS; client-scoped policies for anon/authenticated
CREATE POLICY "Service role full access on harvey_agents"
    ON harvey_agents FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on harvey_evaluations"
    ON harvey_evaluations FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on harvey_drift_alerts"
    ON harvey_drift_alerts FOR ALL
    USING (true)
    WITH CHECK (true);
