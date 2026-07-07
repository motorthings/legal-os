# Legal AI Operating System

A platform for building, deploying, and governing AI across the legal enterprise. Governance-first architecture. Every decision auditable, explainable, and traceable by design.

## The Three Problems This Solves

| Problem | Stat | What the OS Does |
|---------|------|------------------|
| **Shadow AI** — your people are already using AI without your knowledge or control | 69% of legal professionals use generative AI for work | Provides a safe, governed alternative that replaces the ChatGPT tab |
| **Fake Governance** — most firms have no AI policy, or a policy nobody reads | 43% of firms have no AI policy and no plans to create one | Governance is structural — Row-Level Security at the database, not a PDF |
| **Billable Hour Pressure** — clients know AI makes routine work cost zero | 85% of clients say firms should disclose AI use; 64% expect to depend less on outside counsel | Proves value with an audit trail, turns compliance into competitive advantage |

## The Architecture

Five layers. Each independent. Governance at the center.

```
Layer 4 — Organizational Model     ← Maps functions to practice groups, divisions, strategy
Layer 3 — Program Operations       ← Portfolio dashboard, enablement, discovery, engagement
Layer 2 — Legal AI Functions       ← Standalone apps. Each owns UI, workflow, data, governance contract
Layer 1 — Governance & Trust       ← Auditability, Explainability, Traceability. Structural, not policy.
Layer 0 — Knowledge Foundation     ← Unified KB, precedent libraries, clause libraries, search
```

**The three non-negotiable pillars:**

1. **Auditability** — Full prompt capture. Response + reasoning chain. Deterministic score replay. Structured JSONL logging. Immutable.
2. **Explainability** — Chain of reasoning visible to the reviewer. Classification decisions cite the specific clause or signal. No black boxes.
3. **Traceability** — Who, when, what, why. Every override logged. Every artifact exportable. The answer to "prove it" is one query away.

**The architectural principle:** Deterministic over LLM. The platform never trusts an LLM score directly. Every classification, risk score, and recommendation goes through a programmatic scoring layer. The LLM provides reasoning. The system provides judgment.

## What's Built

### Deployed

- **Matter Intake & Triage** — Two-stage pipeline (Router → Evaluator). 5 weighted dimensions. Full audit trail. Under 10 seconds.
- **Contract Review & Analysis** — 5 specialized agents. RAG-powered with 30+ legal standards. 360 contracts/hour. Production.
- **Employment Legal Agents** — Separation agreement generator (US, EMEA, AU). Legal metrics analysis. State report filing. RLS walls between employment and commercial.
- **Cowork Legal Plugin** — 9 skills for in-house legal teams. Playbook-driven contract review. NDA triage. Compliance checks. Risk assessment.

### Roadmap

- **Due Diligence Accelerator** — Bulk document review. Clause-level comparison. Deltas only to the reviewer.
- **Regulatory Change Monitor** — Monitors regulatory updates across jurisdictions. Maps changes to active matters.
- **KM & Precedent Intelligence** — "Have we done this before, and what did we argue?" — answered in seconds.
- **Client Value Reporting** — "Here's what AI saved this quarter" — with the audit trail to prove it.

## Repository Structure

```
legal-os/
├── README.md                   ← You are here
├── VISION.md                   ← Full platform vision (all 8 functions, present tense)
├── BUILD_PLAN.md               ← Concrete build plan for roadmap items
├── matter-intake/              ← Matter Intake & Triage (FastAPI + Next.js)
├── contract-review/            ← Contract Review & Analysis (FastAPI + Next.js + Celery)
├── plugins/                    ← Cowork Legal Plugin (9 Claude skills)
└── governance/                 ← Governance documentation + diagrams reference
```

## Links

- [Full Vision Document](VISION.md) — the complete platform described as it exists today
- [Build Plan](BUILD_PLAN.md) — concrete steps for the four roadmap functions
- [Governance Model](governance/README.md) — the governance architecture in detail
- [Visual Explainers](https://motorthings.github.io/diagrams/) — interactive diagrams of every component

---

Built by [Charlie Fuller](https://github.com/motorthings). Governance-first. Deterministic over LLM. The audit trail is the product.
