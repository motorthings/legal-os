# Harbor Labs and AESOP — Organic Alignment

*Written 2026-09-11. Companion to `design.md`. This is the evidence that the roadmap generator is not a pitch reverse-engineered from Harbor's service page, plus the honest accounting of where the two models diverge.*

---

## 1. Why this document exists

The risk in any alignment story is that it reads as flattery: read the company's website, build a thing that matches their diagram, present the match as insight.

The defense is dates and specificity. What follows separates what was built **before** contact with Harbor's published framework from what was shaped **after**, and names the places the two models genuinely disagree.

## 2. The timeline

| Date | Event |
|---|---|
| 2026-05-17 or earlier | AESOP lifecycle exists. Earliest repo history is a merge commit; the lifecycle predates it |
| 2026-08 | Harbor Deploy launches |
| 2026-08-25 | Harbor's Operationalizing AI report published |
| 2026-09-01 | Eudia / Harbor partnership announced |
| 2026-09-05 | Radar lands in `legal-os` |
| 2026-09-07 | `radar/advisory.py` (the four-effect-order model) |
| 2026-09-11 | This design work begins |

**The honest split:**

- **Organic convergence.** The AESOP lifecycle (Discover → Design → Build → Evaluate → Repair → Track) predates Harbor's published framework by roughly three months. Same arc, arrived at independently.
- **Deliberate alignment.** The radar and `advisory.py` postdate Harbor Deploy. The roadmap generator is explicitly shaped to Harbor's Advise deliverable list.

Do not blur those. The first is evidence of thinking. The second is evidence of listening. Both are worth claiming, and claiming them separately is what keeps the story credible under a cold follow-up.

## 3. Layer one — the lifecycle

| AESOP (built) | Harbor (published) |
|---|---|
| Discover | Advise: readiness assessment, use-case identification, workflow analysis |
| Design | Advise: technology and model evaluation, deployment roadmap, business case |
| Build | Implement: solution design, model selection, system and data integration |
| Operationalize | Implement: workflow redesign, training, change enablement, production launch |
| Evaluate | Manage: adoption and performance monitoring |
| Repair | Manage: workflow optimization |
| Track | Manage: continuous improvement planning |

Seven stages against three bands. The correspondence is close enough to be meaningful and loose enough to be real.

## 4. Layer two — the operating model

Harbor's five-capability Enterprise AI Operating Model, against the AESOP tenets:

| Harbor's capability | AESOP equivalent |
|---|---|
| AI Strategy: define outcomes before buying | Metrics before build; problems before solutions |
| Measure what matters | Certification bands, deterministic scoring, eval harness |
| Invest with intention | Portfolio prioritization with a weighted score and a veto rule |
| Change behavior, not just technology | Working agreement, adoption plan with its own metrics |
| Build trust at the speed of innovation | Human-edit feedback loop, drift monitoring, go/no-go gates |

Also pre-contact. Two independent alignments is a pattern, not a coincidence.

## 5. Layer three — the artifact

This is the deliberate one. Harbor's Advise deliverable list, against what the generator produces:

| Harbor's Advise deliverable | Generator status |
|---|---|
| Readiness assessment | **Input.** Consumes the maturity assessment and firm posture |
| Use-case identification and prioritization | **Output** |
| Workflow and process analysis | **Input.** Consumes the stack inventory |
| Technology and model evaluation | **Output**, with per-claim provenance tiers |
| Governance and risk frameworks | **Output.** Driven by `advisory` GOVERN verdicts |
| Deployment roadmap | **Output** |
| Business case and success measures | **Output**, via the Profit Paradox |
| Operating model design | **Output**, as the roadmap's Manage band |

Items two, four, six and seven are generated. Items one, three, five and eight are consumed. The taxonomy is Harbor's, not invented.

## 6. Where the models genuinely diverge

A perfect match would be suspicious. These are the real differences, and they are where the conversation gets interesting.

### 6.1 Granularity

Harbor's model is three bands, sized for a service organization to describe itself. AESOP's is seven stages with gates between them.

