# Build Plan — Roadmap Functions

Concrete build plans for the four roadmap functions. Each plan identifies what existing infrastructure to reuse, what new infrastructure is needed, the minimum viable version, and estimated effort.

## Shared Architecture

All four functions follow the same pattern established by the built functions:

```
Input → Router (classify) → Evaluator (reason) → Programmatic Scoring (judge) → Audit Trail (capture)
```

Reusable infrastructure across all four:

| Component | Source | What It Provides |
|-----------|--------|------------------|
| Two-stage LLM pipeline | `matter-intake/backend/evaluator.py` | Router + Evaluator + programmatic scoring pattern |
| Pydantic models | `matter-intake/backend/models.py` | Strict response validation, dimension scoring |
| API structure | `matter-intake/backend/api/routes.py` | CRUD endpoints, audit trail endpoint, search/filter/pagination |
| Audit trail | `matter-intake/backend/database.py` | Full prompt I/O capture, rubric snapshots, score replay |
| Provider abstraction | `matter-intake/backend/evaluator.py::_llm_call` | Unified Anthropic/OpenAI-compatible interface |
| Prompt architecture | `matter-intake/backend/prompts/` | Flat-file prompt loading, router + evaluator pattern |
| Celery task queue | `contract-review/backend/celery_app.py` | 3 queues (default/urgent/batch), rate limiting, retry with backoff |
| Contract processing | `contract-review/backend/contract_processor.py` | Full pipeline: fetch → download → extract → router → analyze → score → store |
| Legal standards CRUD | `contract-review/backend/api/routes/legal_standards.py` | Configurable standards with categories, severity, acceptable values |
| RAG pipeline | `contract-review/backend/document_processor.py` | Chunking (800/200), Voyage AI embeddings, pgvector search, Redis cache |
| Performance telemetry | `contract-review/backend/contract_processor.py::PerformanceTimer` | Per-stage timing with metadata |
| Instruction versioning | `contract-review/backend/instruction_versioning.py` | Semver instruction tracking, standards version tracking |

---

## 1. Due Diligence Accelerator

**What it does:** Ingests hundreds of documents for a deal, classifies each, compares every clause against deal-specific target standards, surfaces only deviations. Groups identical clauses. Ranks deviations by severity and materiality.

**Existing code to reuse:**
- `contract_processor.py` — the full contract analysis pipeline (download → extract → router → analyze → score)
- `celery_app.py` — batch task queue with rate limiting, exactly what bulk processing needs
- `legal_standards.py` — the standards CRUD already supports configurable per-category acceptable values and severity
- `calculate_risk_score` — programmatic scoring with red/yellow flag weights
- `document_processor.py` — RAG pipeline for finding similar clauses across the deal corpus

**New infrastructure to build:**

| Component | Description | Effort |
|-----------|-------------|--------|
| `dd_projects` table | Groups documents into a deal: `deal_id`, `deal_name`, `client_id`, `target_standards_id`, `status`, `created_at` | S |
| `dd_documents` table | Individual documents in a deal: `document_id`, `deal_id`, `status`, `deviation_count`, `review_status` | S |
| `dd_deviations` table | Detected deviations: `document_id`, `clause_type`, `target_standard`, `current_text`, `deviation_severity`, `reviewer_notes` | S |
| Target standards per deal | Extend the legal standards system to support deal-specific standard sets — a deal gets its own copy of standards with deal-specific acceptable values | M |
| Delta aggregation endpoint | `POST /api/due-diligence/{deal_id}/analyze` — triggers batch analysis, `GET /api/due-diligence/{deal_id}/report` — returns consolidated deviation report | M |
| Clause grouping | Identifies identical clauses across documents (via embedding similarity + text hash) so the reviewer only sees each unique deviation once | M |
| Bulk upload UI | Drag-and-drop N documents, define target standards, trigger batch analysis, view consolidated report with severity filtering | L |

**MVP scope:**
- Upload N documents into a deal
- Run the existing contract analysis pipeline against each one (reuse `process_contract_task` in batch mode)
- Compare each clause against deal-specific target standards
- Generate a consolidated deviation report showing only flagged clauses, grouped by clause type
- Severity ranking: Critical → High → Medium → Info

**Estimated total effort:** Medium (2-3 weeks for MVP)

---

## 2. Regulatory Change Monitor

**What it does:** Polls regulatory sources across jurisdictions, extracts structured changes, maps them to active client matters by jurisdiction and practice area, notifies responsible teams, and tracks compliance deadlines.

