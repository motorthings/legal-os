# Radar Freeze — the forward-only experiment

The radar cannot prove it predicts from hindsight data. Every in-sample number —
recall, precision, lift, and the top-3 hit rate — is a measure of *how well the system
agrees with itself*, not *how well it predicts the future*, because the feed and the
"right answer" list were both written after the events happened.

So the radar is frozen. This is the experiment: don't touch the inputs, wait for rulings
nobody pre-selected, and see if the frozen system flags them early. That is the only
non-circular test, and it runs in the `out_of_sample` column of the calibration page.

## Freeze window

**2026-09-17 → 2026-12-17** (three months). Re-evaluate at the end; extend to 6–12
months if fewer than a handful of post-freeze rulings have landed (expect 0–2 in a
quarter).

**Re-frozen 2026-09-17, two days after the original 2026-09-15 freeze.** The adoption lane
was reading the same evidence twice: a rule-derived class (`process_mandate`) fed both the
ruling meter and the adoption meter, so 10 ruling-eligible items were scoring in both lanes
across 6 lines (`verification`, `disclosure`, `confidentiality`, `competence`, `convergence`,
`benchmark`). Any scoring change re-baselines the split, so the clock restarts from the change
date rather than being back-dated.

(When auditing this, count only **ruling-eligible** items. `fl["evidence"]` is a provenance
list and holds 18 items that also appear in adoption, but the T3/T4/T5 ones never moved the
ruling grade. Counting provenance overstates the defect by nearly double.)

The cost was close to zero and the timing was the whole argument for doing it now: the
out-of-sample column was **0/0** (no ruling dated after 2026-09-15 had landed), so two days
were discarded and no measurable call was lost. The same change in December would have
discarded three months of the only experiment that cannot be re-run. `KNOBS_FROZEN_AT` and
the fingerprint were both bumped deliberately, which is the documented exception, not a
violation.

## What is frozen — do not touch

| File | Why it matters |
|---|---|
| `radar/sources/feed.jsonl` | the evidence — editing it is hindsight |
| `radar/sources/harvested.jsonl` | same |
| `radar/fault_lines.py` | seeds, taxonomy, `KNOBS_FROZEN_AT` |
| `radar/score.py` | the scoring math (lift curve, divisors) |
| `radar/calibration.py` | `CALL_THRESHOLD` and the other knobs |

Changing any of these after the freeze makes the out-of-sample column void. The
fingerprint below proves whether that happened.

## What still moves — and must

- **`radar/history/resolutions.jsonl`** — this is the *ground truth*, not the evidence.
  When a genuinely new ruling lands (a real case/statute/action dated after 2026-09-17),
  **record it here in real time, as it happens.** Don't wait until December and write them
  all at once — that would re-introduce the hindsight you're trying to escape. Any ruling
  dated after `KNOBS_FROZEN_AT` is automatically graded `out_of_sample`.
- **The weekly CI** re-scores and regenerates the page. It adds no evidence, so the feed
  stays frozen on its own. Leave it alone.

## What to NOT do

- **Do not re-curate the frozen feed.** When the staleness climbs and the "Radar
  re-curation" GitHub issue fires, **ignore it.** Running `/refresh-radar` and admitting
  new evidence into `sources/feed.jsonl` is the one action that quietly un-freezes the
  feed. Staleness growing is the honest signal, not a bug.

  **Re-curating the LIVE corpus is fine and expected.** `sources/feed_live.jsonl` and
  `sources/harvested_live.jsonl` exist so a firm-facing engagement can keep a current
  record without touching the experiment. `live.py` never writes a frozen input and
  refuses to if asked. If you want fresh evidence for the advisory, that is the path:
  `RADAR_LIVE_FETCH=1 python radar/live.py --harvest`. Nothing on that path can move the
  fingerprint.
- **Do not edit seeds or knobs**, even to "improve" them. Every improvement is hindsight.
- **Do not bump `KNOBS_FROZEN_AT` to dodge a violation.** It marks the boundary. The one
  legitimate reason to bump it is a deliberate scoring change, and that has to be recorded
  with its cost — as the 2026-09-17 re-freeze above does. Never bump it because the
  fingerprint moved and you want the check to go green.

## The fingerprint — how to prove the freeze held

`history/freeze_fingerprint.txt` contains the current sha256:

```
66bc0d00f627fe7410b950f8de0bab9b1a0d862c54762d18e3f664da3ea4b185
```

To verify the freeze held (now, or in December):

```bash
cd radar && python freeze.py --check   # read-only; exits non-zero on a violation
```

Use `--check`, not the bare form: plain `freeze.py` REWRITES the baseline, so running it to
"verify" a freeze silently converts a violation into a clean-looking one. CI runs the
`--check` form and fails the build on a mismatch.

If it matches, the out-of-sample calls were made with exactly the frozen inputs — no
retro-fitting. If it differs, someone touched a frozen file and the out-of-sample column
is void; the experiment restarts from a new freeze.

## How to read the result in December

Ignore recall/precision/lift/top-3 — they are all still retrodiction. Look at the single
`out_of_sample` row on the calibration page:

| Out-of-sample | What it means |
|---|---|
| **0/0** | nothing landed yet — the freeze just extends |
| **1/1** (or more) | a post-freeze ruling landed on the frozen top-3 — the ranking earned its first real hit |
| **0/1** | a post-freeze ruling landed and was NOT in the top-3 — a real, honest miss; the first evidence of where the ranking is actually wrong |

One real hit does more than every in-sample number ever will: it moves the ranking from
"sounds like good governance anyway" to "predicts what to build for." A miss is equally
valuable — it tells you the honest boundary of the radar's skill.

## Why three months is a start, not a verdict

AI-legal rulings land steadily, but "truly-new, post-freeze, on-a-fault-line" rulings in
one quarter may be 0–2. Three months starts the clock and catches the first honest data
point; it does not prove the ranking. A defensible verdict needs 6–12 months and roughly
4–8 post-freeze rulings.