Seven stages means seven places to stop and check. **The gates are the product, not the stages.** Harbor's three-band model describes the work. The seven-stage model instruments it.

### 6.2 The loop

Harbor's Advise → Implement → Manage reads as sequential. Work gets advised, then implemented, then managed.

AESOP's Evaluate → Repair → Track is a loop. And the radar instruments the market half of it, which Harbor's framework leaves unaddressed.

Harbor sells "model and platform evaluation" as an episode, appearing once in Advise and once again in Manage. Nothing in the published framework says *when* to re-evaluate. The radar does: fault-line trends and lead indicators give every platform decision a trigger condition.

**This is the one capability a general consultancy cannot replicate**, because it requires a calibrated forecast of the legal-AI landscape feeding a specific firm's plan.

### 6.3 Service model versus machine

Harbor's framework describes what good practitioners do. The generator computes what should happen.

These are complementary, not competing. The framework is the description. The machine is the implementation. Harbor does not need a machine that replaces consultants. It needs one that makes their judgment explicit, replayable, and inheritable, so a doubling team does not depend on any individual's memory.

## 7. The asymmetry, stated plainly

The strongest version of the alignment is not "we match." It is:

> **The machine exists. The knowledge does not have a home.**

Harbor's page says the enablement teams have run AI adoption, training and change management inside law firms, including Magic Circle firms. The knowledge is real and it is the asset. What it lacks is a structured place to live and a way to be deployed against a specific client's facts.

The generator has the opposite problem. A working machine with generic knowledge and no proprietary base to draw on.

Neither is a product alone. That asymmetry is the reason to build this inside Harbor rather than anywhere else, and it is the honest answer to "why not just build it yourself."

## 8. The sayable version

Order matters. Leading with praise and then showing work reads as flattery. Showing work and then discovering the match reads as convergence.

> "The thing I kept running into is firms buying AI and not being able to tell whether it worked. So I built the lifecycle to fix that: discover, design, build, evaluate, repair, track. Gates between each stage, measurement before rollout, a re-evaluation loop on the back end.
>
> Then I read your Advise, Implement, Manage and realized I'd built the same arc, just more granular. Which I think is the right kind of agreement, because it means we're solving the same problem and you've got the piece I don't. I built the machine. You have the knowledge that goes in it. That's the part I can't build, and the part you can't deploy."

The landing is the last two sentences. Not "look how aligned we are." It is: the socket and the plug, neither worth much alone.

## 9. Delivery caution

Two constraints, both from existing prep:

**Justin's hire test is community, not competence** (`Justin-Hectus-Research-and-Approach.md:14-19`). A framework-alignment analysis is a competence move. Right content for the other interviewers, wrong opening for him. With Justin, land the human version first, then let the mapping be backup.

**Do not open the Harvey tension in a PM round** (`Harbor-Questions-by-Role.md:70`). The partner-and-competitor dynamic is the liveliest version of section 6.2 and it belongs with the person selling the business model, not in a delivery or program conversation.

## 10. Claim discipline

What survives a cold follow-up:

- **Claim:** AESOP's lifecycle predates Harbor's published framework, and the repo history shows it.
- **Claim:** The radar is the only instrument that closes the Advise-to-Manage evaluation loop, and it is a solo build with a squashed commit history.
- **Claim:** The generator is designed against Harbor's Advise deliverable list, deliberately.
- **Do not claim:** that the generator has been run against real firm data. It has not. The firms are synthetic and labeled as such.
- **Do not claim:** that Harbor's knowledge base exists in structured form today. That is the premise of the work, not its result.

---

## Appendix — Sources

- `Harbor-Master-Interview-Brief.md:16` — the Advise / Implement / Manage framework
- `Harbor-Master-Interview-Brief.md:53-58` — the five-capability Enterprise AI Operating Model
- Harbor Deploy service page — the Advise / Implement / Manage deliverable lists
- `aesop` repo history, first commit 2026-05-17
- `docs/firm/design.md` — the generator this alignment describes
- `docs/radar/radar-master-reference.md` — the forecast instrument
