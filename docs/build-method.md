# Build Method — how this work gets made

**Status:** canonical source of truth for the *method* (the how). For the *design* of the
prediction engine itself (the what), see `docs/radar-design.md`.
**Owner:** Charlie Fuller. **Last updated:** 2026-09-07.
**Siblings:** `docs/radar-design.md` (engine design), `radar/README.md` (run + backlog log),
the presentation of this method at `diagrams/legal/legal-os-radar-buildlog.html`.

---

## The one-line version

Find a problem worth solving, get under it until the real thing that's broken is exposed, and
then build toward the answer with whatever tools are in front of me. The Fault-Line Radar is the
worked example. The method is the point, and it is the same lifecycle AESOP runs teams through:
**Discover → Design → Build → Evaluate → Repair → Track.**

## The origin move

The work starts with one shift in stance: from *"wouldn't it be nice if we could do X"* to
*"how would I build it."* The wish waits for a permission that never arrives; the plan starts the
moment you ask it. Everything below is that stance made repeatable.

Two rules govern the front of the process:

- **Why before how.** Get the problem and its root cause right first, then let the solution
  follow. Never the reverse.
- **No feasibility filter yet.** "It might not be possible" is a later question. Early on it only
  shrinks what you let yourself imagine.

---

## The six stages

### 1. Discover — keep the problem big
Refuse to shrink the problem. Dig for the root, not the symptom, and keep feasibility out of the
room. For the radar, the problem was that legal AI is moving faster than anyone can track, and the
effects that decide how a firm operates sit two, three, four orders downstream, out where almost
nobody has visibility.

**Do not assume the effects run in a tidy line.** The orders (capability, ruling, adoption, and
what a firm can afford to act on) develop on partly independent clocks and co-mingle. Some fault
lines are pure market or regulatory reactions with no capability driver at all; some run backwards,
where a firm deploying a tool in a filing provokes the rule. That non-linearity, the variability in
how one order feeds the next, is the real thing to model. The honest system does not force a single
order onto every line; it lets each line carry the way its own effects actually move. (See
`radar-design.md` §G3/§G4: the strict `L1→L2→L3` cascade is a forced frame, and per-line causal
driver typing is the fix.)

### 2. Design — let the constraints pick the stack
Press the problem against the solution space until the real constraints fall out, because the
constraints are what choose the platform, the stack, and the tools. For the radar the constraints
were: deterministic and replayable, weighted by who sets the rules rather than by volume, gradeable
against what actually happened, and auditable after the fact. Those demands ruled out letting a
model freehand the forecast and pointed at plain scored code. With the constraints set, the
remaining design forks resolve fast (see the decision record in `radar-design.md`).

### 3. Build — AI for leverage, the logic stays mine
Pair with AI to draft and refactor fast, but keep the scoring itself as deterministic code that can
be read, rerun, and defended line by line. The tool accelerates the build; it does not own the
judgment.

### 4. Evaluate — grade against reality, then say what broke
Score the thing against what actually happened, replayed point-in-time (90 days out for the radar),
and leave the misses in. A panel that only shows hits is marketing, not calibration. The engine
earns trust by being scored, not by sounding sure.

### 5. Repair — a logged miss is the next work item
A miss is not something to bury; it is the next thing to build, and it points straight at the fix.
The evaluation names the weak spot, and the next pass closes it against a scored baseline so you can
tell whether the repair actually moved the number.

### 6. Track — explainable, auditable, traceable
Log every part of every run: the inputs, the reasoning, and the output. The whole run audits end to
end so a problem is caught while it is still just an issue. Every run is hashed and replayable, every
score carries the evidence and math that produced it, and every call traces back to its sources, so
a prediction made today can be explained, audited, and traced months from now. The same record is
where improvements come from: once you can watch how the tool actually gets used and how other people
push on it, the gaps surface on their own and the loop reopens with real evidence instead of a guess.

---

## Cross-cutting: governance is woven through, not a stage

The three legal-os pillars hold at every stage, not at the end:

- **Explainable** — the chain of reasoning is visible; each score cites the specific signal.
- **Auditable** — full input/reasoning/output capture, deterministic score replay, immutable
  structured logs.
- **Traceable** — who, when, what, why; every override logged; every artifact exportable.

## Positioning

The lawyers own the doctrine. This method brings the modeling, the calibration, and the discipline
of checking the work and asking where it's wrong. A forecast no one can read is a forecast no one can
trust, so clarity is treated as part of correctness, not a finish at the end.
