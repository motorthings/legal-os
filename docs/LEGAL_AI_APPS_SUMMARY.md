# Legal AI Portfolio — Apps & Functions

Cross-repo summary of every legal AI application and function built by Charlie Fuller. Use this as the map when working across the legal repos. Everything here is real, shipped, and (where noted) live in production.

**The one-paragraph pitch:** governed AI for legal work. Not the model, not the law library — the layer that makes AI tools deployable and defensible in a firm: every decision logged and provable, client data walled off, the attorney always in the loop. Built on the principle *deterministic over LLM* — the model reasons, the system judges. Every authority cited is verified real and still good law.

---

## The platform

### Legal AI OS — `legal-os/`
The flagship. A governance-first operating model for running AI inside law firms and corporate legal departments — "not a tool, not a chatbot, an operating model." One consolidated **FastAPI** backend (Fly.io), **Next.js** frontend (Vercel, `legal.sickofancy.ai`), **Supabase** Postgres + pgvector, DeepSeek default LLM with per-function provider overrides.

Every function follows one pipeline: **input → Router (classify) → Evaluator (reason) → Programmatic Scoring (judge) → Audit Trail (capture)**. Three non-negotiables: **auditability** (full prompt capture + immutable JSONL + deterministic score replay), **explainability** (visible chain of reasoning, dimension-level scores), **traceability** (who/when/why, every override logged — SOC 2 / ISO 42001 / EU AI Act / ABA 512 ready).

Ten functions:

1. **Matter Intake & Triage** — classifies practice area / urgency / jurisdiction, scores a matter across 5 weighted dimensions (classification 25, urgency 25, conflict 20, staffing 15, data integrity 15). Under 10 seconds. Also serves as the standalone demo app (below).
2. **Contract Review & Analysis** — 5 specialized agents (vendor, customer, employment, DPA, general), clause-by-clause against 30+ configurable standards, multi-dimensional risk scoring with red/yellow flag weighting and one-critical-flag auto-high. RAG over a firm knowledge base. ~360 contracts/hr.
3. **Employment Legal Agents** — Separation Agreement Generator (jurisdiction-specific US/EMEA/AU, severance calc + validation), Legal Metrics Analysis (outside-counsel spend via NL query), State Annual Report Filing. Walled behind RLS so employment data can't touch commercial legal.
4. **Due Diligence Accelerator** — bulk review: ingest hundreds of docs, classify, compare every clause vs deal-specific targets, group identical clauses, rank deviations by severity, surface only the deltas.
5. **Regulatory Change Monitor** — polls SEC/FTC/ICO/CNIL/EU Journal/state AGs, extracts structured changes, maps to active client matters by jurisdiction + practice area, flags deadlines, notifies owners.
6. **Legal Research** — Descrybe-powered: concept search, text search, law search, citation lookup, quote verification, case status/treatment, citing-case search, summaries, passages. Per-user OAuth.
7. **Cite Check** — validates a brief before filing against Descrybe: every citation resolved to a case_id with good-law treatment, every quote verified word-for-word. Catches fabricated cases, wrong reporter cites, overruled authority. Emits a findings report + annotated copy.
8. **KM & Precedent Intelligence** — semantic search over the firm's corpus ("have we done this before, and what did we argue?"), precedent matching, clause libraries that learn from reviewed contracts.
9. **Client Value Reporting** — per-client quarterly reports: matters processed, time saved, cost avoided, risk distribution, models used — every number backed by the audit trail.
10. **Firm Simulation** — Monte-Carlo digital twin of a firm's economics. 18-field intake, calibrated elasticity, budget-capped runs streamed live over SSE, partner-facing report on where value leaks and which levers move profit.

**Supporting platform:** matter enrichment (auto-runs research on a new matter), ROI framework, POC pipeline tracker, plus 7 governance/enablement assets (adoption playbook, AI-literacy FAQ, client-CISO FAQ, prompt-engineering-for-lawyers, workshop deck, RFP templates, client conversation deck).

**MCP server** (`mcp-server/`, self-contained, deterministic, no LLM/DB/API): `clause_risk_check`, `nda_triage`, `risk_matrix` (severity×likelihood). Deployed to Fly.io as `legalos-mcp`, streamable HTTP at `/mcp`.

**Cowork Legal Plugin** (`plugins/`) — 9 skills: review-contract, triage-nda, compliance-check, legal-risk-assessment, legal-response, meeting-briefing, vendor-check, signature-request, brief. Playbook-driven via `legal.local.md`.

---

## The standalone apps

### Matter Intake Evaluator — `matter-intake-evaluator/`
Standalone demo of function #1, built for **Perkins Coie**. Paste or upload a matter summary → practice-area classification, conflict check, risk assessment, staffing recommendation, each scored with reasoning. Two-stage LLM pipeline (router → evaluator) then **deterministic** weighted scoring (25/25/20/15/15) that deliberately does not trust the LLM's own numbers. Full audit trail reconstructs the decision chain. Next.js (Vercel) + FastAPI (Fly.io) + SQLite. 15 synthetic test fixtures against the live endpoint.