**Existing code to reuse:**
- `legal_standards.py` — the standards CRUD can extend to track regulatory sources and their current versions
- `instruction_versioning.py` — regulation versioning follows the same pattern as instruction versioning
- `compliance-check/SKILL.md` — already defines what to monitor, monitoring approach, and escalation criteria
- APScheduler pattern from `services/sync_scheduler.py` — background job scheduling for periodic source polling

**New infrastructure to build:**

| Component | Description | Effort |
|-----------|-------------|--------|
| `regulatory_sources` table | Sources to monitor: `source_id`, `name`, `url`, `jurisdiction`, `agency`, `poll_frequency`, `last_polled`, `status` | S |
| `regulatory_updates` table | Extracted changes: `update_id`, `source_id`, `regulation_name`, `jurisdiction`, `change_type`, `effective_date`, `summary`, `raw_text`, `affected_industries` | S |
| `matter_regulatory_flags` table | Matter-impact mapping: `matter_id`, `update_id`, `impact_severity`, `deadline`, `status`, `assigned_to` | S |
| Source polling task | APScheduler task that fetches each source on its schedule, runs new text through a Claude extraction call (`extract_regulatory_changes`), diffs against last seen state | M |
| Change extraction prompt | Claude system prompt that takes raw regulatory text and returns structured JSON: `{regulation_name, jurisdiction, change_type, effective_date, summary, affected_industries, action_required}` | S |
| Matter matching engine | Matches each regulatory update to active matters by jurisdiction + practice area + industry. Uses the existing matter data model from matter-intake | M |
| Notification system | Slack/email/webhook notification when a matched change is detected. Configurable per practice group. | S |
| Regulatory dashboard | View of active regulatory changes, mapped matters, approaching deadlines, jurisdiction filters | M |

**MVP scope:**
- Seed 5-10 key regulatory sources (SEC, FTC, ICO, EU Official Journal, key state AGs)
- APScheduler polls each source daily
- Claude extracts structured changes from new publications
- Match changes to active matters by jurisdiction + practice area
- Slack notification to responsible partner when a match is found
- Simple dashboard showing active changes and affected matters

**Estimated total effort:** Medium (2-3 weeks for MVP)

---

## 3. KM & Precedent Intelligence

**What it does:** Semantic search across the firm's entire knowledge base. "Have we done this before, and what did we argue?" — answered with citations. Clause libraries that learn from every reviewed contract.

**Existing code to reuse:**
- `document_processor.py` — the full RAG pipeline: text extraction, chunking, Voyage embeddings, pgvector HNSW search, Redis cache, adaptive query types
- `process_conversation_to_kb` — already indexes AI conversations as knowledge; same pattern extends to briefs, memos, deal summaries
- `search_similar_chunks` — pgvector semantic search with client-level data isolation
- `legal_standards.py` — clause library = legal standards with version history + usage tracking

**New infrastructure to build:**

| Component | Description | Effort |
|-----------|-------------|--------|
| `kb_sources` table | Knowledge base entries: `source_id`, `document_type` (brief, memo, deal_summary, contract, research_note, email), `practice_area`, `author`, `date`, `matter_id`, `client_id` | S |
| `kb_collections` table | Grouping concept: `collection_id`, `name`, `description`, `practice_area`, `matter_id` — e.g., "Q3 2026 M&A Due Diligence" | S |
| Document ingestion pipeline | Extends the existing `process_document_to_kb` to handle more formats (email via MIME, DMS exports, OneNote/Confluence). Same chunking → embedding → pgvector pattern | M |
| Precedent search endpoint | `POST /api/kb/search` — semantic search with practice area, document type, date range, and client filters. Returns matching chunks + source citation + "how this was used" summary | M |
| "How used" enrichment | When a document is referenced in an analysis or decision, that context is stored as a backlink — so precedent search shows not just "here's the document" but "here's how we used it" | M |
| Clause library learning | Each analyzed contract automatically enriches the clause library — extracted clauses with their classification, risk flags, and negotiation outcomes become searchable standards | M |
| Query refinement | Claude-powered query rewriting: "can we terminate for convenience" → expands to include "termination for convenience clause," "T4C," "early termination right," jurisdiction-specific variants | S |
| KM search UI | Natural-language search interface showing results grouped by document type with source citations, dates, and relevance scores | L |

