# Legal AI OS: Governed AI Operating System for the Legal Enterprise

## What Legal AI OS Does

Legal AI OS is a governed platform for building, deploying, and measuring AI across a law firm or corporate legal department. It is not a chatbot and not a single tool. It is the operating model for how AI gets built, deployed, and governed across the organization — ten standalone legal-AI functions running on a shared knowledge foundation and a governance layer that every function plugs into.

The whole thing is held together by a non-negotiable contract: **every AI decision is auditable, explainable, and traceable by design.** Each function follows the same pipeline — *input → Router (classify) → Evaluator (reason) → Programmatic Scoring (judge) → Audit Trail (capture)*. The LLM provides the reasoning; the system provides the judgment. Never the reverse.

This is the answer to the structural problem the legal market is running into. Shadow AI is already inside the firm (69% of legal professionals use generative AI for work, most of it unapproved). Most firms have no governance or fake governance (a PDF nobody read after week one). The billable-hour model is under structural pressure. Legal AI OS makes governance the architecture, not the afterthought — so the firm gets governed AI instead of a dozen ChatGPT tabs, and can prove it with an audit trail.

---

## Who It's For

Three kinds of user, served through three personas the app exposes directly:

- **Practicing attorneys** — doing billable work under hours pressure. They land on practice areas (Employment, Corporate, Litigation, Regulatory) with the shared tools (research, cite check, contract review, intake, KM) scoped behind them.
- **Firm leaders / legal ops** — the GC, CKO, or managing partner. They land on "run the firm": adoption and pipeline metrics up front, strategy and proof (governance, simulation, value reporting) behind.
- **The evaluator** — a recruiter, peer, or prospective client being shown the platform. They get the tour persona: a guided path through the whole thing, one beat at a time.

The buyer and the user are different people, and the app keeps them separate rather than cramming one flat menu for all three.

---

## The Ten Functions

Each function is a standalone application — its own UI, workflow, and data — exposing a governance contract (health, metrics, evaluation targets) the governance layer polls independently. Replace one without touching the others.

| function | what it does |
|---|---|
| **Matter Intake & Triage** | Two-stage Router→Evaluator pipeline that classifies practice area, urgency, and jurisdiction, then scores across five weighted dimensions (classification 25%, urgency/risk 25%, conflict check 20%, staffing 15%, data integrity 15%). Under 10 seconds. The highest-leverage entry point — every new matter touches it. |
| **Contract Review & Analysis** | Five specialized agents (vendor, customer, employment, DPA, general) doing clause-by-clause analysis against 30+ configurable standards. Multi-dimensional risk scoring with red-flag weighting and one-critical-flag auto-high. |
| **Employment Legal Agents** | Separation-agreement generation (US/EMEA/Australia), outside-counsel spend metrics, and state annual-report filing. Walled behind Row-Level Security so employment data can't touch commercial legal. |
| **Due Diligence Accelerator** | Bulk document review at scale — ingests hundreds of documents, classifies each, compares every clause against deal-specific target standards, and surfaces only the deviations. The highest-volume automation target for corporate/finance. |
| **Regulatory Change Monitor** | Polls regulatory sources (SEC, FTC, ICO, CNIL, state AGs, enforcement actions), extracts structured changes, and maps each to active client matters by jurisdiction and practice area. |
| **Legal Research** | Descrybe-powered case law, statutes, and citation intelligence — good-law treatment, authority ranking, and quote verification. |
| **Cite Check** | Validates a brief against Descrybe before filing — citations confirmed, quotes verified word-for-word. Catches fabricated cases, wrong reporter cites, and overruled authority. |
| **KM & Precedent Intelligence** | Semantic search across the firm's entire corpus — briefs, memoranda, deal summaries, reviewed contracts. "Have we done this before, and what did we argue?" answered in seconds. Clause libraries that learn from every reviewed contract. |
| **Client Value Reporting** | Per-client reports demonstrating measurable AI value — matters processed, time saved, risk distribution, models used. Every number backed by the audit trail. |
| **Firm Simulation** | A Monte-Carlo digital twin of the firm's own economics (rolled in from the `law-firm-sim` build). Operators fill an 18-field intake, calibrate elasticity coefficients, set objective weights and guardrails, and run budget-capped simulations streamed live over SSE. Returns a partner-facing report on where value leaks and which levers move profit. |

---

## The Governance Layer — Three Non-Negotiable Pillars

Before any function runs, three things are true. They are the architecture.

**Auditability.** Every evaluation captures the full prompt, the full response, the model version, the rubric version, and the scoring formula. When a partner questions a classification six months later — or a client's outside-counsel-guidelines audit asks for proof — the full decision context is retrievable. Immutable JSONL logging.

