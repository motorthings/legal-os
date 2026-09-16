# Firm Roadmap Generator — Design and Build Plan

*Written 2026-09-11. Canonical design for `legal-os/firm/`. Sibling to `docs/radar/radar-design.md`; the radar forecasts the market, this forecasts a firm's path through it.*

---

## 1. What this is

A working model of the **Advise** phase of a legal AI engagement: given a firm's current position and the market's current state, produce a deployment roadmap with a business case attached and a re-evaluation loop running underneath.

It sits on top of `radar/advisory.py`, which already answers the per-fault-line questions ("is this control required of us" and "is now the time to put AI on this work"). It does not duplicate that. It adds the layer above: **which work, in what order, with which tools, gated by what.**

## 2. What this is not

- Not a client deliverable. It generates synthetic roadmaps from synthetic firms. Nothing here has touched real client data.
- Not a replacement for delivery-lead judgment. It makes that judgment explicit, replayable, and inheritable. The override mechanism exists precisely because the model will be wrong.
- Not a product pitch. It demonstrates legal-native rigor at every gate; it does not assert it.

## 3. The thesis

A framework is a socket. It has no value on its own.

The power is in what plugs into it: **Harbor's institutional knowledge on one side, the client firm's own knowledge on the other.** Neither alone produces a roadmap.

- Generic framework + Harbor KB = Harbor's house view, ungrounded in this client.
- Generic framework + client KB = what the client already knows about itself. Worthless from outside.
- Harbor KB + client KB = the product.

Harbor's own service page states the knowledge exists: enablement teams have run AI adoption, training and change management inside law firms, including Magic Circle firms. The knowledge is real. What it lacks is a structured place to live and a way to be deployed against a specific client's facts.

**The corollary is the harder point.** If the KBs are the power, then *capturing* them is the bottleneck. Harbor is 10-12 people doubling within a year. Every engagement's learning currently lives in a delivery lead's head and evaporates on roll-off. Building the socket is what forces the extraction. That is the knowledge-management gap named at the 2026-08-28 panel, made concrete.

## 4. Why this is Harbor-shaped and not generic

Harbor's Advise phase publishes its own deliverable list:

> readiness assessment · use-case identification and prioritization · workflow and process analysis · technology and model evaluation · governance and risk frameworks · **deployment roadmap** · **business case and success measures** · operating model design

Items two, four, six and seven are the generator's outputs. Items one, three, five and eight are its inputs. The taxonomy is not invented here.

Two further points from their own framing:

- **"Model and platform evaluation" appears in both Advise and Manage.** That is a loop, not a duplicate. Platforms must be re-evaluated as the market moves. The radar is the only instrument that knows *when* to re-evaluate.
- **"System and data integration" is a named Implement deliverable.** The KB and data-cleansing work is a first-class category in Harbor's own model, not an incidental prerequisite.

## 5. The market spine

From the 2026-09-11 landscape research (full detail in `landscape-2026.md`):

**The axis is no longer which model. It is who lets a model reach governed firm knowledge without exporting it.**

| Layer | Position |
|---|---|
| Connective tissue | iManage MCP Server (2026-05-14, read; write actions Oct 2026), NetDocuments MCP (2026-04-01) |
| Built on top | Harvey (native API + MCP clients), CoCounsel (MCP to Claude), LexisNexis Protégé (Protégé APIs), Ironclad |
| Thin surfaces | Legora, Eudia. Highest growth, weakest published integration detail, most vendor-supplied deployment claims |
| Enclosed | Relativity aiR (RelativityOne only) |

Supporting findings:

- **iManage's own 2026 benchmark: 32% cite integration complexity as a top barrier to AI adoption.** Wolters Kluwer puts it at 35-39%.
- **Adoption is not the bottleneck.** ILTA 2025: 80% of firms using or exploring genAI, up from 37% in 2024. But 71% of Harvey users and 90%+ of iManage AI users are still piloting. Only 22% have a visible AI strategy.
- **Trust is the bottleneck.** Factor/Artificial Lawyer (2026-03): 83% have broad access, 54% use it often, 22.1% report high trust, 69.7% of outputs still need rework.
- **Measurement is the bottleneck.** Harbor's own Legal Lab finding reproduced in their operating-model research: 0% of participating top-tier firms and global in-house departments reported a mature framework for measuring AI's business impact.

The research carries per-claim reliability tiers. Vendor-supplied deployment numbers are labeled as such throughout. Nothing in the catalog is asserted as audited fact.

## 6. Architecture

### Inputs

| Input | Source | Status |
|---|---|---|
| **Harbor KB** | Synthetic. Constructed from public material plus inference. | Labeled synthetic throughout |
| **Generic KB** | The control. What any consultancy hands you. | Synthetic, deliberately thin |
| **Tool catalog** | The 2026 landscape research, per-claim provenance preserved | Researched, tiered |
| **Firm profile** | Meridian Law Group, the synthetic 47-attorney firm from `feature/ai-maturity-assessment` | Synthetic, from an existing corpus |
| **Market state** | `docs/radar/data.json` and `radar/advisory.py` | Live, deterministic, calibrated |

