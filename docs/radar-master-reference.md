# Fault-Line Radar — Master Reference

**Status:** the single entry point to the radar. Read this top to bottom for the whole picture;
the detailed docs stay canonical for their slice and are listed at the bottom.
**Owner:** Charlie Fuller. **Last updated:** 2026-09-08.

---

## What the radar is

The Fault-Line Radar forecasts where legal AI is headed so someone can decide where to build and
govern next. It does not predict the future in the "here is the date" sense. It tracks **fault
lines** — the places where a new AI capability rubs against an existing legal duty — and measures
how much pressure is building on each one, weighted by who is doing the pushing.

The big idea is simple: a court ruling, a funding round, and a new model release are three
different kinds of event, and you should not weigh them the same. The radar's whole job is to
keep them straight.

## The three parts

The radar is really three tools with three different promises, so no part can claim more than it
can back up.

| Part | Question | Promise |
|---|---|---|
| **A. Forecast core** | Will a court, bar, or law move on this? | Graded against what actually happened |
| **B. Advisory layer** | What should a firm build and buy next? | Evidence-traced advice, never a "prediction" |
| **C. Firm simulation** | Can *this* firm afford to act? | A what-if model, never a forecast |

Part A earns trust by being graded. Part B turns Part A's readouts into build-and-buy advice. Part
C asks whether one specific firm's economics even let it act. They fit together, but they are kept
apart so a grade from Part A never gets muddied by an opinion from Part B.

Part C's headline finding is the **AI Profit Paradox**: on hourly billing, more AI is a net loss
(the hours saved are hours you stop charging); on fixed-fee pricing, the same AI is a net win.
Whether a firm can act on the radar's advice depends on how it bills, and only Part C tests that.

## The eleven fault lines

Each line is a place where AI stresses a legal duty. The radar scores pressure on each one, 0–10.

| Fault line | What it tracks | The fix (control) | Horizon |
|---|---|---|---|
| insurance | Insurers gate who can use AI | Make governance an insurable artifact | near |
| disclosure | AI-use disclosure becomes standard | Verify by default with an audit trail | near |
| verification | "A human checked it" stops being enough | Documented verification + trace logs | near-mid |
| confidentiality | Client data at risk in AI tools | Map data flows + get vendor attestations | near |
| convergence | Conflicting rules force one standard | One operating model, strictest standard | near |
| agentic | Autonomous agents reopen supervision / UPL | Human-decides gates + scope limits | mid |
| benchmark | A tool-certification standard emerges | A benchmark as a compliance tool (NERVE) | mid |
| competence | Competence becomes a governance duty | Firm-wide training program | mid |
| judicial_analytics | Predicting judges gets regulated | Guardrailed strategy sim, no judge-prediction | mid |
| fees | The billable hour cracks under AI | Measure value delivered, not hours | mid-far |
| vendor_liability | Liability starts to shift to vendors | Document tool provenance | far |

## How it scores

**Authority over volume.** Every piece of evidence is stamped with a tier when it enters, and that
tier decides its weight, not how many people repeated it:

| Tier | What it is | Weight |
|---|---|---|
| T1 | Court ruling, statute | 1.00 |
| T2 | Bar opinion, regulatory guidance | 0.80 |
| T3 | Empirical study, institution | 0.60 |
| T4 | Commentary, trade press | 0.35 |
| T5 | Vendor marketing | 0.008 |

A vendor blog carries about a hundredth of an ABA opinion. Ten vendor posts cannot outweigh one
ruling.

**Five meters per fault line.** Each line carries its own readout on five separate questions:

- **L1 capability** — can the AI do the thing yet (the supply signal)
- **L2 ruling** — will the law move on it (the governance signal)
- **L3 adoption** — is the fix becoming table stakes (the market signal)
- **E enablement** — can a firm actually build the fix with what the market sells today
- **S software** — are legal-AI vendors enabled to build the tool (the forward momentum signal)

L1, S, and E are the three layers of a supply stack: model → software → method → firm. Keeping them
separate is what stops "the model can do it" from being mistaken for "a vendor shipped it" or "a
firm adopted it."

