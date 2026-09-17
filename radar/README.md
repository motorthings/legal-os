# Fault-Line Radar

> **Canonical design doc:** `docs/radar/radar-design.md` is the single source of truth for the
> engine's design intent, as-built v1, known gaps, and planned confluence model. This README
> is the run + backlog log.

Maps **fault lines** — the places where an AI capability stresses an existing legal duty —
and ranks them by what the record already shows, weighted by **source authority, not
volume**, so a reading can't be captured by whoever publishes most (usually vendors).

**What the ranking is for.** Eleven controls are on the board and a firm cannot stand all
of them up at once, so the ordering is a sort for attention. It is graded on its own
(`calibration.py`) and is *not* a public claim about which ruling lands next. The
firm-facing claim is narrower and checkable: **most binding events have an antecedent on
the record, and the median lead time from antecedent to binding event is ~20 months**
(`milestones.py`). That is a fact about the past, verifiable by reading the record, and it
requires no prediction to act on.

### What the pages lead with

Both the public page (`docs/radar/index.html`) and the in-app `/radar` lead with the firm-facing
output rather than the meters (§5.11): **what the record already requires** → **actionable now** →
**how much warning it gave** → the evidence per line → then the meters, demoted to *scoring
provenance* alongside the calibration honesty layer.

The **sequenced plan** lives on `/radar/advisory`, because ordering needs a firm posture. `/radar`
shows what is required of everyone and links there for the ordering.

### Two corpora, one engine

| consumer | corpus | refreshed? |
|---|---|---|
| the frozen experiment (`FREEZE.md`) | `sources/feed.jsonl` + `sources/harvested.jsonl` | **never** |
| the advisory (`advisory.py`) | the above **+** `sources/feed_live.jsonl` + `sources/harvested_live.jsonl` | freely |

The advisory answers a present-tense question, so it wants a current record. The
experiment can only prove anything if its inputs never move. `live.py` builds the
advisory corpus as a superset of the frozen one and refuses to write into it, so
re-curating for a firm engagement cannot void the out-of-sample column.

```bash
python radar/live.py                 # build the live landscape (docs/radar/live.json)
RADAR_LIVE_FETCH=1 python radar/live.py --harvest   # harvest, into the LIVE store only
python radar/milestones.py           # lead time + actionable-now + blindside rate
```

Lives in legal-os as a Layer 1/2 governance-monitoring function. Honors the repo
pillars: deterministic score replay, explainable (every score cites its evidence
and weight), evidence over eloquence.

## Run it

```bash
python radar/run.py            # one pass: score curated feed -> regenerate page
python radar/run.py --watch 30 # local background: repeat every 30 min
python radar/run.py --ingest   # also run harvester + admission gate (phase 2)

# Live harvesting is OFF unless explicitly enabled (no surprise outbound calls):
python radar/harvest_preview.py                   # preflight + preview a live run (writes nothing)
RADAR_LIVE_FETCH=1 python radar/run.py --ingest   # fetch allowlisted sources for real
# Full procedure + rollback: docs/radar/harvest-runbook.md
```

**Advisory seam** (`advisory.py` — returns TWO verdicts per fault line: GOVERN = stand up the
control, DEPLOY = put AI on the work; E gates DEPLOY, never GOVERN. Design: `docs/radar/radar-design.md`
§8, and §5.8 for the duty/norm rebuild. Four effect-orders mapped against firm posture.)

