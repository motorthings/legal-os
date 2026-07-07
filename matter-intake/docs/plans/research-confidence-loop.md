# Research Confidence Loop — AESOP Roadmap Generation

**Date:** 2026-07-03
**Context:** Ashurst Perkins Coie roadmap evaluation (37/100 confidence)

## Problem

The AESOP research pipeline generated an AI adoption roadmap for Ashurst Perkins Coie (a 4-day-old merged law firm) with **37/100 confidence**. Three of 12 research documents came back empty ("Insufficient evidence found during research"), and the remaining 9 were all inferred from public sources with caveats. The roadmap agent received thin inputs and couldn't produce high-confidence recommendations.

Low confidence is honest — not a failure. But the system had no mechanism to close the gap between research and roadmap.

## Core Insight

Instead of the linear pipeline:

```
Research → Roadmap → discover gaps → manual re-research → Roadmap again
```

The research function should own the confidence threshold and loop internally:

```
Research → self-assess → gaps? → targeted re-research → confident? → Roadmap
```

The roadmap agent should never see thin inputs because the research phase fills gaps before handing off.

## Strategy

### Tier 1: Research function owns the confidence loop (primary)

**Completeness model per research area** — Each document type (org chart, governance policy, authority map, etc.) has a definition of "good enough." The research function scores its own output against that threshold.

**Gap-aware re-research** — When a research area is below threshold, the follow-up query targets what's specifically missing, not the whole topic again. Uses information found in pass 1 (company name, website, industry) to improve search targeting.

**Stopping condition** — Either confidence ≥ threshold, or N passes exhausted, or "this information doesn't publicly exist." In the last case, the roadmap agent receives an explicit signal ("Org Chart: not publicly available for this 4-day-old merged firm") rather than an empty document.

### Tier 2: Auto-generate research prompts from roadmap gaps (fallback)

When the roadmap report is generated, it also produces a **structured, machine-consumable research prompt** derived from gap analysis. The user can run this prompt in the app to fill remaining gaps and regenerate. This is the fallback for when automated re-research hits a wall — e.g., internal documents that can't be found publicly.

### Tier 3: Distinguish "doesn't exist" from "couldn't find"

Detect signals of new entities, mergers, or pre-governance organizations. An empty Org Chart for a 4-day-old firm is the correct answer — score it as "not applicable / not yet existing" rather than "research failure." This lets the roadmap agent calibrate: "this organization is pre-governance, here's what to build first" instead of "we couldn't find your governance docs."

## Key Design Decisions

1. **Research function is the gatekeeper** — Roadmap agent only receives inputs that meet a confidence threshold, or explicit "not available" signals.
2. **Gap detection is automated** — No user intervention needed for the common case (re-search with better targeting).
3. **User as fallback, not primary path** — The gap-to-research-prompt bridge triggers only when automated re-research exhausts its options. User uploads internal documents, research function re-runs, confidence improves.
4. **Honest nulls are first-class** — "This data doesn't exist publicly" is structured information, not a failure state.
