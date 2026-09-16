# Legal Work Summary — Charlie Fuller

A governed-AI engineering portfolio for the legal profession. Not the model, and not the law
library. The layer that makes AI tools deployable and defensible in a firm: every decision logged
and provable, client data walled off at the database, a licensed attorney always the final decider.

Two principles run through all of it, from a ten-function platform down to a single citation check:

1. **Deterministic over LLM.** The model reasons. A programmatic scoring layer judges. Weights,
   thresholds, and rules are never trusted to the model directly.
2. **Verify before file.** Every authority cited is confirmed real, correctly cited, and still good
   law before it ships. No invented citations, ever.

Everything listed here is real, shipped, and running (where noted). The write-ups are honest about
what each piece does and what it doesn't.

---

## 1 · Legal AI OS — the governed platform

**Repo:** `legal-os/` · **Stack:** FastAPI (Fly.io) · Next.js (Vercel) · Supabase Postgres + pgvector ·
DeepSeek default LLM with per-function provider overrides

The flagship. A governance-first operating model for running AI inside law firms and corporate legal
departments. Not a tool, not a chatbot. The operating model for how AI gets built, deployed, and
governed across an organization, held together by one non-negotiable contract: every AI decision is
**auditable, explainable, and traceable by design.**

Each function follows the same pipeline: input → Router (classify) → Evaluator (reason) → Programmatic
Scoring (judge) → Audit Trail (capture). Ten standalone functions share one governance layer, and each
exposes its own health, metrics, and evaluation targets so governance can verify compliance without
coupling to any function's internals. Ethical walls are enforced at the database layer (Row-Level
Security), not by policy document. The audit trail is the product: "prove it" is one query away.

The ten functions:

| Function | What it does |
|---|---|
| Matter Intake & Triage | Router→Evaluator pipeline; classifies practice area, urgency, jurisdiction; scores across 5 weighted dimensions. Under 10 seconds. |
| Contract Review & Analysis | 5 specialized agents (vendor, customer, employment, DPA, general), clause-by-clause against 30+ standards, weighted risk scoring. ~360 contracts/hr. |
| Employment Legal Agents | Separation-agreement generation (US/EMEA/AU), legal-metrics analysis, state annual-report filing. Walled behind RLS. |
| Due Diligence Accelerator | Bulk review of hundreds of documents; clause-level comparison against deal targets; surfaces only the deltas. |
| Regulatory Change Monitor | Polls SEC/FTC/ICO/CNIL/state AGs; maps structured changes to active matters by jurisdiction and practice area. |
| Legal Research | Descrybe-powered case law, statutes, citation intelligence: treatment, authority ranking, quote verification. |
| Cite Check | Validates a brief against Descrybe before filing: citations confirmed, quotes verified word-for-word, overruled authority caught. |
| KM & Precedent Intelligence | Semantic search across the firm corpus; clause libraries that learn from every reviewed contract. |
| Client Value Reporting | Per-client reports of matters processed, time saved, risk distribution; every number backed by the audit trail. |
| Firm Simulation | Monte-Carlo digital twin of the firm's own economics; budget-capped runs streamed live over SSE; partner-facing report. |

**Supporting platform:** matter enrichment, an ROI framework, a POC pipeline tracker, and seven
governance/enablement assets (adoption playbook, AI-literacy FAQ, client-CISO FAQ,
prompt-engineering-for-lawyers, workshop deck, RFP templates, client conversation deck).

**Governance contracts** (SOC 2 / ISO 42001 / EU AI Act / ABA 512 ready): auditability (full prompt
capture, immutable JSONL, deterministic score replay), explainability (visible chain of reasoning,
dimension-level scores), traceability (who/when/what/why, every override logged).

A self-contained **MCP server** (`mcp-server/`, no LLM/DB/API) exposes `clause_risk_check`,
`nda_triage`, `risk_matrix`, and `cite_check`, deployed to Fly.io as `legalos-mcp`. A **Cowork Legal
Plugin** (`plugins/`) ships 9 playbook-driven skills. Deep detail: `docs/LEGAL_AI_APPS_SUMMARY.md`.

---

## 2 · Fault-Line Radar — the forecasting engine

**Repo:** `legal-os/radar/` · **Canonical spec:** `docs/radar/radar-design.md` · **Evidence:**
`docs/radar/radar-market-inventory.md` · **Page:** `/radar`

The newest and most distinctive piece: a self-backtesting engine that forecasts where legal AI is
headed, so someone can decide where to build and govern next. It does not predict "the date." It
tracks **fault lines**, the places where a new AI capability rubs against an existing legal duty, and
measures how much pressure is building on each, weighted by who is doing the pushing.

A court ruling, a funding round, and a new model release are three different kinds of event. The
radar's job is to keep them straight.

**Eleven fault lines**, scored 0–10 on five separate meters each:

- **L1 capability** (can the AI do it yet), **L2 ruling** (will the law move), **L3 adoption** (is the
  fix becoming table stakes), **E enablement** (can a firm build it with what the market sells today),
  and **S software** (are vendors enabled to build the tool).

