# legal-os — Legal AI Operating System

A platform for building, deploying, and governing AI across the legal enterprise. Governance-first: every decision auditable, explainable, traceable by design.

## The three problems it solves
- **Shadow AI** — safe, governed alternative that replaces the ChatGPT tab.
- **Fake governance** — governance is structural (RLS at the database), not a PDF nobody reads.
- **Billable-hour pressure** — proves value with an audit trail; compliance becomes competitive advantage.

## Architecture — five layers, governance at the center
```
Layer 4 — Organizational Model      ← maps functions to practice groups, divisions, strategy
Layer 3 — Program Operations        ← portfolio dashboard, enablement, discovery, engagement
Layer 2 — Legal AI Functions        ← standalone apps; each owns UI, workflow, data, governance contract
Layer 1 — Governance & Trust        ← auditability, explainability, traceability (structural, not policy)
Layer 0 — Knowledge Foundation      ← unified KB, precedent/clause libraries, search
```

## Three non-negotiable pillars
1. **Auditability** — full prompt capture, response + reasoning chain, deterministic score replay, structured JSONL logging, immutable.
2. **Explainability** — chain of reasoning visible to reviewers; classification decisions cite the specific clause/signal.
3. **Traceability** — who/when/what/why; every override logged; every artifact exportable.

## Layout
- `backend/` — FastAPI services
- `frontend/` — Next.js app
- `supabase/` — schema, RLS (the governance enforcement point)
- `mcp-server/` — MCP server
- `matter-intake/` `contract-review/` — standalone legal-AI functions
- `governance/` `enablement/` `plugins/` — governance contracts, enablement, plugins
- `docs/` `scripts/` `results/` `screenshots/`

## Notes
- Recent work (2026-08-23): legal-engineer verification + governance rigor.
- Build plans: `BUILD_PLAN.md`, `BUILD_PLAN_PROGRAM_OPS.md`, `BUILD_PLAN_HARVEY_MONITORING.md`.
- `VISION.md` / `personas.md` for product intent and personas. `Makefile` for common tasks.