### Legal Contract Review — `legal-contract-review/`
The full production contract-analysis SaaS (origin of function #2). Router classifies each contract into 5 types; type-specific expert agent extracts terms, flags issues, computes weighted 0–100 risk score. Human-in-the-loop review workflow, RAG chat grounded in the contract text, triage + admin analytics dashboards, voice interview (ElevenLabs), team feedback loop on AI quality. Next.js (Vercel) + FastAPI + Celery (Railway) + Supabase/pgvector + Voyage AI. Contentful AI Solutions Partner demonstration piece.

---

## The simulations / research

### Law Firm Sim — `law-firm-sim/`
Digital twin of a single AmLaw-100 firm subjected to Monte Carlo + Bayesian analysis: given the firm's actual shape, which AI levers (pricing, comp, leverage, seams, latency) to pull and in what order to move PPP/margin/partnership. Headline finding: the **AI Profit Paradox** — under hourly billing AI is a net loss (compressed hours = lost revenue); under fixed-fee it's a net win. Deterministic mock engine searches cheap, one cost-capped real-DeepSeek run validates. Grown into a multi-firm web app: intake form, live SSE run progress, results viewer, cost caps, full audit export. Next.js + FastAPI + Supabase.

### Legal Sim — `legal-sim/`
Older sibling: the industry / legal-AI-company perspective. Two-track A/B simulation (organic discovery vs partnership/consensus) over 16 quarterly sprints. Headline: "adoption is not the problem; pricing and comp are" — discovery beats design on tacit seams. Deterministic research engine (mock LLM default), self-contained HTML results pages, adversarial-review workflow, evidence registry tying every parameter to a citable source. Not a shipped app.

---

## The case tool

### Atticus — `atticus/`
AI legal assistant for Charlie's pro se **JAMS employment-arbitration case against Contentful** (defamation, wrongful termination, pre-existing IP). Not a shipped app — a self-contained case-command knowledge base + filing kit encoded as a Claude Code agent (CLAUDE.md). Zero-file fast path answering 80%+ of questions, 7 ranked claims with evidence matrix, opponent modeling of Contentful/Littler, 18 procedural filing templates, Descrybe cite-check skill, exhibit registry with SHA-256 integrity checks, deadline tracking, settlement decision tree. Its Descrybe cite-check skill verifies every authority before filing — the strongest existing example of the verify-before-file guarantee.

---

## The skills / functions (shipped via `clode/`)

`clode/` is the config-sync repo that ships Charlie's legal AI *functions* into every Claude Code environment:

- **`cite-check` skill** — the flagship legal function. Verifies every authority in a filing against the Descrybe Legal Engine (existence, correct caption/reporter, treatment/good-law status, word-for-word quote accuracy). Catches fabricated/hallucinated cases. Same engine powers Cite Check in legal-os and Atticus.
- **`career-strategist` skill + agent** — career counselor / HR / negotiation rep (boundary: career, not strictly legal).
- **`prd` skill** — Socratic PRD generator (used to spec legal products).
- **`diagrams` skill** — publishes the `legal/` architecture pages to the diagrams repo.
- **`contract-review` project setup** — the Celery-based contract review app's dev commands.
- Plus cipher, transcript-analysis, glean-docs, fitness (non-legal).

---

## The portfolio / explainers — `diagrams/legal/`

The `diagrams/legal/` folder is the public, portfolio-facing explainer layer (GitHub Pages). It documents this same portfolio as interactive HTML: **legal-ai-os-overview**, **legal-ai-os-full-platform**, **legal-ai-os-ashurst-perkins-coie**, **legal-ai-maturity-model**, **legal-ai-governance**, **legal-descrybe-integration**, **legal-os-mcp-server**, **matter-intake-overview/pipeline**, **law-firm-sim**, **legal-project-registry**, plus project pages (separation-agreement, nda-triage, state-filing, legal-metrics, itfa, metrics). The index positions the whole body of work: *the brain (drafting tools), the library (the law), the rails (the governance layer — what I build)*. The boundary is explicit: the platform recommends, a licensed attorney decides.

Also documented here: the vendored **Anthropic claude-for-legal** skill library (13 practice packs, ~100 skills) that legal-os subsumes (`clode` / `claude-for-legal` checkout).

---

## Cross-cutting architecture

- **Deterministic over LLM** — the model reasons, a programmatic scoring layer judges. The LLM never decides alone.
- **Audit everywhere** — structured immutable JSONL, prompt + output capture, deterministic score replay, full chain-of-reasoning reconstruction.
- **Ethical walls via RLS** — client A vs client B, employment vs commercial legal, walled at the database.
- **Verify before file** — Descrybe-backed cite-checking across legal-os, Atticus, and the cite-check skill. The "no invented citations" guarantee.
- **Same engine, three scales** — legal-sim (research) → law-firm-sim (single firm) → legal-os functions (production).

## Where everything lives

| Repo | Host | Role |
|---|---|---|
| `legal-os/` | Fly.io + Vercel + Supabase | Flagship platform + MCP server + Cowork plugin |
| `legal-contract-review/` | Vercel + Railway + Supabase | Production contract-analysis SaaS |
| `matter-intake-evaluator/` | Vercel + Fly.io | Standalone intake demo (Perkins Coie) |
| `law-firm-sim/` | Supabase + FastAPI + Next.js | Firm digital-twin decision tool |
| `legal-sim/` | local | Research simulation |
| `atticus/` | local (Claude Code) | Pro se Contentful arbitration case |
| `clode/` | local | Ships skills/MCP/config into Claude Code |
| `claude-for-legal/` | Anthropic (vendored) | Anthropic skill library (subsumed) |
| `diagrams/legal/` | GitHub Pages | Public portfolio explainers |
