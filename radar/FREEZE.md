# Radar Freeze — the forward-only experiment

The radar cannot prove it predicts from hindsight data. Every in-sample number —
recall, precision, lift, and the top-3 hit rate — is a measure of *how well the system
agrees with itself*, not *how well it predicts the future*, because the feed and the
"right answer" list were both written after the events happened.

So the radar is frozen. This is the experiment: don't touch the inputs, wait for rulings
nobody pre-selected, and see if the frozen system flags them early. That is the only
non-circular test, and it runs in the `out_of_sample` column of the calibration page.

## Freeze window

**2026-09-15 → 2026-12-15** (three months). Re-evaluate at the end; extend to 6–12
months if fewer than a handful of post-freeze rulings have landed (expect 0–2 in a
quarter).

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
  When a genuinely new ruling lands (a real case/statute/action dated after 2026-09-15),
  **record it here in real time, as it happens.** Don't wait until December and write them
  all at once — that would re-introduce the hindsight you're trying to escape. Any ruling
  dated after `KNOBS_FROZEN_AT` is automatically graded `out_of_sample`.
- **The weekly CI** re-scores and regenerates the page. It adds no evidence, so the feed
  stays frozen on its own. Leave it alone.

## What to NOT do

- **Do not re-curate.** When the staleness climbs and the "Radar re-curation" GitHub issue
  fires, **ignore it.** Running `/refresh-radar` and admitting new evidence is the one
  action that quietly un-freezes the feed. Staleness growing is the honest signal, not a bug.
- **Do not edit seeds or knobs**, even to "improve" them. Every improvement is hindsight.
- **Do not bump `KNOBS_FROZEN_AT`.** It marks the boundary; moving it moves the goalposts.

## The fingerprint — how to prove the freeze held

`history/freeze_fingerprint.txt` contains the current sha256:

```
2104e6361b2c4fc7bdffb3ae872a2e4020867c18287506b00bd129a527ce656a
```

To verify the freeze held (now, or in December):

```bash
cd radar && python freeze.py   # prints the current fingerprint
diff <(python freeze.py) history/freeze_fingerprint.txt && echo "FREEZE HELD"
```

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
