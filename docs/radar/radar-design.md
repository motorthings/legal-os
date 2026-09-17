# Fault-Line Radar — Prediction-Engine Design

**Status:** canonical source of truth for the fault-line engine (the "Fault-Line Radar").
**Owner:** Charlie Fuller. **Last updated:** 2026-09-17.
**Naming note (2026-09-17):** the artifact is no longer presented as a prediction engine. The
ranking is demoted to an internal sort function and the firm-facing claim is the record plus the
antecedent lead time — see §5.7.
**Siblings:** `docs/radar/build-method.md` (the canonical *method* — how this work gets made),
`radar/README.md` (run + backlog log), `radar/sources/coverage_notes.md` and
`radar/sources/review_queue.md` (operational gap lists). The generated page and data live in
`docs/radar/` and are not edited by hand.

**Scope decision (resolved 2026-09-07):** three-part stack with a single determinism contract
(§2). Part A, a gradeable forecast core scoped to legal-duty stress and rules; Part B, an
advisory layer that renders operationalization guidance from an enablement axis plus A's outputs
and is never backtested as a prediction; Part C, the firm-transformation sim (law-firm-sim /
legal-sim) that models whether a specific firm's economics permit acting. Audience intent: an
**AI legal-consulting operationalization advisor** — the work helps a consultancy tell a legal
organization where to build and govern AI next. It is deliberately generic and names no specific
firm; it is written so it aligns with any such consultancy without calling one out.

---

## 1. Why the engine exists — the confluence, stated as intent

The engine forecasts where a legal-AI consultancy should tell a legal organization to build
and govern AI next. That readout sits at the intersection of three influences that develop on
partly independent clocks and co-mingle:

1. **Supply — the technology and its direct effects.** What AI can now actually do in legal
   work, and the first-order effects of that capability.
2. **Enablement — the tools a firm can actually run.** What a legal organization is able to
   do *because of the software it has*: which tools exist, integrate, and are being adopted
   by firms, not just what a raw model can do in a lab.
3. **Governance — the rules.** The rulings, bar opinions, and statutes put in place *as a
   result of the technology and of the tools deployed*.

The three are hard to separate cleanly and feed each other both directions: a capability can
provoke a rule, a deployed tool can provoke a rule (firms filing AI output caused the sanction
wave), and a rule then gates or forces broader adoption. The confluence — the operating
envelope a legal organization can actually run and should invest in — is the product of all
three. **The engine surfaces that envelope.**

To keep that claim honest, the work is split into **three parts with different epistemic
standards** (see §2): the part that forecasts rules is graded against reality; the part that
traces the market trajectory is evidence-weighted but never graded as a call; the part that
models what a *specific* firm can do is a confidence-intervaled scenario model, never a
prediction. The three parts together are the end-to-end operationalization answer.

## 2. Scope — three parts, one determinism contract

The full architecture is a three-part stack. Each part has a different object, and the kind of
determinism each can honestly claim follows from that object. This is the unifying contract:
never let one part claim the determinism of another.

| Part | Object | What it is | Determinism claim |
|---|---|---|---|
| **A. Forecast core** (radar) | outside the firm, the rules | forecast | **T-rule**: graded by backtest |
| **B. Advisory layer** (radar) | outside the firm, the market | trajectory + agenda | **T-market**: evidence-traced, never a call |
| **C. Firm-transformation sim** | inside the firm | scenario model | **T-model**: confidence-intervaled, never a prediction |

### Part A — Forecast core (gradeable)

Scoped to legal-duty stress and the rules that react to it. This is what calibration backtests,
so a "call" means the duty/rule meter was already elevated before the event landed. Epistemic
standard: evidence over eloquence, deterministic, auditable. Enablement and market opinion must
not pollute this layer's meters, or the grade stops meaning anything.

### Part B — Advisory / operationalization layer (not gradeable as a call)

Consumes Part A outputs (rule pressure, adoption, horizon) plus an **enablement axis** that Part
A deliberately excludes, and renders build-priority and operationalization guidance. This is
where the consulting value lives: "given what AI can do, what the rules now require or permit,
and what tools a firm can actually deploy, what should this organization build, govern, and buy
next?" It is guidance under uncertainty, so it is never run through the backtest and never
framed as "predicted." Its trajectory claims are evidence-weighted (T-market), and it hands its
agenda to Part C for the firm-specific economics.

### Part C — Firm-transformation sim (scenario model, inside the firm)

The answer to the implementation-variance question that no outside forecast can resolve. Two
sibling engines share one core: **law-firm-sim** (a digital twin of one real firm, driven by a
`FirmSignature`: pricing posture, leverage, comp, origination concentration) and **legal-sim**
(the abstract / legal-AI-industry question: which seam a tool attacks, which lever moves
adoption in general). These take a firm's actual signature plus Part B's agenda and Monte Carlo
which levers move this firm's P&L and in what order, returning confidence-intervaled outcomes.
Its headline finding, the **AI Profit Paradox**, is a firm-level reality check Part B cannot
compute on its own: on hourly billing, more AI is a net loss; only fixed-fee (value) pricing
makes the same AI a net win. So whether a firm *can* act on the radar's agenda is conditional on
its economics, and only Part C tests that condition.

Part C is never graded as a call and never enters the calibration. Its psych profiles and
mock-LLM priors stay low-confidence and human-reviewed (the same discipline applied to persona
models in the judicial-analytics fault line). It is a decision-support what-if, reported as a
distribution, never as a fabricated point forecast of a specific firm's outcome.

