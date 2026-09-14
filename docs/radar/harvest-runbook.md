# Harvest runbook — first live run

How to run the Fault-Line Radar harvester live, safely, and how to undo it. Live
harvesting is **off by default**; nothing here happens unless you run it.

## What a live run does

Fetches the allowlisted sources (`fetchers.SOURCES`), turns each document into a
candidate, and runs the full admission gate. Admitted rows are appended to
`sources/harvested.jsonl` (never the hand-curated `sources/feed.jsonl`); every decision
is appended to `radar/history/admissions.jsonl`. The scorer then reads
`load_corpus()` = curated + harvested.

**Outbound calls:** three, to allowlisted domains only (`courtlistener.com`,
`lawnext.com`, `artificiallawyer.com`). A non-allowlisted domain is refused before any
request. A source that 4xx/5xx's or times out is skipped — never fatal.

## Step 0 — preflight (static, no network)

```bash
python radar/harvest_preview.py --offline      # preflight + built-in samples
```

Checks every configured source domain is allowlisted (an unlisted one would be silently
skipped and the run would harvest nothing) and that the store paths are writable. Exit
code is non-zero if preflight fails.

## Step 1 — preview the live run (no writes)

```bash
python radar/harvest_preview.py                # fetches for real, writes nothing
```

This is the actual network call, but the admission gate runs in **dry-run**: it shows
every candidate's decision and reason and touches nothing. Safe to run repeatedly.

Read the output:
- `would admit` — what the real run would add.
- `reason tally` — the distribution of decisions. Expect a **high quarantine rate**;
  that is the anti-noise gate working, not a bug (see Limitations).

## Step 2 — run it for real

```bash
RADAR_LIVE_FETCH=1 python radar/run.py --ingest
```

Writes the harvested store + ledger, rebuilds the page, refreshes reliability.

## Step 3 — check

```bash
python radar/calibration.py                    # backtest should be unchanged unless
                                               # harvested items landed on old fault lines
git status --short radar/sources radar/history # see exactly what was written
git diff --stat radar/sources/harvested.jsonl
```

## Rollback

Everything a run writes is isolated to two files, both git-tracked:

```bash
git checkout -- radar/sources/harvested.jsonl radar/history/admissions.jsonl
```

Or drop just one run's rows: every ledger row carries `"run": "run-<timestamp>Z"`, so
`grep -v '"run": "run-20260914T180000Z"' radar/history/admissions.jsonl` removes exactly
that run's decisions. The curated `feed.jsonl` is never touched by harvesting.

## Limitations to know before trusting a live run

1. **Relevance is signal-substring matching for harvested items.** Curated feed rows
   carry a hand-assigned `fault_lines` field; fetched rows do not (that is human work),
   so they fall back to matching the fault line's `signals` substrings against
   title+text. Expect many `no_fault_line_match` quarantines. The preview's reason tally
   is how you tune the signal vocabulary.
2. **The substring fallback is leaky by design.** `score.py` notes the real example:
   the signal `certif` matches `uncertified`. Curation exists to stop exactly this; the
   fallback cannot. Treat signal-matched admissions as lower-confidence than curated ones.
3. **CourtListener may require auth.** If the search endpoint returns 401/403, that
   source is skipped silently and only the RSS sources contribute. Check the preview's
   `candidates` count against the source count.
4. **A live run changes scores, which touches calibration honesty.** If harvested items
   land on lines with resolutions, the backtest numbers can move. That is expected —
   more evidence, different reading. It does **not** require bumping `KNOBS_FROZEN_AT`
   (the knobs didn't change; the evidence did) but the shift should be noted.
5. **First meaningful learning needs post-freeze rulings.** The Layer-3 reliability
   learner stays dormant until rulings dated after `KNOBS_FROZEN_AT` accrue. Harvesting
   alone does not wake it.