**MVP scope:**
- Index all previously reviewed contracts (already processed through contract-review pipeline)
- Add a "Knowledge Base" upload endpoint that ingests any document into the vector index with metadata
- Semantic search endpoint with practice area and document type filters
- Results include: matching text excerpt, source document name, date, practice area, relevance score
- Start with contracts only, expand to briefs and memos in phase 2

**Estimated total effort:** Large (4-6 weeks for MVP, ongoing for full document corpus ingestion)

---

## 4. Client Value Reporting

**What it does:** Generates client-facing reports demonstrating measurable AI value — total matters processed, time saved, risk distribution, models used, governance documentation. Every number backed by the audit trail.

**Existing code to reuse:**
- Audit trail infrastructure from `matter-intake/backend/database.py` — full evaluation capture with processing time, model version, rubric version
- `PerformanceTimer` from `contract_processor.py` — per-stage timing with metadata
- KPI routes from `contract-review/backend/api/routes/kpis.py` — existing aggregation patterns
- `contract_analysis` table — stores risk scores, red flags, yellow flags, processing time per contract

**New infrastructure to build:**

| Component | Description | Effort |
|-----------|-------------|--------|
| `client_value_reports` table | Report records: `report_id`, `client_id`, `period_start`, `period_end`, `total_evaluations`, `total_matters`, `total_processing_time_ms`, `total_tokens_used`, `estimated_hours_saved`, `risk_distribution` (JSON), `generated_at` | S |
| Time-saved baseline config | Configurable multipliers per function type: e.g., matter intake evaluation = 30min manual equivalent, contract review = 2hr manual equivalent. Stored as settings in the existing settings KV store | S |
| Report aggregation engine | Queries across all function databases (matter-intake evaluations, contract-review analyses) for a given client + period. Aggregates: count, processing time, tokens, risk distribution. Applies time-saved multipliers | M |
| Report generation endpoint | `POST /api/reports/generate` with `{client_id, period_start, period_end}` → generates and stores a report. `GET /api/reports/{report_id}` → returns the full report. `GET /api/reports?client_id=X` → list all reports for a client | M |
| PDF export | Markdown → PDF pipeline (or HTML → PDF via Puppeteer/Playwright) with firm branding. Report includes: executive summary, metrics overview, function-by-function breakdown, governance documentation, audit trail sample | M |
| Governance documentation pack | Auto-generated section for each report: model governance summary, ABA 512 compliance statement, data privacy architecture, confidentiality architecture. Pulls from governance layer health endpoints | S |
| Client-facing dashboard | Optional: a client-accessible view showing their firm's metrics in real time, with governance documentation always available | L |

**MVP scope:**
- Per-client quarterly report aggregation
- Report includes: total matters processed, average processing time, estimated hours saved (configurable baseline), risk distribution, models used, governance compliance statement
- Export as styled markdown (→ PDF conversion as phase 2)
- Manual trigger via API endpoint (scheduled automation as phase 2)

**Estimated total effort:** Medium (2-3 weeks for MVP, +1-2 weeks for PDF export and scheduling)

---

## Build Order

Recommended sequence based on dependency chains and value delivery:

1. **Due Diligence Accelerator** — Highest reuse of existing infrastructure. The contract-review pipeline is already 80% of what's needed. Quickest path to a working MVP.
2. **Client Value Reporting** — Depends on data from matter-intake and contract-review (already running). Pure aggregation + reporting layer. No new AI pipeline needed.
3. **Regulatory Change Monitor** — Independent of other roadmap items. Can be built in parallel with #2. New external data dependency (regulatory sources).
4. **KM & Precedent Intelligence** — Largest scope. Depends on having a corpus of reviewed documents to index (which #1 will generate). Best built last, after the other functions have populated the knowledge base.

---

## Governance for Roadmap Functions

Every new function must implement the governance contract pattern before it ships:

1. **Health endpoint** — `GET /api/{function}/health` → `{status, uptime, last_error}`
2. **Metrics endpoint** — `GET /api/{function}/metrics` → `{adoption_rate, processing_volume, avg_response_time, accuracy, flag_rate}`
3. **Evaluation targets** — `GET /api/{function}/targets` → `{standards, current_scores, drift_status}`

No function ships without audit trail capture. The pattern from `matter-intake/backend/database.py::get_audit_trail()` is the template — full prompt I/O, rubric snapshot, score replay.

Confidentiality architecture applies to every function: Row-Level Security at the database layer, client data isolation, enterprise LLM agreements (no training, no retention, no cross-client leakage).