**Two-sided scoring.** Most meters only go up. The L2 ruling meter now goes both ways: an item can
carry a `negative_fault_lines` flag, meaning it argues *against* a line (a court holding that
disclosure is *not* required), and it drags the meter down instead of up. That matters for honesty —
a forecast that can only ever say "more pressure" cannot notice when the rules reverse course.

**Trajectory flags.** Every capital/M&A event is labeled continuation (more of the same),
origination (first-of-a-kind), or direction shift (M&A into new territory). The software meter can
only predict continuation, so an origination is flagged honestly rather than scored as if it were
predictable.

## How evidence gets in

A fact does not enter the feed just because someone found it. It enters because it survived.

1. **Split the question** into angles and search them in parallel, including one angle that
   deliberately looks for where the story is wrong.
2. **Try to kill every claim.** Three independent reviewers each try to prove each claim false. It
   survives only if two of the three cannot break it.
3. **Rank by who said it** (the tier system above), stamped at intake, never guessed later.
4. **Note the kind of change** (continuation / origination / direction shift).
5. **Refuse to invent.** If a date or amount cannot be verified, the honest answer is "we found
   nothing," not a guessed number.

This is the step that caught real mistakes: a court rule that only one source mentioned, a
"disqualification" that was actually a reprimand, a claim about two vendors no source supported.

The full story is in `docs/evidence-methodology.md`.

## The six evidence streams

The feed (76 items) draws from six streams, each feeding a different meter:

1. **Vendor capital & M&A** — funding rounds and acquisitions (Harvey to $11B, Legora to $5.55B,
   Thomson Reuters/Casetext, Clio/vLex, Spellbook, Robin, EvenUp, Luminance, Paxton, Leya). Feeds
   the S software meter.
2. **Model access** — frontier model unlocks (Claude long-context, computer-use, agentic tools).
   Feeds L1 capability.
3. **Regulatory room** — laws and rulings that widen or narrow what vendors can build (EU AI Act
   deferral, the anti-splitting rule). Feeds S and vendor_liability.
4. **Method / playbook** — insurer governance (CNA), competency frameworks, LPL coverage changes.
   Feeds E enablement.
5. **Docket feed** — the actual sanctions and bar referrals for AI misuse (Mata, Manasco, Whiting,
   and the first order naming a specific AI product). Feeds L2 ruling.
6. **Certification watch** — the emergence of a named tool standard (ABA Op 512, California's
   proposed rules). Feeds E and benchmark.

The full cited, dated inventory is in `docs/radar-market-inventory.md` (people) and
`docs/radar-market-inventory.jsonl` (machine).

## How to run it

```bash
cd legal-os/radar
/opt/homebrew/bin/python3 run.py            # one pass: score feed -> regenerate page
/opt/homebrew/bin/python3 run.py --watch 30 # repeat every 30 min
/opt/homebrew/bin/python3 score.py          # quick CLI table of all meters
/opt/homebrew/bin/python3 advisory.py --pricing fixed_fee --enablement 7 --name "Firm"
```

Output lands in `docs/radar/index.html` + `data.json` + `kb.json`, regenerated weekly by CI.

## What's next

The order, recorded in `docs/radar-upgrade-roadmap.md`:

1. **Docket feed** (done) — the leading enforcement signal.
2. **Certification watch** (done) — the origination the model is waiting for.
3. **Consultancy stream** — deliberately skipped; it lags enforcement and adds little.

The single open signal to watch: no insurer has yet made a certified AI tool a condition of
malpractice coverage, and no bar has adopted a named benchmark. When one does, that is the event
that flips the method layer from voluntary to enforceable.

## Where the deep detail lives

| If you want… | Read |
|---|---|
| The full engine design, scope, and calibration | `docs/radar-design.md` |
| The process method (how work gets made) | `docs/build-method.md` |
| How evidence is found and verified | `docs/evidence-methodology.md` |
| What to research next, and why | `docs/radar-upgrade-roadmap.md` |
| The full cited evidence (dated, tiered) | `docs/radar-market-inventory.md` / `.jsonl` |
| Run commands and the backlog log | `radar/README.md` |
