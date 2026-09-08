# Which part of the simulation is most defensible

A note on where to plant the flag. Simulating a whole firm's AI adoption is a big
lift and easy to attack. The question here is narrower: which single component of
the sim survives a hostile reviewer, and is therefore the right thing to focus on.

## Recommendation: narrow to the Pricing lever (the AI Profit Paradox)

It's the one finding that survives, because it doesn't actually depend on the
simulation being right.

Why it's the most defensible:

- It reduces to an accounting identity, not emergent agent behavior. Under hourly
  billing, revenue = hours × rate; AI cuts the hours, so it cuts revenue unless you
  refill the capacity. Under fixed fee, the same hour reduction drops straight to
  margin. Same tool, same people, same adoption, opposite sign. A skeptic can't
  dismiss it with "your agents are made up" — the result holds even if you throw the
  multi-agent layer away.
- The metrics carry `[SURVEY]` / `[INFERRED]` provenance tags
  (`legal-sim/src/models/metrics.py`) anchored to real AmLaw figures. The input
  assumptions are auditable, not vibes.
- It's counterintuitive enough to be interesting, but mechanical enough to be
  unarguable. That combination is what "defensible" means.

## Strong second: the comp/adoption negative result

"Restructuring origination moves adoption 40→49.6% but does not move outcomes."
Negative results are harder to attack than positive ones — nobody accuses you of
wishful modeling when the model refuses to give you the win you'd want.
`validate.py` already isolates this as Signal 6.

## What not to lead with

The Track A vs B contest (organic discovery vs planned design). That's the big lift.
It's the most emergent output — it depends on agent psychology, calibration, and
behavioral dynamics all being correct at once. The most impressive claim and the
most fragile. Keep it as illustration; don't stake the whole thing's credibility on it.

## How to harden the pricing finding

1. Pull the pricing calculation out of the full sim and show it as a closed-form
   model first — prove the paradox arithmetically, then show the simulation
   reproducing it. The sim becomes corroboration, not the load-bearing argument.
2. Run the sensitivity sweep on the two or three inputs it depends on (rate,
   hour-reduction %, capacity-refill rate) and show the sign flip is robust across
   the plausible range, not a knife-edge.
3. Frame the seam analysis (codifiable vs tacit) as the scope qualifier on the
   pricing claim — it tells you which work AI can actually compress, which bounds
   the paradox. A clean, defensible pairing.
</content>
</invoke>