L1, S, and E are three layers of one supply stack: model → software → method → firm. Keeping them
separate is what stops "the model can do it" from being mistaken for "a vendor shipped it."

The lines span the real stress points: insurer gating, AI-use disclosure, documented verification,
client confidentiality, conflicting rules converging, autonomous agents reopening supervision/UPL, a
tool-certification standard emerging, competence as a governance duty, judge-prediction analytics
getting regulated, the billable hour cracking, and liability shifting to vendors.

**Authority over volume.** Every piece of evidence is tier-stamped at intake, and the tier decides the
weight, not how many people repeated it. A court ruling weighs 1.00, a bar opinion 0.80, an empirical
study 0.60, commentary 0.35, vendor marketing 0.008. Ten vendor posts cannot outweigh one ruling. The
feed holds 76 real, dated, 2023–26 evidence items across six streams (vendor capital and M&A, model
access, regulatory room, method/playbook, the docket of actual sanctions and referrals, and a
certification watch).

**Two-sided scoring.** Most meters only go up. The L2 ruling meter goes both ways: an item can argue
*against* a line, dragging pressure below the seed. A forecast that can only say "more pressure"
cannot notice when the rules reverse course.

**It grades itself.** A calibration layer replays the feed as it stood days before each ruling that
actually landed, and scores its own hit rate. Part A earns trust by being graded.

**The advisory seam — GOVERN vs DEPLOY.** The layer that turns the readouts into advice returns two
separate verdicts per fault line. GOVERN asks whether the control is required of the firm and whether
it can meet it, and economics never blocks a required control. DEPLOY asks whether this is the moment
to put AI on the work, gated by pricing and market enablement. Fixed-fee and hourly firms get opposite
DEPLOY answers: the **AI Profit Paradox**, applied at the fault-line level (hourly billing makes AI a
net loss, fixed-fee makes it a net win). Part B is advice, never a forecast. Part C, the firm
simulation, tests whether one specific firm's economics even let it act.

**Method that survives review.** A fact does not enter the feed because someone found it. It enters
because it survived. Three independent reviewers each try to break every claim; it stands only if two
of three cannot. Dates and amounts that cannot be verified are reported as "we found nothing," never
guessed. This is documented in `docs/radar/evidence-methodology.md` and
`docs/radar/build-method.md`, and it is what caught real mistakes: a court rule only one source
mentioned, a disqualification that was actually a reprimand, a two-vendor claim no source supported.

**Live in the app:** `/radar`, `/radar/advisory` (the GOVERN/DEPLOY seam), `/radar/kb` (the knowledge
base), and `/radar/reference` (the scroll-reveal master reference). The engine regenerates its page
weekly via CI and stays deterministic: given the same feed and date, it replays to the same score.

---

## 3 · Production apps

The platform's functions also ship as focused, standalone products. These are the origin builds some
functions rolled up from.