The three-part split is what lets the work be simultaneously credible (A grades itself), current
on the market (B traces the trajectory), and actionable for a specific organization (C models
whether this firm's economics permit acting). The consulting product is the whole stack;
credibility lives in A, market truth in B, firm specificity in C.

## 3. Core concepts

**Fault line.** The place where an AI capability stresses an existing legal duty. The engine
forecasts the fault line, never an exact ruling or date.

**Meters (0–10).** Each fault line carries three meters plus a queue:

- **L1 Capability** — can AI now do the thing that creates the fault line. The supply signal.
- **L2 Ruling pressure** — will a court, bar, or statute move on it. The governance signal.
- **L3 Adoption** — is the *control* (the operating-model fix for that fault line) becoming
  table stakes, court or no court. Market adoption of the fix.
- **Queue** — currently a single confluence readout (see §4 G1 and §7 for its redesign into
  Layer B).

**Order framing.** The meters are presented as a one-way cascade —
`L1 capability → L2 ruling → L3 adoption` — and Layer A's calibration grades that order
(§4). The history validation in §5 shows this single ordering is a forced frame for some
lines: several are capability-driven, others are pure market or regulatory reactions with no
capability driver. §6 records that as a gap; Layer A should move to per-line causal drivers.

**The eleven fault lines** (each also carries `pressure_seed`, `horizon`, `layer`, a
`control`, and the Model Rules it maps to):

| id                 | control                                        | seed | horizon       |
| ------------------ | ---------------------------------------------- | ---- | ------------- |
| insurance          | Governance as an insurable artifact            | 8.5  | near (0-12mo) |
| disclosure         | Verification-by-default with an audit trail    | 8.0  | near (0-12mo) |
| verification       | Documented verification + trace logs           | 7.5  | near-mid      |
| confidentiality    | Data-flow mapping + vendor attestation         | 7.0  | near (0-12mo) |
| convergence        | One operating model, to the strictest standard | 7.5  | near (0-12mo) |
| agentic            | Human-decides gates + scope-limiting           | 6.5  | mid (1-3yr)   |
| benchmark          | Tool-certification benchmark (NERVE)           | 6.0  | mid (1-3yr)   |
| competence         | Firm-wide training + governance program        | 6.0  | mid (1-3yr)   |
| judicial_analytics | Guardrailed strategy sim (no actor prediction) | 5.0  | mid (1-3yr)   |
| fees               | Value-delivered measurement                    | 4.5  | mid-far       |
| vendor_liability   | Tool-provenance documentation                  | 3.5  | far (3yr+)    |

## 4. Layer A — forecast core, as built (v1)

Code lives in `radar/` (`fault_lines.py`, `score.py`, `calibration.py`, `kb.py`, `build.py`).
This section describes the current implementation. §6 lists what must change to keep Layer A
honest under the two-layer scope.

### 4.1 Source-authority tiers — weight authority, not volume

Every item in `radar/sources/feed.jsonl` is tagged with a tier. Weight by sway so the forecast
cannot be captured by whoever publishes most (usually vendors).

| Tier | label                        | weight |
| ---- | ---------------------------- | ------ |
| T1   | Binding / primary            | 1.00   |
| T2   | Regulatory guidance          | 0.80   |
| T3   | Empirical / institutional    | 0.60   |
| T4   | Professional commentary      | 0.35   |
| T5   | Vendor / marketing / opinion | 0.008  |

A T5 vendor blog carries ~1/100 of an ABA opinion and ~1/125 of a binding ruling. Volume
alone never moves a reading.

### 4.2 Scoring math (deterministic and replayable)

All knobs live in `fault_lines.py` so any run replays exactly. Per fault line, given evidence
available on or before the as-of date:

- **Base weight** = tier weight, × 0.4 if the source sells what it comments on (`conflict`),
  × 1.25 if it carries hard data (`empirical`), × recency decay.
- **Decay**: momentum halves every 180 days for non-standing tiers. T1/T2 never decay out.
  Capability evidence never decays — a proven capability does not un-happen.
- **Corroboration**: +0.15 per distinct higher-or-equal tier. Ten vendor posts cannot outweigh
  one ruling.
- **Meter shape**: each meter starts at a seed and is lifted toward 10 by a saturating curve,
  `lift = (10 − seed) × (1 − exp(−weighted_evidence / divisor))`. Divisors: ruling 3.0,
  adoption 2.0, capability 4.0 (the capability lane is the most conservative so a demonstration
  nudges rather than shouts).

### 4.3 Lane separation

Capability and market evidence are distinct objects from a ruling, so they get their own
weighted, labeled lanes so inference never masquerades as legal fact.

- **L1 capability** uses `CAPABILITY_WEIGHTS`: benchmark 1.00, study 0.80, deployment 0.50,
  release 0.35, demo 0.12, hype 0.02. Non-decaying.
- **L3 adoption** uses `MARKET_WEIGHTS` — how binding the item is *on the market*: insurer
  1.00, procurement 0.85, deployment 0.70, cert 0.60, process_mandate 0.55, commentary 0.20,
  pundit 0.02.

### 4.4 Calibration — grading the engine, not asserting the future

`calibration.py` backtests point-in-time. For each recorded resolution (a ruling/event that
landed, in `radar/history/resolutions.jsonl`), it replays the engine `LEAD_DAYS` (90) before
the event using only prior evidence and checks whether the right meter already read ≥
`CALL_THRESHOLD` (7.0) — "called?" plus lead. It reports hit rate overall and per order, two
cascade conditionals (`P(L2|L1)`, `P(L3|L2)`), an "outran" set (capability called with no
ruling yet), a pressure time-series (`history/snapshots.jsonl`), and immutable per-run audit
artifacts (`history/runs/run-*.json`). The seed set is small and the L1 lane is young, so hit
rates are reported honestly as such.

### 4.5 Outputs

`radar/build.py` writes `docs/radar/index.html` + `data.json` + `kb.json` (served by GitHub
Pages) and mirrors them into `frontend/public/radar/` for the in-app `/radar` page.
Regenerated by `.github/workflows/radar.yml`.

## 5. Coverage vs recent history (validation, 2026-09-07)

Method: an inventory of the engine's tracked effects was diffed against a researched inventory
of the major events and structural shifts in legal AI from 2023 through mid-2026. Verdict: the
**governance axis is on target**; the **enablement axis is the demonstrated gap**, and recent
history says that is where the largest and most monetizable effects actually were.

### 5.1 On target — the governance axis matches recent history

Every defining rule-level effect of the period is captured and seeded:

| Effect (recent history)                                   | Fault line                  |
| --------------------------------------------------------- | --------------------------- |
| Hallucination sanctions → disclosure/verification wave    | disclosure, verification    |
| ABA Op. 512 + state ethics wave                           | competence, confidentiality |
| EU AI Act + US state patchwork                            | convergence                 |
| Malpractice insurers gating AI                            | insurance                   |
| Benchmarks / error-rate studies                           | benchmark                   |
| Agentic + UPL + the AI AGENT Act                          | agentic                     |
| Billing pressure (value-based fees)                       | fees                        |
| Vendor/product liability (EU Product Liability Directive) | vendor_liability            |
| Judicial profiling (France Art. 33)                       | judicial_analytics          |

### 5.2 Off target — the enablement axis, with real content

The major effects the engine does **not** track are all on the supply/enablement side, and they
are the content Layer B's enablement axis must eventually carry:

- **Tool-landscape consolidation and funding.** Harvey to an ~$8B valuation with >$100M ARR
  and roughly half the Am Law 100; Thomson Reuters bought Casetext ($650M); Clio bought vLex;
  ~$4B/yr of VC into legal tech. The tools available to lawyers are consolidating fast.
- **Firm-wide deployment and structural reorg.** One global firm put gen-AI on ~5,000 lawyers
  and 43 offices, then shipped agentic tools with revenue-sharing deals; chief-AI-officer roles
  normalized. Firms are reorganizing around the tools, not just piloting them.
- **Client / GC procurement pull.** AI questions in outside-counsel RFPs roughly quadrupled;
  a large share of GCs say they would switch firms lacking an AI strategy. This is demand-side
  pull that now decides whether a firm gets work.
- **The proven use-cases maturing.** Contract review and e-discovery are the two most-trusted,
  most-adopted AI uses (e-discovery ~95% trust); this is the concrete "what the software does"
  base under everything else.
- **Delivery-channel reform.** Regulatory sandboxes and alternative business structures
  (Arizona ~150 licensed entities including a Big Four entrant; Utah's sandbox) change *who is
  allowed* to deliver AI legal services and through what channel.
- **Courts regulating their own AI use.** A first statewide court rule (Cal. Rule of Court
  10.430) requires courts to adopt AI-use policies — distinct from the judge-*analytics* line,
  which only tracks predicting judges.

### 5.3 Data-currency corrections (for the feed, not the logic)

- **Colorado weakened in 2026.** Colorado's 2024 comprehensive AI law was repealed/replaced in
  May 2026 by a lighter transparency regime effective Jan 2027. **Resolved 2026-09-07:** the feed
  item asserting the risk-based regime never took effect was corrected to the actual 2026-05-14
  repeal/replacement (SB 26-189).
- **Cal. Rule of Court 10.430** (adopted July 2025) was a real governance event absent from the
  feed. **Resolved 2026-09-07:** added as a T1 item mapping to convergence/disclosure/verification.

## 5.4 Run-to-run harvester memory — Layer 0 (2026-09-14)

So a new research run uses what the last one did instead of starting cold, the admission
gate has durable memory, wired into the OS so it runs on **every** pass (not only when
harvesting):

- **Identity** (`dedup.py`) — a document is identified by canonical URL, content hash,
  and extracted case citations (rule/statute refs excluded so FRAP 38 doesn't collapse
  distinct rulings). Pure, deterministic, no deps.
- **SeenIndex + admission ledger** (`ledger.py`) — the `SeenIndex` is everything the KB
  (`feed.jsonl`) already holds; `history/admissions.jsonl` is every candidate any prior
  run decided on (admit / quarantine / dedup, with reason). `admit()` (`ingest.py`)
  consults both BEFORE evaluating a candidate, so a run never re-admits a document the
  KB holds, never re-judges a quarantined one, and collapses echoes to the primary.
  Idempotent and tested (`tests/test_dedup.py`, 7/7).
- **Wired into the OS** — `run.py` calls `reconcile_kb()` on **every** pass (local,
  `--watch`, and the weekly CI job), enforcing KB integrity and refreshing the seen-memory
  before any build; the CI workflow commits `feed.jsonl` + the ledger + snapshots so the
  memory persists across scheduled runs. Distinguishes true content duplicates (alarm)
  from distinct docs sharing an aggregator URL (informational).
- **Not yet**: the network fetchers (`_harvest()`) and Layer-2 Voyage/pgvector semantic
  dedup. `admit()` runs the full memory today on any candidate list.
- **Honesty interaction**: Layer-3 learned tuning (source reliability, thresholds) would
  change scoring and therefore must bump `KNOBS_FROZEN_AT` (see §5.3) and re-baseline —
  learned-methods memory and the forward-only holdout are coupled by design.

## 5.5 Source-reliability learning — Layer 3 (2026-09-14)

The "use what it learned last time" half. Authority (tier) is fixed; reliability is
EARNED and kept strictly separate (backlog 8b).

- **Mechanism** (`reliability.py`) — a source that repeatedly presages real rulings (an
  item attributed to a ruling's fault line, dated ≥ `LEAD_DAYS` before it) earns a
  multiplier `1 + PRESAGE_STEP × (rulings presaged)`, capped at `RELIABILITY_CAP_MULT`.
  Written to `history/source_reliability.json`, read by `score._item_weight`, which then
  caps the *effective* weight at `RELIABILITY_MAX_EFFECTIVE` (0.75) — below the T2 (0.80)
  and T1 (1.00) primary-authority floors. A proven vendor blog can rise; it never becomes
  a court. One-directional: written by the learner, only read by the scorer.
- **The honesty gate** — only OUT-OF-SAMPLE presages count (rulings dated after
  `KNOBS_FROZEN_AT`). In-sample hits are retrodiction (§5.3); rewarding a source for
  "presaging" a ruling the feed was authored knowing about would tune the scorer on
  hindsight and silently corrupt the holdout. So today, with no post-freeze rulings, every
  multiplier is 1.0 and scoring is byte-identical to Layer-2 — the loop is wired and
  dormant, not faked. It begins learning only from genuine forward evidence.
- **Wired into the OS** — `run.py` refreshes the ledger every pass; the reliability ledger
  hash is captured in each run artifact's knobs so a score replays against the exact
  learning state it used. Tested (`tests/test_reliability.py`, 4/4: dormant-today,
  in-sample-gated, earns-and-caps, effective-cap-below-primary).

## 5.6 Network fetchers — allowlist-bound, offline by default (2026-09-14)

The harvesting half of Phase 2 (`fetchers.py`), wired to `ingest.admit()` so every fetch
flows through the Layer-0 dedup memory.

- **Allowlist is the boundary, not a filter.** A URL whose domain is not in
  `SOURCE_ALLOWLIST` is refused *before any request*; tier is assigned at admission from
  the allowlist, never from the source's own claim. No open-web crawl.
- **Offline by default.** `harvest()` makes no network calls unless `live=True` or
  `RADAR_LIVE_FETCH=1`, so CI, tests, and default runs are deterministic and silent. Per-
  source failures are skipped, never fatal.
- **Harvested docs get their own store.** Fetched rows go to `sources/harvested.jsonl`
  (marked `harvested: true`), NEVER the hand-curated `feed.jsonl` — a human vouched for
  every curated row, and mixing machine-pulled items into it would silently move the
  calibration baseline. `score.load_corpus()` merges the two for scoring; an absent/empty
  harvested file means curated-only, so scoring is unchanged until harvesting admits
  something.
- **Stdlib only** (urllib + xml.etree) — RSS 2.0 and Atom, no new dependency. Tested
  offline against recorded fixtures (`tests/test_fetchers.py`), including the allowlist
  refusal and the fixture→candidate→admit path.
- **CourtListener removed (2026-09-15).** Court opinions are no longer harvested from
  CourtListener. The search endpoint + a 2-step full-text fetch were built, but full
  opinion text drowns the AI signal in boilerplate — the real AI case scored *below*
  noise under embedding cosine. Discovery is Descrybe's job: `curate.py` turns
  `search_cases_by_concept` results into feed candidates, deduped against the KB and
  hand-attributed. The Voyage embedding gate (`embed.py`) was reverted for the same
  reason — general embeddings are the wrong tool for legal relevance.

## 6. Logic gaps in v1 (recorded so each fix is traceable)

- **G1 — The confluence readout (queue) drops the capability axis.** Queue is
  `(pressure/10) × (adoption/10) × 10`, a product of the rule and adoption meters only. L1
  never enters, and enablement is absent. It answers "which compliance control to stand up,"
  not "where capability, deployable tools, and permissive rules make an operational
  opportunity." This readout belongs to Layer B and must be rebuilt there.
- **G2 — Firm-side enablement is not an independent axis.** "What firms can do given the
  software they have" has no meter. It is folded into L3 as one weight (`deployment: 0.70`)
  beside insurer/cert/process_mandate, conflating "the governance fix is table stakes" with
  "the enabling tool is deployable." The history validation in §5.2 confirms this is the gap
  that matters. **(Resolved 2026-09-07: the E market-enablement axis, §9, is that meter.)**
- **G3 — The causal model cannot represent tool-deployment → rule.** The cascade is strictly
  capability → ruling → adoption, and calibration grades only L1→L2 and L2→L3. But the richest
  lines (disclosure, verification) were provoked by firms *deploying* tools in filings — a
  deployment→rule path that runs backwards in the current order.
- **G4 — A strict single order is a forced frame.** Some lines are capability-driven; others
  (insurance, fees, convergence, vendor_liability) are pure market or regulatory reactions with
  no capability driver. Every line still carries all three meters and the same conditional
  calibration, so the meters mean different things line to line.
- **G5 — The L2 "ruling" meter is not lane-isolated.** It ingests every matched document
  regardless of lane, so a T3 market action or commentary can lift ruling pressure. Under the
  two-layer scope this is a Layer-A integrity problem: the meter the ruling grade is computed on
  must be isolated to actual ruling/regulatory evidence.
  **(Resolved 2026-09-14.** `RULING_TIERS = {T1, T2}` + optional per-item `ruling` override in
  `fault_lines.py`; `score._is_ruling()` gates the L2 math. Only ruling/regulatory evidence feeds
  ruling pressure, its corroboration, and its trend; market/commentary/vendor items stay on the
  line as provenance but cannot lift the grade. Effect: RULE de-saturated on the vendor-heavy lines
  — benchmark 9.1→6.9, agentic 9.3→7.3. `n_ruling_evidence` is reported beside `n_evidence`.)

## 5.3 Calibration honesty — the false-positive side and the holdout (2026-09-14)

The recall backtest (§calibration) answered only "of the rulings that landed, how many did we
flag?" That number is structurally inflatable: a model that pins every line high scores perfect
recall. Four fixes close the gap, all deterministic and replayable:

- **Precision / base-rate grid** (`calibration.precision_report`). A (fault-line × month) grid over
  the feed's lifespan scores every cell TP/FP/FN/TN against order-2 resolutions within a forward
  window, yielding **precision, recall, flag-rate, base-rate, and LIFT (precision / base-rate)**.
  Current reading: precision **0.10**, flag-rate **0.62**, base-rate 0.063, **lift 1.59** — the
  engine flags ~62% of line-months and has modest but real skill over flagging blindly. This is the
  honest exposure the recall number hid; it is reported, not buried.
- **Forward-only holdout** (`KNOBS_FROZEN_AT`). Every resolution on/before the freeze is graded as
  `in_sample` (**retrodiction** — knobs, seeds, and feed were authored knowing the outcome) and only
  post-freeze events count as an `out_of_sample` forecast track record. Today: in-sample 0.67 (6/9),
  out-of-sample 0/0. The 6/9 is explicitly *not* claimed as predictive skill.
- **Seed ablation** (`calibration.seed_ablation`). Re-runs the backtest with every seed neutralized
  to `NEUTRAL_SEED`. `seed_dependence` = default hit-rate − neutral hit-rate = **0.11** today: that
  share of calls rests on the analyst baseline, not on point-in-time evidence.
- **Corroboration by independent source, capped** (`CORROBORATION_STEP`/`CORROBORATION_CAP`). The
  bonus is now keyed to distinct `source` strings among ruling-eligible evidence (not tiers), with
  `single_source` items excluded and a hard ceiling — a curated feed can no longer inflate a reading
  with many tiers or re-reported echoes. This also closes the ratchet's inflation vector; standing-
  authority *persistence* (a landed sanction does not un-happen) is intentional and kept.

## 5.7 The forecast demoted to a function; the record promoted to the product (2026-09-17)

**The decision.** The engine makes three claims at once, and only one of them needs the forward
test. Separating them was the whole job:

| claim | rests on | needs the freeze? |
|---|---|---|
| the **record** — these rulings/statutes/actions happened, at these tiers | three-adversary intake, tier stamping | no |
| the **mapping** — given that, these controls are required | Model Rules + `FAULT_ANNOTATIONS`; GOVERN gates on *is-it-required*, never on economics | no |
| the **economics** — acting pays for *this* firm | the AI Profit Paradox identity, on the firm's own inputs | no |
| the **ranking** — these lines, in this order, are where the next ruling lands | precision 0.10 / lift 1.59 in-sample; 0/0 out | **yes, and that is the point** |

So the ranking is demoted from a public claim to a **function**: an internal sort order for
attention across eleven controls a firm cannot stand up at once. It stays graded (§5.3), and it
is reported as a column, not as the thesis. The firm-facing claim is the other three, all of
which are checkable today.

**Why the ranking is the weakest of the four.** Three order-2 rulings exist on the whole record.
`LEAD_DAYS` is 90. The freeze expects 0-2 genuinely-new post-freeze rulings per quarter, so a
defensible verdict needs 6-12 months to reach an n that means anything. A claim whose validation
horizon outruns a typical engagement cannot anchor one.

**The milestone method** (`radar/milestones.py`, `history/milestones.jsonl`). Grade a denser
outcome variable instead: **antecedents**. Most binding events do not arrive unannounced. A rule
has a proposal, a comment period, a bar committee, a first court, and those are dated tier-stamped
facts already on the record. The grader reports two numbers:

- **Lead time** — antecedent to binding event. Today: median **601 days** across 9 landed pairs
  (min 192d, max 2161d). This is a fact about the past, verifiable by reading the record, and it
  is where the 12-18 months a firm actually needs to stand up a control comes from.
- **Blindside rate** — of standing-authority events, how many had no earlier item on their line.
  Today **0.12** (10/83), reported as a **floor, not an exact rate**: the scan runs over a feed
  curated with hindsight, so it reads low by construction. This is the honest measure of what a
  forecast is *for*. A low blindside rate means the record is the product.

The grader also surfaces **actionable now** — controls with a precursor on the record and no
binding event yet (today: `insurance`, `agentic`). That list is a statement about the record, not
a forecast. The Colorado row is kept deliberately as the counter-case: an antecedent does not
guarantee a binding event. Enacted February, repealed May.

**Two corpora, one engine** (`radar/live.py`). A frozen experiment and a firm engagement want
opposite things from the same corpus. The experiment can only prove anything if its inputs never
move; the advisory answers a present-tense question and wants a current record. The fork:

| consumer | corpus | refreshed? |
|---|---|---|
| the experiment | `sources/feed.jsonl` + `sources/harvested.jsonl` | **never** |
| the advisory | the above **+** `sources/feed_live.jsonl` + `sources/harvested_live.jsonl` | freely |

The advisory corpus is a superset, so the two cannot drift apart in what they share. `live._guard`
refuses to write a frozen input, `tests/test_live.py` asserts the fingerprint survives a live
build, and CI runs `freeze.py --check` (read-only) so a violation **fails the run** instead of
landing as a quiet bot commit. `harvested.jsonl` was a latent leak before this: it is a hashed
input, `load_corpus` merges it, and CI auto-committed it. Live harvesting now targets
`harvested_live.jsonl` and the frozen store stays empty.

**Fixed in passing.** `advisory.PRICING_DIR` was `HERE.parents[2]`, one level above the repos, so
the legal-sim import failed silently and the Order-4 gate ran on mirror constants while still
printing `legal-sim/pricing` as its source. Now `parents[1]`, and the mirror path reports itself
as a mirror (`PRICING_SOURCE`, `pricing_model_imported`).

**Open issue found while wiring this: GOVERN did not discriminate.** With
`MANDATORY_PRESSURE = MANDATORY_ADOPTION = 7.0`, the advisory returned `stand-up-now` for **10 of
11** lines on every demo posture, while DEPLOY discriminated cleanly. Same "calls almost
everything" failure that forced `CALL_THRESHOLD` up to 8.0 in `calibration.py`. Fixed below.

## 5.8 GOVERN rebuilt — duty vs norm, an evidence floor, and a sequence (2026-09-17)

The diagnosis, from the decision surface rather than from taste:

```
line                press  adopt   via              n_ruling  n_adopt
verification          9.7    8.2   pressure+adoption      20        3
confidentiality       9.4    6.9   pressure               13        1
insurance             6.5    8.1   adoption                0        2
agentic               7.2    6.3   pressure                1        2
```

Four defects, each fixed:

**1. The threshold was stale and self-contradicting.** `MANDATORY_PRESSURE = 7.0`, and its own
comment called it "the radar call threshold," while `calibration.CALL_THRESHOLD` had moved to 8.0.
Two modules disagreeing about what "the law moved" means is a bug, not a tuning choice. The
constant is now **imported** from the calibration layer, so there is one source.

**2. The two triggers were fused.** `required = pressure OR adoption` gave `confidentiality` (13
ruling items, a binding rule) and `insurance` (zero ruling items, two CNA renewal questionnaires)
the identical `stand-up-now`. A duty is comply-or-risk-sanction; a norm is compete-or-lose-work.
They are now separate flags with separate verdicts:

| | ready | not ready |
|---|---|---|
| **mandated** (pressure ≥ `CALL_THRESHOLD`) | `stand-up-now` | `build-capacity-first` |
| **expected** (adoption ≥ 7.0) | `match-the-market` | `build-capacity-first` |

A duty outranks a norm when both trip. `MANDATED_PRESSURE` is calibrated; `EXPECTED_ADOPTION` is
**not** — the backtest grades order-2 rulings only, so no threshold for the adoption lane has been
earned. Reported as `thresholds.expected_adoption_calibrated: false` rather than passed off as
measured.

**3. Opportunity leaked into GOVERN.** `actionable = required or opportune` meant a line that was
explicitly *not* required could still get a GOVERN verdict, with a note reading "required/open."
Opportunity answers "would this pay," which is the DEPLOY question. GOVERN is now gated on duty
and norm only; opportunity still opens DEPLOY.

**4. No evidence floor.** `agentic` was called `stand-up-now` off a **single** ruling item. Verdicts
now carry a `confidence`: `supported` at `MIN_DRIVING_EVIDENCE = 3` or more items in the lane
driving the call, else `thin`. Thin does not suppress the verdict, it labels it — the firm sees
"mandated, thin evidence," which is true.

**Result:** `stand-up-now` 6 · `match-the-market` 2 · `no-mandate` 3, from 10 · 1. The two norms
(`insurance`, `benchmark`) both read **thin**, which is the honest description of two CNA forms and
two ruling items.

**Sequencing.** Ten rows all saying "do this" is a list, not direction. GOVERN now emits a `plan`,
ordered by tier (duty-unmet → duty → norm-unmet → norm → none), then confidence, then **shortest
measured lead first** — a line whose antecedents historically bind in 192 days gives less warning
than one binding in 907, so it starts first. Lines with no milestone of their own are reported with
the record median but deliberately **not ranked** by it; an invented 601 would place them against
lines that were actually measured.

**Closing a gap between artifacts.** `agentic` computed to `no-mandate` while `milestones.py`
simultaneously flagged it "actionable now" (AI LEAD Act proposed, nothing bound). Both true, but a
firm reading only one would draw opposite conclusions. Rows now carry a `precursor` field, and a
`no-mandate` row with a precursor says so: *not required yet, but a precursor is on the record*.

**Fixed in passing:** the frontend `GOV_ACCENT` / `DEP_ACCENT` maps referenced `--emerald`,
`--indigo`, and `--sky`, none of which exist in `globals.css`, so every verdict pill had been
rendering with no accent. Mapped onto tokens that do exist.

## 5.9 The adoption lane was reading the ruling lane (2026-09-17, re-freeze)

`EXPECTED_ADOPTION = 7.0` was an uncalibrated prior, and the obvious fix was to calibrate it.
Checking whether there was anything to calibrate against found a structural defect instead.

**The defect.** G5 (2026-09-14) isolated the ruling meter: a T3 market action must never lift
the ruling grade. The symmetric case was never fixed — a ruling was lifting the **adoption**
grade. Measured on the real feed: **10 ruling-eligible items were scoring in both lanes across
6 lines** (`verification`, `disclosure`, `confidentiality`, `competence`, `convergence`,
`benchmark`). `verification`'s adoption of 8.2 was built entirely from ABA 512, CA COPRAC, and
the federal expert-exclusion order, all three of which were already driving its pressure of
9.7. The two meters were correlated by construction, which is why `pressure OR adoption`
barely discriminated.

> **Measure this correctly.** `fl["evidence"]` is the *provenance* list and holds **18** items
> that also appear in adoption. Only 10 of those were ruling-eligible. Counting provenance
> overstates the defect by nearly double, and it was the first number reported before being
> checked. Audit with `ruling_eligible`, or `tier in RULING_TIERS`.

**The fix.** `ADOPTION_EXCLUDED = {"process_mandate"}` — a rule mandating a process is a duty,
and the ruling lane already owns it. Scoped to ruling-eligible items only: a T3/T4
`process_mandate` keeps its adoption weight, because adoption is the only lane that can count
it and dropping it would lose evidence rather than de-duplicate it. `agentic`'s AI AGENT Act
row (T3) is that case, and survives.

**Then the lane had almost nothing in it.** With rule-derived evidence removed, every line
falls back to its seed except `insurance` (8.1, two CNA items). The entire market-adoption
meter had independent evidence on one line, from one carrier — which is what
`evidence-methodology.md` predicted when it called the absence of an insurer mandate the most
valuable finding in the research.

**So the threshold stopped being the point.** A control is table stakes when an actor who can
*withhold* something requires it. `LEVERAGE_CLASSES = {"insurer", "procurement", "deployment"}`:
the insurer withholds coverage, the client withholds the engagement, the court withholds the
docket. `cert` and below are things people wrote down — nobody yet loses anything over a
benchmark existing. The norm verdict now requires at least one leverage item, which makes
`EXPECTED_ADOPTION` a tiebreak and the leverage test the actual claim. `benchmark` (adoption
6.4, `cert` only) drops out of the norm category, correctly.

**The threshold was then retired outright** — see §5.10.

## 5.10 `EXPECTED_ADOPTION` retired; leverage replaces it (2026-09-17)

The prior section left the number in place as a tiebreak. Trying to calibrate it showed there
was nothing to calibrate, and the number was doing less than it appeared to.

**It was nearly inert.** With leverage gating in place, sweeping `EXPECTED_ADOPTION` across its
whole range 0 to 10 moved at most two verdicts:

```
threshold   govern verdict counts
        0   {build-capacity-first: 8, no-mandate: 3}
        6   {build-capacity-first: 7, no-mandate: 4}   <-- fees drops out
      8.5   {build-capacity-first: 6, no-mandate: 5}   <-- insurance drops out
       10   {build-capacity-first: 6, no-mandate: 5}
```

Only two lines are reachable by it at all (`insurance` 8.1, `fees` 5.3). Every other line is
`expected=False` at any value, because it has no leverage evidence.

**There was nothing to fit to.** Three order-3 rows exist. CNA insurance is a genuine leverage
event. "Verification duty extended to expert work product" is a court broadening a duty, which
is pressure wearing an adoption label. "AI AGENT Act codifies scope-limited authorization" is
described in the feed itself as a proposal that *would* require it, so it has not landed. One
clean event. And the meter it thresholded rested on **three items across eleven lines**, two of
them the same carrier. A threshold over three datapoints is not a parameter.

**So the gate became a countable fact instead of a fitted number.** A control is table stakes
when a **named actor who can withhold something** requires it. That lives in
`history/leverage.jsonl` (`radar/leverage.py`), a labeling layer like `resolutions.jsonl` and
`milestones.jsonl`, so it never writes a frozen input.

```json
{"date": "2026-06-15", "match": "CNA adds AI-governance questionnaires", "fault_line": "insurance",
 "actor": "CNA", "actor_class": "insurer", "withheld": "coverage",
 "requirement": "AI-governance questionnaire required at malpractice renewal"}
```

The record's entire leverage evidence base is **one requirement**, from one carrier. Rows with
`"requirement": null` are reviewed-and-excluded and kept as findings — the `fees` pricing-trend
row is there, because a trend in client demand is not a named actor requiring anything.

**Leverage is firm-relative, so the firm states it.** `FirmPosture` gained `carriers` and
`key_clients`. If *your* carrier requires a control it is table stakes *for you*, and a carrier
requiring it in the trade press is only a proxy for that. Same category as `pricing` and
`enablement`: a stated fact needing no calibration. The verdict is the same either way; the
strength of the claim is not:

| firm | verdict | confidence | note |
|---|---|---|---|
| names no actors | `match-the-market` | thin | "CNA requires it of firms like yours" |
| carrier is CNA | `match-the-market` | **supported** | "CNA — an actor you named — requires it: match it or lose coverage" |

`EXPECTED_ADOPTION` remains in `advisory.py` as a displayed number with
`expected_adoption_gates_anything: false` in the output, so nobody later mistakes it for
something earned.

**Bug found while testing this:** `actor_match` guarded neither side against empty, and
`"" in "cna"` is `True`, so a leverage row with no actor would have matched every named carrier
and quietly upgraded a generic market signal to "your own carrier requires this." Caught by the
test suite, fixed, and the guard is now asserted for `None`, `""`, and whitespace on both sides.

## 5.11 The pages follow the claim (2026-09-17)

Demoting the forecast changed what the product *is*, and the pages still led with the old thing.
Sections 5.7 through 5.10 reframed copy; this restructures the presentation.

**What was stale.** `/radar` opened with "Where legal-AI rules are heading — and what to build
before they land", which is the retired claim verbatim. The sidebar nav group holding all five
radar pages was labelled **`Predict`**, and the KB page's eyebrow read "Predict · Knowledge
base". And the new output had no home: the milestone panel sat wedged inside
`docs/radar/index.html` between the queue and the calibration panels, while the sequenced plan
lived only on `/radar/advisory`, so a reader arriving at `/radar` got the meters and had to
already know to visit two other pages.

**The restructure.** Both the public page (`build.py`) and the in-app page now lead with the
firm-facing material and push the meters below the fold as **scoring provenance**:

| | section | firm-dependent? |
|---|---|---|
| 1 | **What the record already requires** — controls at or above the flag threshold, ruling evidence only | no |
| 2 | **Actionable now** — precursor on the record, nothing bound | no |
| 3 | **How much warning the record gave** — median antecedent-to-binding lead, with n | no |
| 4 | The evidence per fault line | no |
| 5 | Scoring provenance — the L1 / L2 / L3 / E / S meters | no |
| 6 | Calibration — what none of it claims | no |

The **sequenced plan** stays on `/radar/advisory`, because sequencing needs firm readiness and
that is the only page carrying a posture. `/radar` says so and links there under "Sequence for
your firm". The split is deliberate: the generic page shows what is required of everyone, the
advisory page orders it for one firm, and neither duplicates the other's logic.

**One drift guard.** The in-app page first hardcoded `8.0` for the duty threshold. It now fetches
`call_threshold` from `calibration.json`, because a hardcoded threshold whose comment claimed to
be the calibrated one is precisely the bug fixed in §5.8, and it should not get a second chance
in TypeScript.

**Renames:** nav group `Predict` → `Fault lines`; KB eyebrow `Predict · Knowledge base` →
`Fault lines · Knowledge base`. `milestones.json` is now published beside `data.json` to both
`docs/radar/` and `frontend/public/radar/` so the two pages cannot drift, and CI commits it.

**Re-freeze.** `ADOPTION_EXCLUDED` and the `score.py` gate are frozen inputs, so this was a
deliberate re-freeze, which is the documented exception. `KNOBS_FROZEN_AT` moved 2026-09-15 →
2026-09-17 and the fingerprint was regenerated. The cost was near zero because the
out-of-sample column was **0/0** and the freeze was two days old; the same change in December
would have discarded three months of the one experiment that cannot be re-run. That timing,
not the severity of the bug, is the argument for having done it now.

## 7. Design direction — the planned three-part confluence model

The scope decision in §2 plus the history in §5 point to this build-out. The forecast core
stays tight and gradeable; the advisory layer grows; the firm sim becomes its internal-model
leg.

**In Layer A (forecast core):**
- **Per-line causal driver typing.** Each fault line declares its dominant trigger
  (capability-driven, deployment-driven, market-driven) so capability→rule, deployment→rule,
  and rule→gate-on-adoption arrows are representable and separately gradeable, instead of one
  enforced order. Closes G3 and G4.
- **Isolate the L2 meter** to actual ruling/regulatory evidence so the backtest grades ruling
  prediction, not a grab-bag. Closes G5.

**In Layer B (advisory / operationalization):**
- **An enablement axis.** A distinct meter (or meter set) for firm-deployable tools and their
  adoption — fed by the content named in §5.2: tool-landscape consolidation, firm-wide
  deployment and reorg, client/procurement pull, maturity of the proven use-cases, and
  delivery-channel changes. It is clearly labeled as enablement, never mixed into the rule
  forecast or its calibration.
- **Two readouts, not one.**
  - *Compliance alarm* (on Layer A): governance × adoption — the current defensive queue,
    kept as "when the fix becomes mandatory."
  - *Opportunity envelope* (Layer B): supply × enablement, reported where governance is
    permissive — where to build value before it is required. This is the confluence readout
    that a legal-AI consultancy operationalizes against. Replaces the current single queue.

**In Layer C (firm-transformation sim, the internal-model leg):**
- **Radar → sim feed-forward: grounded world shocks.** The sim already applies market phase and
  shocks (`WorldEngine`). Feed it the radar's grounded external conditions as boundary inputs —
  which fault lines are at horizon X, which controls are becoming mandatory, the enablement
  trajectory (tool consolidation, insurer gating, procurement pull) — so the sim's world is
  constrained by the deterministic evidence side instead of hand-configured.
- **Sim → Layer B feed-back: which levers move *this* firm, and whether its economics permit
  acting.** The radar's agenda is a list of controls/opportunities at horizon X; the sim
  returns, for a given `FirmSignature`, which to pull, in what order, and — via the AI Profit
  Paradox — whether this firm's pricing lets the AI be a net win rather than a net loss. Layer B
  cannot compute the economic condition on its own; the sim supplies it.
- **Seam as the differentiator.** The codifiable-vs-tacit seam finding (legal-sim) explains why
  two firms facing the same ruling diverge: it is not noise, it is which seam the tool attacks.
  The radar treats tools uniformly; the sim models the seam that decides whether a control pays.
- **Guardrails.** Part C is never graded as a call and never enters calibration. Psych-profile
  and mock-LLM priors stay low-confidence and human-reviewed. Its output is a confidence-intervaled
  what-if, never a fabricated point forecast of a specific firm's outcome.
- **Altitude for the advisory sell.** law-firm-sim is the consulting product (a specific real
  organization's twin); legal-sim is the abstract insight (which seam, which lever in general).

### Roadmap markers

- **Shipped (v1):** 11 fault lines, tier model, deterministic weighted scorer, calibration +
  run artifacts, seeded feed, scheduled regen. See §4.
- **Existing, separate (Part C):** law-firm-sim and legal-sim (shared engine, `FirmSignature`,
  Monte Carlo/Bayesian, AI Profit Paradox).
- **Shipped 2026-09-07 (seam, two-verdict):** `radar/advisory.py` maps the four effect-orders into a
  **GOVERN/DEPLOY** verdict per fault line — GOVERN (stand up the control: required + readiness,
  economics never block it) and DEPLOY (put AI on the work: pricing + capture + market E). Composes
  the radar landscape (Orders 1 + 3) with firm posture (Orders 2 + 4). See §8.
- **Shipped 2026-09-07 (enablement axis E):** fourth per-fault-line meter (market deployability),
  non-decaying enable evidence on six lines, and E as a hard gate on the DEPLOY axis only. See §9.
- **Shipped 2026-09-07 (curation-first attribution):** each item evidences only the fault lines in
  its curated `fault_lines` field (signal match = fallback), killing signal-word leakage between
  lanes.
- **Shipped 2026-09-07 (app):** /radar shows E; new /radar/advisory renders GOVERN/DEPLOY from
  precomputed posture JSONs. Build-verified.
- **Planned:** isolate the L2 ruling meter to actual rulings (G5); the two-readout build (compliance
  alarm = governance × adoption, opportunity envelope = supply × enablement); deeper Part C
  integration (world-shock feed-forward to the sim). Recorded here first so the canonical intent
  outpaces the implementation.

---

## 8. How the effects fit together: the advisory seam

Everything this system tracks can be grouped into four layers of effect, running from what the
technology can do down to whether one specific firm can act on it. The seam stacks the four and,
for each issue the radar watches, answers the two questions a firm actually faces separately:
**stand up the control** (governance) and **put AI on the work** (economics).

No single layer is enough on its own. A firm that only watches the technology over-invests. A
firm that only watches the rulings under-prepares. The right call for any one organization lives
where all four layers meet, and the seam is what finds that meeting point.

### The four layers, as four questions

Think of each issue the radar tracks as needing the same four questions answered. Two are true
for everyone in the market. Two are true only for your firm.

| # | The question | True for whom | What answers it |
|---|---|---|---|
| 1 | Can AI actually do this yet? | everyone | public evidence of capability |
| 2 | Can *we* actually run it? | only your firm | your tools, skills, data |
| 3 | Is the law moving here? | everyone | public rulings and adoption pressure |
| 4 | Does it pay for *us* to act? | only your firm | your pricing economics |

Layers 1 and 3 are public facts, measured from real rulings and evidence. Layers 2 and 4 are
private facts about one firm. The system never guesses the private ones from public data, because
whether a single firm can deploy and profit is not something anyone can predict from the outside.
You supply them. That is the honesty boundary: it reports what is knowable and asks you for the
rest.

### Two questions, not one

Each issue forces two different decisions, and the seam keeps them separate rather than mashing
them into one answer. The mistake the single-verdict model made was treating "stand up this
control" and "put AI on this work" as the same call — which told a ready firm to delay required
governance because the AI economics were not there yet. They are different questions, answered by
different evidence, for different people.

**GOVERN — stand up the control?**
Is this control required of us now, and can we meet it? Driven by whether the law has moved (or the
fix is becoming table stakes) and by the firm's readiness. The AI economics never block it: a
required competence program or data-governance is not deferred because the billable hour makes AI
less profitable. Answers: **stand up now · build capacity first · no mandate yet**.

**DEPLOY — put AI on the work?**
Is this the moment to put AI on the underlying work the control governs? Driven by how the firm
bills (the pricing paradox) and whether the AI can capture the work yet (the seam). A rule
requiring verification does not force you to scale AI. Answers: **deploy now · fix pricing first ·
defer · watch**. Only asked where AI does the billable work; market-driven controls (insure your
governance, unify your operating model) have no deploy question.

The two answers land in different hands. GOVERN feeds the compliance calendar — what we must stand
up, and by when. DEPLOY feeds the build-and-buy budget — where AI effort and tooling actually pays.
Keeping them separate is what stops the engine from giving a ready firm bad advice about required
governance.

### One issue, two firms, two answers each

Take verification, the requirement that firms prove their AI work was checked. The law has already
moved, so both firms are required to stand the control up now.

An hourly firm is required to stand it up and is ready, so **GOVERN says stand up now** — nothing
about the billable hour lets you skip required verification. But running the deploy economics it
loses roughly $124,000 per lawyer a year from putting AI to work, because the hours it saves are
hours it stops billing. **DEPLOY says fix pricing first** — stand up the control, but don't scale
the AI that feeds it until pricing changes.

A fixed-fee firm is also required and ready, so **GOVERN says stand up now** too. And its deploy
economics are the mirror image: it gains roughly $7,900 per lawyer a year, because the hours AI
saves are pure cost taken out. **DEPLOY says deploy now.**

Same rule, same governance answer for both — a requirement is a requirement regardless of billing.
What differs is the deploy answer, because layer 4 is the one only the firm can answer. That split
is the whole reason the seam exists: governance is not the economics, and the engine no longer
conflates them.

### What it does not do

The seam predicts nothing new. It reuses the pricing identity the firm simulation already proved
(the AI Profit Paradox), so the seam and the simulation cannot disagree. It imports nothing from
the forecast core, so it can never corrupt the backtest that keeps the forecast credible. Its
output is advice for a human to act on, never a claim about what will happen.

Running it for a firm:

```bash
python radar/advisory.py --pricing fixed_fee --enablement 7 --name "Your firm"
```

## 9. Part B spec — the market enablement axis (E)

The structural gap §5.2 proved: the radar measures what the rules demand (governance) and what
the AI can do (capability), but not whether the market actually lets a firm stand the fix up.
This spec defines that missing axis. It is Part B, so it is evidence-traced (T-market), never
graded as a call, and it never touches Part A's meters or calibration.

**Status 2026-09-07:** implemented in the scorer — attribution is now curation-first (each item
evidences the fault lines in its curated `fault_lines`, signal matching only as a fallback), which
fixes signal-word leakage between lanes. The E meter lives in `fault_lines.py` (`ENABLE_WEIGHTS`,
`ENABLE_SEEDS`) and `score.py`, surfaced in `data.json`, the CLI table, and the radar page detail
line. Calibration is unaffected (E is Part B).

**Enable evidence is ingested and persistent.** `enable` evidence now covers six lines (feed = 30
items): benchmark (standard, Stanford), insurance (playbook, CNA), competence (standard, PLI),
agentic (deploy_scale, A&O+Harvey), verification (deploy_scale, e-discovery/contract-review
maturity), confidentiality (provider, no-training/data-governance). Enable evidence deliberately does
NOT decay — unlike ruling/adoption momentum, "the market can supply X" is a persistent fact once a
tool is proven at scale or a standard exists (same logic as capability). Readings now differentiate:
benchmark 8.3, verification 8.1, competence 7.4, insurance 6.9, confidentiality 6.7, agentic 6.5,
disclosure 6.0 (seed), others at seed.

**E is a hard gate on the deploy axis.** The seam's deploy verdict cannot be deploy-now unless
market enablement E ≥ 6.0; if E is below that, deploy becomes defer ("the market can't supply mature
tooling for this yet"). The gate sits on the DEPLOY axis only — it never touches GOVERN, so a
required control is never deferred on market-supply grounds. Currently all deploy-eligible lines have
E ≥ 6 by evidence or seed, so the gate is latent-but-correct: it binds only if a control's market
supply drops below threshold.

### Why it is separate from L3 adoption

L3 adoption and enablement are the demand and supply halves of the same question, and L3 currently
conflates them. L3 asks "is the *control* becoming required or table stakes" (insurers gating,
process mandates, procurement requiring it). Enablement asks "even if it is required, can a firm
actually *build it* with what the market offers right now" (a usable tool, a certification to aim
at, a provider to buy from, a playbook to follow). A control can be mandatory yet undeployable:
supervision rules for agents arrived before mature agent tooling. Splitting them lets the system
say "required AND you can build it" versus "required but nothing good exists to build with yet."

### The E meter

A fourth reading per fault line, 0–10, the same shape as the others.

- **Question:** can a firm that wants to stand this control up do it, from what the market
  offers today?
- **Scoring:** same saturated-curve machinery as adoption — a seed lifted by weighted `enable`
  evidence, corroborated across distinct enable classes, decayed like market momentum (standing
  T1/T2 exempt; reuse the existing half-life). Divisor ≈ 2.0 (adoption's).
- **Sources:** feed items carry a new class key `enable`. A single item can be `market` (L3), and
  `enable`, and `capability` — they are three different questions about the same event.

### Enable signal classes and weights

| class | weight | a market item proving the ecosystem can support building the control now |
|---|---|---|
| deploy_scale | 1.00 | operational at production scale at major firms (firm-wide deployment, usage data) |
| standard | 0.90 | a concrete certification / benchmark / minimum standard to build against (bar cert, NERVE) |
| playbook | 0.75 | a defined process / playbook / insurer form a firm can follow (not just a duty) |
| provider | 0.65 | a maturing vendor/provider category to buy from (dedicated tools, capital, M&A) |
| client_pull | 0.55 | clients / RFPs actively requiring the tool or control |
| launch | 0.30 | a tool / offer launched but not yet proven at scale |
| pundit | 0.02 | narrative only |

Analyst seed proposal (baseline ecosystem readiness before evidence): verification 6.5,
benchmark 7.0 (NERVE exists), disclosure 6.0, competence 6.0, confidentiality 5.5, insurance 5.0,
convergence 4.0, fees 3.5, agentic 3.5 (immature tooling), judicial_analytics 3.0,
vendor_liability 3.0.

### How E reaches the seam (Order 2's market half)

Order 2 in the advisory seam is two-sided: the *market* can support it (E, public) **and** the
*firm* can run it (private readiness). E is read from each fault line's meter and carried on the
row (`orders.2_market_enable`).

**E is a hard gate on the deploy axis only.** The deploy verdict cannot be deploy-now unless
market enablement E ≥ 6.0; below that it defers ("the market can't supply mature tooling for this
yet"). E belongs on the deploy axis, never the govern axis — govern is requirement + readiness and
must never be deferred on market-supply grounds. (An early attempt gated E before enable evidence
existed, so seed noise wrongly deferred required governance; that is why the gate is deploy-only and
waited for real enable evidence.) With enable evidence now ingested and non-decaying, E readings are
evidence-backed, and the deploy gate is honest: currently every deploy-eligible line is ≥ 6 by
evidence or seed, so it is latent-but-correct rather than firing on noise.

### Evidence backlog (what to ingest once the axis ships)

From §5.2: tool-landscape consolidation and funding (Harvey, Clio/vLex, TR/Casetext) as
`provider`; firm-wide deployment at scale (one global firm on 5,000 lawyers) as `deploy_scale`;
procurement RFP pull (~8%→34%) as `client_pull`; e-discovery / contract-review maturity as
`deploy_scale` on the relevant lines; any bar adoption of a tool certification or benchmark as
`standard`; ABS / sandbox licensing as `playbook`/`provider` on the delivery-channel side. These
are not fault lines themselves (recorded as scope calls in §5.2); they are enable evidence the E
meter reads.

### Guardrail

E is T-market: an evidence-weighted trajectory, never a backtested call, never in Part A's
calibration. It cannot decide "the rules will move"; it only reports "the means to comply exist
and are maturing." The two-readout build (§7) becomes meaningful once E exists: compliance alarm =
governance × adoption, opportunity envelope = capability × E.

## 10. Part B spec — the software-capability lane (S), the vendor trajectory

Enablement is not one axis; it is a three-layer supply stack, and the engine only modeled two of
the layers until now:

| Layer | Name | Question | Engine lane |
|---|---|---|---|
| 1 | AI capability | can the underlying AI do the legal thing | L1 `capability` (shipped) |
| 2 | Software capability | can legal-AI software vendors build a tool for it | **S `software` (this spec)** |
| 3 | Method | does the playbook/standard exist to adopt it | E `enable` (shipped) |

Each layer enables the next — model → software → method → firm — and each has different drivers and
different clocks. Collapsing them into one "enablement" bucket loses the difference between "the
model can do it but no vendor has built it" and "vendors built it but no method exists to adopt
it": different predictions, different lead times.

### What S is

A forward momentum signal for the middle layer: what vendors are **enabled to build next**, driven
by the movements behind the current state. Evidence class `software`, weights:

- `capital` 1.00 — a funding round / valuation step that funds future build
- `model_access` 0.90 — a frontier model unlock vendors can now build on
- `acquisition` 0.85 — M&A consolidating build capacity / incumbency
- `regulatory_room` 0.70 — a law/ruling opening or constraining what vendors may ship
- `ship` 0.55 — a vendor shipping a major product

S **decays** (`SOFTWARE_HALF_LIFE = 120` days): it is momentum, so a round two years ago does not
signal today's build — unlike E, which is a persistent supply fact and does not decay.

### Calibration — S is graded against its own milestones

A forward signal that cannot be graded is just a vibe. So S has its own point-in-time backtest
(`calibration.software_backtest`), replaying the engine 90 days before each dated build milestone
(funding round, acquisition, shipment) using only prior evidence. Threshold 6.0.

**First result (4 milestones, 2023-2026): 1/4, and each miss is a different, defensible limit.**

| Milestone | Result | What it reveals |
|---|---|---|
| Harvey → \$8B (Nov 2025) | **called** | escalating capital (\$3B→\$5B) pointed at the decacorn — the one clean momentum continuation |
| Agentic tools ship at scale (Apr 2025) | missed | the funding that drove it landed ~2 months before the ship; S tracks *funding* momentum, not shipment timing |
| Clio acquires vLex (Nov 2025) | missed | M&A into a new area (practice-management) is a direction shift, not a continuation |
| TR acquires Casetext (Aug 2023) | missed | first-of-kind — the trajectory had not started, nothing prior to predict from |

The honest finding: **S predicts trajectory *continuation* (who keeps building faster), and it is
transparent that *origination* (first vendor into an area) and *direction shift* (M&A into new
territory) are outside its reach.** That boundary is the calibration doing its job — the same
first-of-kind honesty the L1 capability lane already carries.

### Forward tweaks (what the backtest says to tune next)

1. **Grade S against funding/momentum milestones, not shipments.** The agentic "miss" was a
   shipment graded against a funding signal — re-anchor the milestone set on the capital events
   (the thing S actually tracks) and the lane reports its real hit rate.
2. **Do not chase origination or direction shifts.** First-of-kind and M&A-into-new-territory are
   low-signal by nature; flag them separately rather than folding them into a momentum call.
3. **Extend the milestone set forward.** As the vendor build continues, each new dated funding /
   acquisition / ship event is another resolution the lane earns or misses, which is the ongoing
   calibration loop the whole engine is built on.

---

*Canonical. Edit this file, not the generated `docs/radar/` output, when the design changes.*
