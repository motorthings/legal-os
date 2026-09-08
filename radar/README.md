# Fault-Line Radar

> **Canonical design doc:** `docs/radar-design.md` is the single source of truth for the
> engine's design intent, as-built v1, known gaps, and planned confluence model. This README
> is the run + backlog log.

Forecasts *where the next legal-AI rulings land* by tracking **fault lines** — the
places where an AI capability stresses an existing legal duty. It scores each fault
line's pressure from evidence weighted by **source authority, not volume**, so the
forecast can't be captured by whoever publishes most (usually vendors).

Lives in legal-os as a Layer 1/2 governance-monitoring function. Honors the repo
pillars: deterministic score replay, explainable (every score cites its evidence
and weight), evidence over eloquence.

## Run it

```bash
python radar/run.py            # one pass: score curated feed -> regenerate page
python radar/run.py --watch 30 # local background: repeat every 30 min
python radar/run.py --ingest   # also run harvester + admission gate (phase 2)
```

**Advisory seam** (`advisory.py` — returns TWO verdicts per fault line: GOVERN = stand up the
control, DEPLOY = put AI on the work; E gates DEPLOY, never GOVERN. Design: `docs/radar-design.md`
§8. Four effect-orders mapped against firm posture.)

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
  amplified by **corroboration across independent tiers**. Ten vendor posts can't
  outweigh one ruling.
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
      lead), pressure time-series snapshots, and an immutable per-run audit artifact
      (`history/runs/`) capturing knobs, evidence, weights, math, predictions, backtest.
      The engine earns trust by being graded, not by asserting the future.

### Most valuable next (do these first)
1. **Harvester + admission gate** (`ingest.py`) — allowlist-only fetch, then admit
   only on tier + relevance + novelty; quarantine the rest with a logged reason.
   The anti-noise layer. Appends to `feed.jsonl` in the existing schema.
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
8b. **Source-reliability tracking** — let a source earn effective weight above its
   tier floor by a proven track record (a vendor blog stays ~1/100 of an ABA opinion
   UNLESS its earlier posts kept presaging real rulings). Authority (tier) and
   reliability (earned) kept separate; reliability written by the calibration ledger,
   read by the scorer; capped below primary authority. One-directional learning loop.
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