### Processing

Deterministic Python. No LLM in the scoring path. An LLM may narrate the output, but every number and every verdict traces to a mechanical gate. This is the `csm-health` principle applied here: risk scoring is code, the model only writes prose.

```
firm/stack.py      load firm's systems, integration status, posture
firm/catalog.py    load tool capability docs with per-claim provenance
firm/score.py      (capability × tool × firm) -> fit score, deterministic
firm/sequence.py   -> roadmap: projects in Advise / Implement / Manage bands
firm/triggers.py   radar fault-line trends -> re-evaluation conditions
firm/provenance.py [OBSERVED] / [INFERRED] / [ASSUMPTION] machinery
firm/synthesize.py orchestrator
firm/build.py      render JSON + self-contained HTML
firm/run.py        CLI driver
```

### Output

A synthetic Harbor Advise deliverable:

1. Current position (maturity bottleneck, stack inventory, integration reality)
2. Prioritized use cases
3. Technology and model evaluation (ranked, with per-claim provenance)
4. Deployment roadmap (projects in three bands, with dependencies and gates)
5. Business case (per-project economics via the Profit Paradox)
6. Operating model note
7. **Assumption register** (generated, not hand-written)
8. **Re-evaluation triggers** (radar-driven)

## 7. Project taxonomy

Four types, mapped to Harbor's own language:

| Type | Harbor's term | Band | Driven by |
|---|---|---|---|
| Foundation | System and data integration | Implement | Firm stack, maturity bottleneck |
| Governance | Governance and risk frameworks → Governance controls | Advise → Implement | `advisory` GOVERN verdicts |
| Platform | Technology and model evaluation → Model selection and orchestration | Advise → Implement | `advisory` DEPLOY verdicts, stack fit |
| Measurement | Business case and success measures | Advise | The zero-percent gap |

## 8. Sequencing model

Rules, applied in order:

1. **Foundation precedes platform** where the platform depends on it. A precedent-search tool is worthless against an unclean precedent library.
2. **Governance precedes deploy** where the control is required. `advisory.py` already enforces this: economics never block a required control.
3. **Measurement runs alongside, never after.** A project without a go/no-go threshold is a pilot, and pilots are what the market is stuck on.
4. **Required before opportunistic.** `advisory` distinguishes them; the sequence respects it.

## 9. The re-evaluation loop

The novel piece. Harbor sells "model and platform evaluation" as a service. This makes it continuous.

The radar tracks eleven fault lines with trend data and a lead indicator. Each platform decision in the roadmap carries a **trigger condition** derived from it:

> Re-run the Harvey-versus-Eudia call when `convergence` pressure crosses 7.0, or when the `vendor_liability` seam annotation changes.

This is only possible because the radar exists. It is the join between the market forecast and the firm's plan, and it is the one thing a general consultancy cannot replicate.

## 10. The assumption layer

Every project carries:

- **inputs** — which inputs drove it, each tagged `[OBSERVED]` / `[INFERRED]` / `[ASSUMPTION]`, reusing the convention at `backend/simulation/intake.py:21`
- **confidence** — fraction of driving inputs that are observed
- **falsifier** — one line: what would change this call

The roadmap carries an aggregate: what percentage of the sequenced work rests on assumed versus observed inputs.

Tool catalog entries carry their own provenance separately, inherited from the research:

```
"deployment_claim": {"text": "80% of the Am Law 100", "tier": "TRADE", "verified": false}
```

So the roadmap can state plainly that a recommendation rests on a vendor-supplied number that was not independently verified. That is the radar's authority-over-volume discipline applied to vendors instead of courts.

## 11. Override capture — the flywheel

`firm/data/overrides/{firm}.json`. When a delivery lead changes a sequenced step, the change *and the reason* are stored. On the next run, stored overrides load as an additional KB layer.

Nobody writes a capability doc. The knowledge gets captured as a byproduct of doing the work, which is the only way knowledge capture has ever succeeded. It is the same mechanic as the Rubrik human-edit feedback loop.

This is the component that decides whether the thing becomes an asset or another wiki nobody reads. If it does not work, the KB stays in people's heads.

## 12. The demo

Four runs, showing the delta:

|  | Generic firm | Meridian Law Group |
|---|---|---|
| **Generic KB** | Every consultancy's roadmap | What the firm already knows about itself |
| **Harbor KB** | Harbor's house view, ungrounded | **The product** |

Then the flip: change Meridian from hourly to fixed-fee. The `fees` fault line moves, drafting goes from net-loss to net-win under the Profit Paradox, and the roadmap re-sequences.

That interaction proves it is a model and not a document. A plan you cannot re-run is a wish.

