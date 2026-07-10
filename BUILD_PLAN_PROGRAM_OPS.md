# Legal-OS: Program Operations Layer — Build Plan

## Context

The legal-os repo has strong Layer 2 (AI Functions) and Layer 1 (Governance). What it's missing is **Layer 3 — Program Operations**: the tools the K&I Program Manager uses day to day. Each piece maps directly to a JD responsibility.

The `MetricsCollector` captures raw telemetry (tokens, time, cost) — but that's plumbing, not a framework. The JD asks for "frameworks to track AI solution performance, including time saved, cost impact, and quality metrics." The framework layer doesn't exist yet. We build that first, then the dashboard and reports that display it.

## Build Order

---

### 1. ROI Tracking Framework (M+ effort, ~1 week) ← HIGHEST PRIORITY

**Maps to JD:** "Develop frameworks to track AI solution performance, including time saved, cost impact, and quality metrics" — the full sentence, all three dimensions. Everything else (dashboard, client reports, RFP responses) depends on this.

**What exists:** `MetricsCollector` captures raw invocation data — `processing_time_ms`, `human_time_equivalent_ms`, `time_saved_ms`, `cost_usd` (API tokens only). Baselines exist as a single `baseline_seconds` integer with no methodology.

**What's missing — the framework layer:**

#### 1a. Cost Impact Engine
Time saved isn't cost impact. Cost impact = time saved × the right rate.

- New DB table: `rate_cards` — `id, client_id, practice_group_id, rate_type (blended/partner/associate), hourly_rate_usd, effective_from, effective_to, created_at`
- New service: `backend/app/services/roi.py` — `calculate_cost_avoided(time_saved_ms, practice_group_id, client_id)` → looks up the right rate, returns USD
- Per-function, per-quarter aggregation: total cost avoided = Σ (time_saved_ms / 3600000) × rate
- This is the number the JD means by "cost impact." Not API token cost — human cost avoided.

#### 1b. Baseline Calibration Framework
"You saved 30 minutes" isn't defensible without methodology.

- Extend `time_saved_baselines` table: add `methodology` (text — how was this established?), `calibrated_by` (user_id), `calibrated_at` (timestamp), `sample_size` (int — how many manual timings?), `confidence_level` (low/medium/high)
- New endpoints: `GET /api/roi/baselines` (list with methodology), `PUT /api/roi/baselines/{id}` (update with calibration metadata)
- The point: when a partner or client asks "how do you know this used to take 2 hours?", the answer is in the baseline record, not an assertion

#### 1c. Quality Metrics Framework
The JD asks for "quality metrics." Currently a free-text `result_quality` string.

- New DB table: `quality_metrics` — `id, invocation_id, function_id, client_id, human_override (bool), override_reason, reviewer_agreement (bool), false_positive (bool), accuracy_category (correct/minor_issues/major_issues/incorrect), reviewer_notes, created_at`
- New endpoints: `POST /api/roi/quality` (record quality review), `GET /api/roi/quality/summary?function_id=X&period=Q3` (aggregate — override rate, accuracy rate, false positive rate)
- Integrates with existing `audit.py::record_human_override()` — when an attorney overrides, the quality record is created
- Key metric: **override rate per function** — if 40% of outputs get overridden, the AI isn't helping

#### 1d. Adoption Rate Calculator
Adoption isn't "who clicked." It's "what % of eligible users are active."

- New DB table: `eligible_users` — `id, client_id, practice_group_id, user_id, eligible_since`
- New endpoint: `GET /api/roi/adoption?practice_group_id=X&period=30d` — returns: eligible_count, active_count, adoption_pct, trend vs prior period
- Active = at least one invocation in the period
- This gives the K&I PM the denominator. Without it, "50 lawyers used Harvey this month" means nothing. 50 out of 50 is great. 50 out of 500 is a problem.

#### 1e. ROI Calculation Engine
"Return on innovation" = cost avoided − AI cost.

- New endpoint: `GET /api/roi/summary?period=Q3&client_id=X` — returns:
  - Total cost avoided (time saved × rates)
  - Total AI cost (API tokens + infra estimate)
  - Net ROI = cost avoided − AI cost
  - ROI ratio = cost avoided / AI cost (e.g., "$12.40 saved for every $1 spent")
  - Breakdown by function, by practice group
- This is the number that goes in the portfolio dashboard. This is the "return on innovation" the JD asks for. This is what puts APC in the 18% that tracks ROI.

**New files:**
- `backend/app/services/roi.py` — calculation engine
- `backend/app/api/routes/roi.py` — API endpoints
- `backend/migrations/006_roi_framework.sql` — rate_cards, quality_metrics, eligible_users, baseline_calibrations extension columns
- `frontend/src/lib/roi-api.ts` — API client
- `frontend/src/app/roi/page.tsx` — ROI dashboard (or integrated into the main dashboard)

---

### 2. Portfolio Dashboard (M effort, ~1 week)

**Maps to JD:** "Maintain a portfolio dashboard highlighting adoption, client outcomes, and return on innovation"