GOVERN separates a **duty** (the law moved — comply or risk sanction) from a **market norm**
(table stakes — compete or lose work); remedies differ, so the verdicts do too. Verdicts:
`stand-up-now` (duty, ready) · `build-capacity-first` (duty or norm the firm can't meet yet) ·
`match-the-market` (norm, ready) · `no-mandate`. Calls resting on thin evidence are marked
**thin**. Output includes a `plan`: the order to work them in, duties first and shortest
measured lead first.

A norm requires a **named actor who can withhold something** to require the control, not a high
adoption score (`leverage.py`, `history/leverage.jsonl` — §5.10). `EXPECTED_ADOPTION` is retired
from the gate and `expected_adoption_gates_anything: false` records that. Name the firm's own
leverage actors to get the firm-relative read:

```bash
python radar/advisory.py --pricing fixed_fee --carrier CNA --carrier Chubb --enablement 7
python radar/leverage.py     # what leverage is on the record, and what was reviewed out
```

```bash
python radar/advisory.py --pricing fixed_fee --enablement 7 --name "Your firm"  # GOVERN + DEPLOY
python radar/advisory.py --pricing hourly  --refill 0.15 --enablement 4          # hourly case
```

The seam also powers the in-app view: `build.py` writes demo postures to `frontend/public/radar/advisory/`
(rendered at `/radar/advisory`).

Output: `docs/radar/index.html` (self-contained, GitHub Pages serves it) +
`docs/radar/data.json`. CI regenerates weekly via `.github/workflows/radar.yml`.

## How scoring works (v1, shippable)

- Each item in `sources/feed.jsonl` carries a **tier** (T1 binding … T5 vendor),
  and optional `empirical` / `conflict` flags.
- Weight = tier weight × conflict discount × empirical boost × recency decay.
  Standing authority (T1/T2) never decays out.
- A fault line's pressure = seed thesis lifted by summed weighted evidence,
  amplified by **corroboration across independent sources** (distinct `source`
  strings, `single_source` items excluded, hard-capped). Ten vendor posts can't
  outweigh one ruling, and a curated feed can't inflate a reading with echoes.
- **Ruling-lane isolation (G5):** only ruling/regulatory evidence (`RULING_TIERS`
  T1/T2, or a per-item `ruling` override) lifts the L2 ruling meter. Market,
  commentary, and vendor items stay on the line as provenance but cannot move the
  ruling grade (they feed the adoption/capability/software lanes instead).
- **Negative evidence** (optional `negative_fault_lines` on an item): an item can
  COUNTER a line (e.g. a court holding disclosure is NOT required). Its weight is
  subtracted on the listed lines and added everywhere else; the ruling meter is
  two-sided, so counter-evidence drags pressure below the seed, not just offsets the
  lift. Provenance keeps the sign per item.
- All knobs live in `fault_lines.py` so scores replay exactly.

## Two curves (the mental model)

The radar tracks two coupled trajectories:

- **Capability** — what AI can actually do in legal work (agentic autonomy, error
  rates, model releases).
- **Governance** — what the rules currently allow.

**Fault lines are where the two diverge.** Capability inputs adjust *how fast* a gap
widens (horizon/likelihood). Ruling inputs are evidence the law is *reacting*. They
live in separate lanes so speculation never masquerades as legal fact (see backlog #3).

---

## Priority stack

### Shipped (v1 — the interview-ready core)
- [x] Fault-line taxonomy (10 lines, mapped to Model Rules)
- [x] Source-authority tier model + deterministic weighted scorer
- [x] Provenance-transparent static page + data.json
- [x] Seeded feed of real 2023-2026 rulings/opinions/actions
- [x] Scheduled regeneration (GitHub Actions) + local `--watch`
- [x] JSONL audit logging
- [x] **Calibration layer** (`calibration.py`) — point-in-time backtest (replay the
      engine N days before each ruling landed, using only prior evidence; "called?" +
      lead) plus pressure time-series snapshots. The engine earns trust by being graded,
      not by asserting the future.
      **Run artifacts are off by default (2026-09-17).** `python radar/run.py --trace`
      writes one to `history/runs/` when a replayable record of a specific run is wanted.
      Nothing in the repo reads them, and each re-embeds the full evidence set and weight
      math, so auto-writing one per run grew the directory by 4 MB in an afternoon. The
      writer in `calibration.py` is untouched — that file is a frozen input and this
      decision should not cost a re-freeze.
- [x] **Calibration honesty layer** (2026-09-14) — the recall backtest can't see false
      positives, so it's paired with: a **precision / base-rate grid** (precision,
      flag-rate, lift over a line×month grid — currently precision 0.10, lift 1.59); a
      **forward-only holdout** (`KNOBS_FROZEN_AT` splits retrodictive in-sample from a real
      out-of-sample track record); and a **seed ablation** (how much of each call rests on
      the analyst seed vs point-in-time evidence). See design doc §5.3.

### Most valuable next (do these first)
1. **Harvester + admission gate** (`ingest.py`) — allowlist-only fetch, then admit
   only on tier + relevance + novelty; quarantine the rest with a logged reason.
   The anti-noise layer. Appends to `feed.jsonl` in the existing schema.
   - [x] **Layer 0 — run-to-run dedup memory** (`dedup.py`, `ledger.py`). `admit()`
         consults the `SeenIndex` (canonical URL / content hash / citation-echo over
         the KB) and the `history/admissions.jsonl` ledger (what a prior run already
         judged) BEFORE evaluating a candidate — so a new run never re-admits a
         document the KB holds, never re-judges a quarantined one, and collapses
         echoes to the primary. Idempotent, deterministic, no deps, tested
         (`tests/test_dedup.py`, 7/7). The tier + signal-relevance gate is live.
   - [x] **Network fetchers** (`fetchers.py`, 2026-09-14) — allowlist-bound RSS/Atom
         (stdlib only), wired to `admit()`. **Offline by default** (no network unless
         `RADAR_LIVE_FETCH=1`); the allowlist is a hard boundary (non-allowlisted domains
         refused before any request); fetched rows land in `sources/harvested.jsonl`
         (marked `harvested: true`), never the curated feed.
   - [x] **Case-law curation** (`curate.py`, 2026-09-15) — court opinions are discovered
         semantically with **Descrybe** (`search_cases_by_concept`), not the harvester.
         `descrybe_to_items()` turns Descrybe results into feed-schema candidates, flags
         them against the KB (`in_kb`), and a human attributes `fault_lines` before
         admission. (CourtListener harvesting was tried and reverted — full opinion text
         drowns the AI signal in boilerplate; embeddings/rerank were the wrong tool.)
   - [ ] Layer 2 — Voyage/pgvector semantic dedup (`REL_MIN`/`DEDUP_MAX`) — re-scoped to
         dedup of curated items only, not discovery.
3. **Capability-trajectory lane** — ingest AI-capability forecasts as a **separate,
   clearly-labeled, low-weight signal** that shifts a fault line's horizon/likelihood,
   NOT its ruling evidence. Named inputs so far, and they are DIFFERENT epistemic
   objects, so tag them apart:
   - **AI 2027** (AI Futures Project) — *predictive* default-path capability scenario.
     Feeds the **capability curve**; near-mid horizon; moderate weight on
     capability-driven lines (agentic autonomy, verification).
   - **AI 2040 / Plan A** (same authors) — *normative advocacy* scenario ("what should
     happen": delay superintelligence, public research, compute tracking). NOT a
     capability prediction. Maps to the **governance curve** as a macro-policy
     scenario, mostly upstream of legal-practice rules. Very low weight, background
     context only; must never move a legal-practice pressure reading. Belongs in the
     scenario-branch feature (#9). Flag as advocacy (ideological conflict) the same way
     a vendor's self-promotion is flagged.

   Apply **horizon-graded weighting**: the further out, the lower the weight and the
   more it is confined to far-horizon lines. Prefer empirical capability signals
   (benchmark results, model releases, deployment data) over speculative timelines.
   Keep predictive capability, normative governance scenarios, and legal-ruling
   evidence in three separate lanes so neither hype nor advocacy masquerades as fact.

### Backlog (valuable, not urgent)
4. **Voyage indexing** — embed admitted docs with `voyage-law-2` into Supabase
   pgvector; powers admission-gate relevance + dedup and semantic retrieval.
5. **Forecast agent** — LLM pass over the indexed KB to draft fault-line narrative
   updates for human review (never auto-published; humans decide).
6. **Corroboration references** — keep deduped echoes as lightweight refs so
   re-reporting lifts corroboration without double-counting.
7. **Alerting** — notify on a fault line crossing a pressure threshold or a new T1
   item landing.
8. **Calibration-driven tuning** — adjust tier weights/knobs from the ledger's
   hit/miss record (with change log, so replay stays honest).
8b. **Source-reliability tracking** — [x] SHIPPED 2026-09-14 (`reliability.py`). A source
   earns a bounded weight multiplier by presaging real rulings; authority (tier) and
   reliability (earned) kept separate; effective weight capped below primary authority;
   one-directional (written by the learner, read by the scorer). **Honesty gate:** only
   OUT-OF-SAMPLE presages (rulings after `KNOBS_FROZEN_AT`) count, so it can't be tuned on
   hindsight — dormant (all multipliers 1.0) until forward rulings accrue. Design §5.5.
9. **Scenario branches** — model "if capability X arrives, these fault lines jump."
10. **Litigation strategy simulation** (separate product, extends `law-firm-sim`) —
    Monte Carlo over a litigation decision tree to find best cumulative strategies.
    DEFENSIBLE CORE: strategy stress-testing under uncertainty (settle/proceed, motion
    sequencing, downside tails). LANDMINE, guardrailed: judge/jury/opposing-counsel
    persona models as low-confidence, human-reviewed *priors only*, never determinative,
    never sold as "predict the judge." France criminalized judicial profiling (Art. 33);
    US direction is toward rules — this idea sits on the `judicial_analytics` fault line,
    so build the strategy engine, guardrail the persona modeling. Concept only for now.

### Explicitly out of scope (for now)
- Open-web crawling (allowlist only — noise control is the point).
- Predicting exact ruling text or firm dates.
- Auto-publishing agent output without human review.