**Risk to watch:** if the generic-KB roadmap comes out close to the Harbor-KB one, the demo proves the opposite of the thesis. Run it before showing anyone.

## 13. File layout

```
legal-os/
├── firm/
│   ├── __init__.py
│   ├── synthesize.py
│   ├── catalog.py
│   ├── stack.py
│   ├── score.py
│   ├── sequence.py
│   ├── triggers.py
│   ├── provenance.py
│   ├── build.py
│   ├── run.py
│   ├── data/
│   │   ├── kb/
│   │   │   ├── harbor/          # synthetic Harbor experience
│   │   │   └── generic/         # the control
│   │   ├── tools/               # ~12 vendor capability docs
│   │   ├── firms/               # meridian.json, generic.json
│   │   └── overrides/           # captured delivery-lead changes
│   └── tests/
├── docs/firm/
│   ├── design.md                # this document
│   ├── method.md
│   ├── assumption-register.md
│   ├── landscape-2026.md
│   └── roadmaps/                # generated output
└── frontend/public/firm/        # mirrored JSON + HTML
```

Mirrors the radar's pattern exactly: standalone module, deterministic, writes into `docs/` and mirrors to `frontend/public/`.

## 14. Staged build

### Stage 1 — the proof

`synthesize`, `catalog`, `stack`, `score`, `sequence`, `provenance`, `run`. Two KBs. One firm. Twelve tools. The 2x2 and the flip. JSON output.

Proves the thesis. Everything else is additive.

### Stage 2 — the surface

`build.py` and the HTML page. Frontend route at `/firm`. Override capture and the KB ingestion loop.

### Stage 3 — wiring

`triggers.py` against live radar data. The re-evaluation loop. Connection to `/api/projects/{id}/simulate` (the transformation wind tunnel) for the transformation-level view.

## 15. Documentation set

| Doc | Contents |
|---|---|
| `design.md` | This. Architecture, sequencing model, build plan |
| `method.md` | How a roadmap gets made, step by step. Pairs with `docs/radar/build-method.md` |
| `assumption-register.md` | Every load-bearing assumption with its pressure test |
| `landscape-2026.md` | The research, published as its own piece with provenance tiers |

## 16. Assumption register for this design

The document's own assumptions, pressure-tested.

| # | Assumption | Fails if | Test |
|---|---|---|---|
| 1 | A firm's stack fits a small structured schema | The real constraint is contractual or political, not technical | Compare against a real firm's inventory |
| 2 | Products compare on a common rubric | Harvey and Claude are not the same kind of thing and should not be ranked head to head | Factor into the rubric, or stop ranking them on one axis |
| 3 | Integration status predicts feasibility | The real blocker is vendor API terms and the firm's IT appetite, both invisible in the schema | Add contract and appetite fields |
| 4 | Fault-line pressure translates to sequencing priority | Untested | Anecdotal check against the three case postures in `advisory.py` |
| 5 | Maturity bottleneck gates which projects can start | Untested | Test against the maturity branch's own StageGap logic |
| 6 | A roadmap is the right output format | Firms do not want a roadmap, they want the next decision | This is the most likely to be wrong, and it is a scope question, not a modeling one |
| 7 | Harbor's institutional knowledge can be made explicit | It is tacit and stays tacit | The override mechanism is the only proposed answer |
| 8 | The synthetic Harbor KB is representative | It is constructed from public material and inference | Review by someone inside Harbor |

Assumption 8 is the live risk. The Harbor KB is the component most likely to be wrong and the one everything else builds on.

## 17. Provenance conventions

Every fact in this system carries how it was obtained.

| Tier | Meaning |
|---|---|
| `PRIMARY` | Vendor page or first-party release, read directly |
| `TRADE` | Reputable legal-tech press |
| `SECONDARY` | Ordinary press, partner blogs, press-release reprints |
| `LQ` | Low-quality aggregator. Treat as a lead, not a fact |
| `UNVERIFIED` | Single-sourced, contradictory, or unreachable |
| `SYNTHETIC` | Constructed for this POC. Not a claim about reality |

The system refuses to promote a tier. A vendor's claim stays a vendor's claim in every downstream artifact.

---

## Appendix — Sources

- `radar/advisory.py` — the four-effect-order model this builds on
- `docs/radar/radar-design.md` — the forecast engine
- `docs/radar/radar-market-inventory.jsonl` — the tiered vendor evidence feed
- `backend/simulation/intake.py:21` — the `[SURVEY]`/`[INFERRED]`/`[ASSUMPTION]` convention
- `feature/ai-maturity-assessment` — the maturity models, `StageGap`, and the Meridian corpus
- `legal-sim/pricing/pricing_model.py` — the AI Profit Paradox
- Harbor Deploy service page — Advise / Implement / Manage framework and deliverable lists
- 2026-09-11 legal AI landscape research — `docs/firm/landscape-2026.md`