**Depends on:** #1 (ROI framework provides the numbers)

**Backend:**
- New `backend/app/api/routes/dashboard.py` — cross-client, cross-function aggregation
- Endpoints:
  - `GET /api/dashboard/overview` — KPI cards: functions deployed, total hours saved, total cost avoided, net ROI, active users
  - `GET /api/dashboard/by-function` — per-function: invocations, hours saved, cost avoided, adoption %, quality score, ROI ratio
  - `GET /api/dashboard/by-practice-group` — per-practice-group: functions used, active/eligible users, adoption %, hours saved
  - `GET /api/dashboard/trends?months=6` — monthly time-saved, cost-avoided, and adoption trend lines
- Reuses: `roi.py` calculations, `metrics.py` rollup queries, `by_function` aggregation pattern

**Frontend:**
- New `frontend/src/app/dashboard/page.tsx`
- New `frontend/src/lib/dashboard-api.ts`
- Components: KPI card row (hours saved, cost avoided, net ROI, adoption %), function breakdown with trend sparklines, practice group adoption table

---

### 3. Client Value Report Generator (S-M effort, ~3 days)

**Maps to JD:** "Create client-facing materials and outcome reports that demonstrate measurable AI value"

**Depends on:** #1 (ROI framework provides cost-avoided numbers)

**Backend:** Reporting routes already partially built. Add:
- `GET /api/reporting/export?client_id=X&period=Q3&format=markdown` — markdown export
- Report template: executive summary, time saved, cost avoided, quality metrics, governance compliance, audit trail samples

**Frontend:**
- Rewire `frontend/src/lib/reporting-api.ts` to call real backend instead of mock
- Update `frontend/src/app/reporting/page.tsx` — keep existing UI structure, add client selector, period picker, export button

---

### 4. POC Pipeline Tracker (M effort, ~5 days)

**Maps to JD:** "Lead end-to-end delivery of AI-enabled client projects from concept through implementation"

**Backend:**
- DB migration: `007_poc_pipeline.sql` — `poc_projects` table
- New `backend/app/api/routes/poc_pipeline.py` — CRUD + feedback log
- Endpoints: list/create/update status, add feedback

**Frontend:**
- New `frontend/src/app/poc-pipeline/page.tsx` — Kanban view
- Status flow: Discovery → Build → Review → Graduated (or Cancelled)

---

### 5. AI Literacy & Enablement Kit (S effort, ~2 days)

**Maps to JD:** "Partner with Learning & Development to upskill lawyers and staff in AI literacy"

**Content only — no backend:**
- New `enablement/` directory at repo root
- `enablement/workshop-deck-outline.md` — 60-min workshop structure
- `enablement/prompt-engineering-for-lawyers.md` — practical guide with confidentiality boundaries
- `enablement/adoption-playbook.md` — champion network, lunch-and-learn format, feedback loops
- `enablement/ai-literacy-faq.md` — common lawyer questions and answers

---

### 6. Client Conversation Pack (S effort, ~2 days)

**Maps to JD:** "Serve as strategic advisor to client relationship teams on AI as value-added differentiator" and "Respond to client RFPs and surveys"

**Backend:**
- `GET /api/reporting/governance-pack?client_id=X` — one-click export: governance summary, ABA 512 compliance, data handling, audit trail samples

**Content:**
- `enablement/client-conversation-deck-outline.md`
- `enablement/rfp-response-templates.md`
- `enablement/technical-faq-for-client-cisos.md`

---

## Dependency Graph

```
#1 ROI Framework ──┬── #2 Portfolio Dashboard
                   ├── #3 Client Value Reports
                   └── #6 Client Conversation Pack (governance export)

#4 POC Pipeline Tracker (standalone — no dependency)

#5 AI Literacy Kit (standalone — content only)
```

Items 1, 4, and 5 can start in parallel. Items 2, 3, and 6 depend on #1.

## Verification

1. **ROI Framework:** Seed a rate card, set calibrated baselines, record quality reviews. Hit `/api/roi/summary` — confirm cost avoided = time_saved × rate, ROI ratio computes correctly.
2. **Dashboard:** Hit `/api/dashboard/overview` — confirm KPIs match ROI calculations. Frontend renders cards with real data.
3. **Client Report:** Hit `/api/reporting/quarterly-report` with auth — confirm aggregation pulls from ROI framework. Export markdown — confirm template renders.
4. **POC Pipeline:** CRUD a project through all statuses — confirm Kanban reflects state.
5. **Enablement content:** Read each file — confirm actionable by L&D or relationship partner without modification.
6. **Integration:** `cd backend && python -m pytest tests/ -v` — confirm new routes don't break existing tests.

## What We're NOT Building

- No Harvey integration (Technology team owns vendor relationships)
- No KM unification engine (massive IT program with existing teams)
- No AFA pricing calculator (Pricing/LPM team owns pricing strategy — we provide the cost-impact data they need)
- No Advance integration contract (Advance has its own leadership)
- No changes to existing contract-review or matter-intake functions (already deployed)
