# Merge Plan: claude-for-legal → legal-os

**Status:** vendoring complete, sync tooling scaffolded
**Date:** 2026-08-19
**Upstream:** [anthropics/claude-for-legal](https://github.com/anthropics/claude-for-legal)
**Vendored at:** `vendor/claude-for-legal` (pinned `4a6c6518`)

## The principle

**Vendor Anthropic's content. Keep legal-os's runtime.**

`claude-for-legal` is a library of Claude skills, plugins, and managed-agent
cookbooks — reasoning content with no data layer. `legal-os` is a deployable,
governed platform — FastAPI + Next.js + Supabase (RLS), deterministic scoring,
and an immutable audit trail. Neither replaces the other. The merge lets
Anthropic's reasoning ride legal-os's governance, with the content updating
like a dependency instead of a copy-paste.

## What merges, what doesn't

| Concern | Home | Why |
|---|---|---|
| Skill/plugin content, checklists, risk flags, escalation thresholds | `vendor/claude-for-legal` (upstream) | This is Anthropic's surface and updates constantly |
| RLS ethical walls, deterministic score replay, JSONL audit, model governance | `legal-os` backend | Anthropic structurally cannot supply these — no data layer |
| Simulation engine, program ops, enablement, org model | `legal-os` | Uniquely ours, no upstream counterpart |

## Sync mechanism: git subtree

`claude-for-legal` is vendored under `vendor/claude-for-legal` via
`git subtree` (squashed history). Chosen over submodule because we expect to
customize the vendored skills, and subtree merges instead of overwriting.

- **Remote:** `upstream-legal` → `https://github.com/anthropics/claude-for-legal.git`
- **Prefix:** `vendor/claude-for-legal`
- **Pin file:** `vendor/claude-for-legal.pin` — records the upstream commit we last validated against
- **Tool:** `scripts/sync-upstream.sh` — fetch, subtree pull, re-pin, commit (no push)

### Manual update

```bash
./scripts/sync-upstream.sh            # pull latest main, pin, commit
./scripts/sync-upstream.sh --dry-run  # fetch + report only
```

### Automating updates (future)

Add a GitHub Action that runs `sync-upstream.sh` weekly and opens a PR. This
mirrors the existing Supabase keepalive Action. Surfacing updates as PRs —
rather than auto-merging — keeps a human in the loop for content that feeds
legal decisions.

## Adapter layer (where the merge does real work)

Syncing yields a folder of `.md` skill files. That is not the product. The
platform wins by *executing* governed, so the merge needs an adapter that maps
upstream skill content into the runtime. This layer is the next build target
and is **not yet implemented**.

1. **Skill → evaluator mapping.** Upstream `SKILL.md` files carry the domain
   logic (criteria, checklists, risk flags, escalation triggers). The backend's
   Router/Evaluator/scoring shape already exists. Feed upstream criteria into
   the programmatic scoring layer so updated reasoning drives deterministic
   judgment: the LLM supplies reasoning from upstream prompts, the system still
   applies weights, thresholds, and rules.

2. **One source, two consumers.** The vendored skills become the single source
   of truth for both surfaces — the Cowork plugin serves them verbatim as slash
   commands, and the backend reads the same files to build evaluator configs.
   An upstream update moves both surfaces together.

3. **Version pinning in the audit trail.** Store the `claude-for-legal` commit
   each function was validated against, alongside the rubric version the audit
   trail already logs. This gives provenance over *whose* reasoning produced a
   decision, not merely that reasoning happened.

## Repository shape

```
legal-os/
├── vendor/claude-for-legal/     # subtree — the content, updatable
├── vendor/claude-for-legal.pin  # upstream commit we validate against
├── scripts/sync-upstream.sh     # subtree pull + re-pin + commit
├── plugins/                     # Cowork plugin — serves vendored skills verbatim
├── backend/app/agents/          # evaluators — read vendored SKILL.md as config
└── docs/                        # this plan
```

## Coverage gap (what upstream already builds)

Before building anything in the adapter layer, note that several roadmap items
are already realized upstream as skills:

- **Due Diligence Accelerator** → upstream `corporate-legal` (tabular review,
  issue extraction, data room watcher, closing checklist, material contracts)
- **Regulatory Change Monitor** → upstream `regulatory-legal` (reg feed watcher,
  policy diff, gap tracker, NPRM comments)
- **KM & Precedent Intelligence** → upstream `litigation-legal` + CoCounsel
  Westlaw connector
- **Employment agents** → upstream `employment-legal` (classification, leave,
  investigation, policy drafting, expansion planning)

The adapter should prioritize wiring these upstream skills into governed
evaluators over re-implementing their logic from scratch.

## Non-negotiables (never delegated to upstream)

- Row-Level Security ethical walls (Client A / Client B, employment / commercial)
- Deterministic score replay and JSONL immutable logging
- Model governance with hard veto rules
- Compliance readiness (SOC 2, ISO 42001, EU AI Act, ABA 512)
- The audit trail itself — it remains the product

## Next steps

1. Commit the vendoring + scaffold on `vendor/claude-for-legal`, open a PR to `main`.
2. Wire the weekly sync GitHub Action (PR-based, not auto-merge).
3. Build the skill → evaluator mapper for one function (contract review) as the
   adapter prototype.
4. Add `claude-for-legal` commit provenance to the audit trail.
