# Harvey Agent Monitoring Layer — Build Plan

## The Pivot

Legal-OS functions that overlap with Harvey (contract review, due diligence) stay as POC demos. The build focus shifts to what Harvey can't do: **evaluate its own outputs, detect quality drift, and prove the boundary held.**

AESOP already has the evaluation architecture for this. The pattern ports directly: register Harvey agents → run multi-dimension evaluations → score with veto rules → monitor for drift over time.

---

## What We're Adding

### 1. Harvey Agent Registry

**What:** Register Harvey agents as monitored entities. Each gets an ID, evaluation schedule, and baseline snapshot (the system prompt or agent instructions at registration time).

**Schema:**
```sql
create table harvey_agents (
    id uuid primary key,
    client_id uuid references clients(id),
    name text not null,              -- e.g., "Contract Review Agent v2"
    agent_type text not null,        -- 'contract_review', 'due_diligence', 'legal_research', 'document_drafting'
    harvey_agent_id text,            -- Harvey's internal agent ID
    system_prompt text,              -- baseline instructions snapshot
    evaluation_schedule text,        -- 'daily', 'weekly', 'per_invocation'
    status text default 'active',
    created_at timestamptz default now()
);
```

### 2. Four-Dimension Evaluation Pipeline

**What:** AESOP-style multi-agent evaluation, adapted for legal outputs:

| Dimension | Weight | What it checks | Adapted from AESOP |
|---|---|---|---|
| **Accuracy** | 1.5x | Hallucination detection, citation verification, factual correctness | `accuracy_scorer.txt` |
| **Safety** | 1.5x | Confidentiality boundaries, PII detection, ethical guardrails | `safety_agent.py` |
| **Bias** | 1.5x | Jurisdictional fairness, demographic neutrality, party balance | `bias_probe_agent.py` |
| **Compliance** | 1.0x | ABA 512 alignment, privilege preservation, reasonable fee implications | `legal_compliance_agent.txt` |

**Veto rule (from AESOP):** any Tier 1 score (Accuracy, Safety, Bias) below 75 caps final at 74.9.

**Flow:**
```
Harvey output → Router (classify type) → 4 evaluators in parallel
                                        → Scoring engine (weighted + veto)
                                        → Audit trail (full prompt, response, scores)
                                        → Quality review queue (if flagged)
```

**New files:**
- `backend/app/services/harvey_evaluator.py` — orchestrates the 4-dimension evaluation
- `backend/app/agents/prompts/harvey_accuracy.txt` — accuracy evaluation prompt
- `backend/app/agents/prompts/harvey_safety.txt` — safety evaluation prompt  
- `backend/app/agents/prompts/harvey_bias.txt` — bias evaluation prompt
- `backend/app/agents/prompts/harvey_compliance.txt` — compliance evaluation prompt
- `backend/migrations/008_harvey_monitoring.sql` — schema

### 3. Scoring Engine

**What:** Port AESOP's `helpers/scoring.py` to legal-os. Same formula:
- Tier 1 (1.5x): Accuracy, Safety, Bias
- Tier 2 (1.0x): Compliance
- Veto: any Tier 1 < 75 → final capped at 74.9
- Certification: Platinum ≥ 90, Gold ≥ 85, Silver ≥ 80, Bronze ≥ 75

**New file:** `backend/app/services/scoring.py`

### 4. Harvey Drift Monitor

**What:** Periodic re-evaluation of Harvey outputs against baseline. Same prompt, different day → is quality degrading?

**How it works:**
1. Snapshot Harvey's system prompt at registration (baseline)
2. Weekly: submit a standard evaluation prompt to Harvey, capture output
3. Run the same 4-dimension evaluation on the output
4. Compare scores against historical baseline
5. Alert if drift exceeds threshold (score drops >10 points in any dimension)

**New files:**
- `backend/app/services/drift_monitor.py` — scheduler + comparison logic
- `backend/app/agents/prompts/harvey_drift.txt` — drift detection prompt

### 5. Harvey Quality Dashboard

**What:** Frontend view showing Harvey-specific metrics:

- **Agent quality scores** — Accuracy, Safety, Bias, Compliance per agent, with trends
- **Drift alerts** — which agents are degrading, when, by how much
- **Override tracking** — how often attorneys correct Harvey outputs
- **Evaluation history** — timeline of every evaluation with score decomposition
- **Certification status** — Platinum/Gold/Silver/Bronze per agent

**New files:**
- `frontend/src/app/harvey-monitor/page.tsx` — Harvey quality dashboard
- `frontend/src/lib/harvey-api.ts` — API client
- `backend/app/api/routes/harvey_monitor.py` — API endpoints

---

## Build Order

| # | Component | Effort | Depends on |
|---|---|---|---|
| 1 | Harvey Agent Registry (schema + API) | S | Nothing |
| 2 | Scoring Engine (port from AESOP) | S | Nothing |
| 3 | 4 Evaluation Prompts | S | #2 |
| 4 | Harvey Evaluator (orchestrator) | M | #1, #2, #3 |
| 5 | Drift Monitor | M | #1, #3, #4 |
| 6 | Harvey Quality Dashboard | M | #1, #4, #5 |

Items 1-3 can start in parallel. Total: ~1 week.

---

## What This Tells APC

"Harvey is your AI engine. But Harvey can't grade its own homework. Legal-OS provides the independent evaluation layer: every Harvey output scored across accuracy, safety, bias, and compliance. Quality drift detected before it becomes a sanction event. The 700+ hallucination cases in courts right now? Those happened because nobody was checking. This layer makes checking systematic."

## What We're NOT Building

- Harvey API integration (Technology team owns this — we evaluate outputs, not trigger them)
- Replacement contract review or due diligence functions (Harvey does these, ours stay as POC demos)
- Full AESOP agent builder (out of scope — this is the evaluation layer only)