**Explainability.** Every output includes its chain of reasoning, visible to the reviewer. Classification decisions cite the specific clause, signal, or pattern that drove the result. Risk scores decompose into their weighted dimensions. The attorney understands *why* before they decide *whether*.

**Traceability.** Who ran the evaluation, when, which model version, which rubric version, what the score was, whether a human overrode it and why. Full chain of custody from upload through review. Compliance-ready artifacts on demand — SOC 2, ISO 42001, EU AI Act, ABA 512, client audit requests.

Underneath the pillars: **ethical walls enforced at the database layer** (Client A's data cannot touch Client B's models via Row-Level Security), **human-in-the-loop gating** (AI recommends, humans decide, with mandatory escalation below confidence thresholds), and **model governance** with hard veto rules.

---

## The Knowledge Foundation

Every function reasons over a shared knowledge base inside the trust boundary — precedent libraries, clause libraries, and search infrastructure. Without it, every function starts from zero; with it, institutional memory compounds.

- **Embeddings** — Voyage AI (`voyage-3-large`, 1024 dimensions).
- **Vector search** — pgvector cosine similarity in Postgres, with text-search fallback when embeddings aren't available.
- **RAG** — chunked document ingestion (800-token chunks, 200-token overlap), embedding generation, similarity retrieval (max 20 chunks, 0.75 threshold), and document-to-document similarity.

---

## The Persona Model

One shell, one page set, three framings — resolved through a persona selector at the top of the left menu:

- **Attorney** — practice areas front, shared tools behind.
- **Firm leader** — "run it" (ops) front, "steer & prove" (strategy) behind.
- **Tour leader** — the whole platform as a guided path, the showpiece made first-class.

The nav is organized around *what you're doing right now*, not around the app's internal modules. This is the fix for the "unfocused menu" problem: an area of practice (Employment) and a workflow verb (Intake) don't belong in the same flat list.

---

## Architecture

- **Backend** — Python FastAPI on Fly.io (`legal-os-api.fly.dev`). Asyncpg for pgvector and raw SQL, Celery for background work.
- **Frontend** — Next.js 16 on Vercel (`legal.sickofancy.ai`). Server components for guides, client components for the live simulation stream.
- **Database** — Supabase (Postgres + pgvector). Service-role pool for writes; Row-Level Security for ethical walls.
- **Legal research** — Descrybe Legal Engine (OAuth + MCP, no static API key).
- **Embeddings** — Voyage AI.
- **LLM** — DeepSeek by default, with per-function provider overrides (Anthropic/OpenAI); the simulation's deterministic mock is the zero-cost stand-in.

---

## Tech Stack

| layer | technology |
|---|---|
| backend | Python 3, FastAPI, asyncpg, Celery |
| frontend | Next.js 16, React 19, Tailwind, Recharts, react-markdown |
| database | Supabase (Postgres + pgvector) |
| embeddings | Voyage AI (`voyage-3-large`) |
| legal research | Descrybe Legal Engine (OAuth + MCP) |
| LLM | DeepSeek (default), Anthropic, OpenAI, deterministic mock |
| hosting | Fly.io (backend), Vercel (frontend) |
| logging | structured JSONL (immutable audit trail) |
| testing | pytest (backend), Playwright (frontend e2e) |

---

## Key Architectural Decisions

- **The LLM reasons; the system judges.** Every function runs programmatic scoring over the LLM's reasoning — weights, thresholds, and rules are never trusted to the model directly.
- **One shared contract per function.** Each function exposes health, metrics, and evaluation targets, so the governance layer verifies compliance without coupling to any function's implementation.
- **Governance is the database, not a PDF.** Ethical walls, escalation thresholds, and model vetoes live in Row-Level Security and code, not in a policy document.
- **The audit trail is the product.** Full prompt capture and immutable JSONL logging make "prove it" a one-query answer — the differentiator that turns the disclosure obligation (85% of clients expect AI disclosure) into a retention asset.
- **Firm Simulation is a digital twin, not a rankings list.** The rolled-in sim models one firm's economics under interventions, returning a recommendation with a confidence interval and a causal story, not a brute-forced leaderboard.
- **Three personas, one page set.** Role-based framings over shared routes keep the working surfaces focused without duplicating the app.

---

## Summary

Legal AI OS turns "AI is coming for legal" from a governance panic into a governed, measurable operating model. Ten functions — from intake to research to a firm's own Monte-Carlo digital twin — run on a shared Voyage/pgvector knowledge foundation and a governance layer that captures every decision with its reasoning and its score.

The defensible core is the pipeline itself: the LLM reasons, the system judges, and the audit trail records everything. That's what separates a platform from a pile of demos. The functions are individually familiar (contract review, research, intake are crowded markets); what's unique is that they're *governed* — every output explainable, every decision replayable, every override logged. The audit trail is the product.