### Legal Contract Review — `legal-contract-review/`
The full production contract-analysis SaaS (origin of the platform's function #2). Router classifies
each contract into 5 types; a type-specific expert agent extracts terms, flags issues, and computes a
weighted 0–100 risk score. Human-in-the-loop review, RAG chat grounded in the contract text, triage
and admin dashboards, a voice interview, and a team feedback loop on AI quality. Next.js + FastAPI +
Celery + Supabase/pgvector + Voyage AI.

### Matter Intake Evaluator — `matter-intake-evaluator/`
Standalone demo of the intake function, built for a named AmLaw-50 firm. Paste or upload a matter
summary → practice-area classification, conflict check, risk assessment, and a staffing
recommendation, each scored with reasoning. A two-stage LLM pipeline (router → evaluator) then
**deterministic** weighted scoring (25/25/20/15/15) that deliberately does not trust the LLM's own
numbers. Full audit trail reconstructs the decision chain. Next.js (Vercel) + FastAPI (Fly.io).

### Legal AI MCP server — `legal-os/mcp-server/`
Self-contained, deterministic, no LLM/DB/API. Tools: `clause_risk_check`, `nda_triage`, `risk_matrix`,
`cite_check`. Deployed to Fly.io as `legalos-mcp`, streamable HTTP at `/mcp`.

### Cowork Legal Plugin — `legal-os/plugins/`
Nine skills for in-house legal teams: review-contract, triage-nda, compliance-check,
legal-risk-assessment, legal-response, meeting-briefing, vendor-check, signature-request, brief.
Playbook-driven via `legal.local.md`.

---

## 4 · Simulations and research

The strategic layer: simulations that model AI's economics inside law before anyone builds anything.

### Law Firm Sim — `law-firm-sim/`
A Monte-Carlo digital twin of a single AmLaw-100 firm. Given the firm's actual shape, it works out
which combination of AI levers (pricing, comp, leverage, seams, latency) moves PPP/margin/partnership,
and in what order. Grown into a multi-firm web app with live SSE run progress and full audit export.

### Legal Sim — `legal-sim/`
The industry perspective: a two-track A/B simulation (organic discovery vs planned design) over 16
quarters, plus a standalone **AI Profit Paradox pricing model and calculator**. Headline finding:
adoption is not the problem, pricing and comp are.

These two produced the finding the whole portfolio returns to: under hourly billing, AI is a net loss
(hours saved are hours not charged). Under fixed-fee pricing, the same AI is a net win. Which is why
the radar's DEPLOY verdict, and the firm sim, both turn on how a firm bills.

---

## 5 · Skills and functions shipped into Claude Code

`clode/` is the config-sync home for the skills that run across every environment. The legal ones:

- **`cite-check`** — the flagship legal function. Verifies every authority in a filing against the
  Descrybe Legal Engine: existence, correct caption and reporter, treatment/good-law status, and
  word-for-word quote accuracy. Catches fabricated or hallucinated cases, wrong reporter cites, and
  overruled authority. The same engine powers Cite Check in Legal AI OS and the case tool below.
- **`career-strategist`** — career counselor and negotiation rep (boundary: career, not law).
- **`prd`** — Socratic PRD generator, used to spec legal products.
- **`diagrams`** — publishes the legal architecture pages to the diagrams repo.

The vendored **Anthropic `claude-for-legal`** skill library (13 practice packs) is a separate,
upstream, third-party reference that Legal AI OS subsumes, not original work.

---

## 6 · Portfolio explainers — `diagrams/legal/`

The public, GitHub-Pages-facing layer that documents this same body of work as interactive HTML.
Covered here: the **fault-line-radar** cluster (overview, app, how-it-works, knowledge base, build
log, streams, master reference), **cite-check / Descrybe** integration and case study, the
**seam-finder** and the **AI Profit Paradox calculator**, the ten functions and their pipelines, the
MCP server, the governance and maturity models, plus project pages. The index positions the whole
portfolio: the drafting tools, the law library, and the governance rails, which is the layer the work
actually builds. The boundary is explicit everywhere: the platform recommends, a licensed attorney
decides.

---

## 7 · The verify-before-file guarantee

The strongest proof in the portfolio is a discipline, applied where it matters. The same
cite-check/Descrybe engine that powers Cite Check in the platform was run over a **real, contested
filing lifecycle, end to end, before a single document went out**: every authority resolved to a case
ID with good-law treatment, every quote verified word-for-word, every exhibit checksummed, an
exhibit registry with SHA-256 integrity, and a verification ledger. It is the working demonstration
that the "no invented citations" guarantee holds on actual adversarial work, not just on a demo.

It is documented as the cite-check case study in `diagrams/legal/` and embodied in a Claude Code
case-command knowledge base with a Descrybe verify gate, integrity checks, and deadline tracking.

---

## 8 · Education and professional engagement

**MIT Computational Law — the law.MIT.edu 2026 Summer Intensive** (August 20, 2026), hosted by Dazza
Greenwood. A hands-on, project-based session at the intersection of AI agents and law, where
participants brought their own agents (Claude Code, Codex) and worked in teams on participant-voted
topics in a shared multi-agent workspace: verifying agent-produced legal work before it is relied on,
what a "the human authorized this" record must contain to survive scrutiny, authority boundaries,
AI-native professional-services economics, and public-sector AI procurement. MIT keynote by Sandy
Pentland. Follow-up: **HOPE Lab** (Hands-On Projects and Experimentation), September 16, 2026.

This is the same discipline the Fault-Line Radar and the cite-check work sit inside: authority
boundaries, verification, and agent-produced legal work under human control. *[Note: add which team
topic or project you worked if you want this section specific to you.]*

---

## Cross-cutting architecture

- **Deterministic over LLM.** The model reasons; a programmatic scoring layer judges. Weights and
  thresholds are never trusted to the model.
- **Audit everywhere.** Structured immutable JSONL, prompt and output capture, deterministic score
  replay, full chain-of-reasoning reconstruction.
- **Ethical walls via RLS.** Client A vs client B, employment vs commercial legal, walled at the
  database.
- **Verify before file.** Descrybe-backed cite-checking across the platform, the case tool, and the
  `cite-check` skill. The no-invented-citations guarantee.
- **Same engine, three scales.** Legal sim (industry research) → law firm sim (one firm) → Legal AI OS
  functions (production). The radar's advisory layer and the firm sim connect to the same economics.

## Where everything lives

| Repo | Host | Role |
|---|---|---|
| `legal-os/` | Fly.io + Vercel + Supabase | Flagship platform + Fault-Line Radar + MCP server + Cowork plugin |
| `legal-contract-review/` | Vercel + Railway + Supabase | Production contract-analysis SaaS |
| `matter-intake-evaluator/` | Vercel + Fly.io | Standalone intake demo (AmLaw-50 firm) |
| `law-firm-sim/` | Supabase + FastAPI + Next.js | Firm digital-twin decision tool |
| `legal-sim/` | local | Industry research simulation + AI Profit Paradox model |
| `clode/` | local | Ships the legal skills into Claude Code |
| `claude-for-legal/` | Anthropic (vendored) | Upstream reference library (not original work) |
| `diagrams/legal/` | GitHub Pages | Public portfolio explainers + cite-check case study |

---

*This is a portfolio index of engineering work. Nothing here is legal advice. Every artifact keeps the
boundary explicit: the system recommends, a licensed attorney decides.*
