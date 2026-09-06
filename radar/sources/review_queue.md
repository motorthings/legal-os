# Review Queue — found, but not confidently admitted

Items surfaced during the pass that I would **not** append without more checking. The
admission gate is the point: each of these is either unverifiable, a prediction dressed
as fact, a near-duplicate, or scope-drift.

## 1. "Mississippi is the first state to mandate AI-specific CLE" — CONFLICTING, do not admit

- **What's claimed:** Mississippi became the first state requiring mandatory AI CLE for
  all attorneys (per `aivortex.io/legal/guides/cle-ai-competence-requirements`).
- **Problem:** A second source (`irys.ai/legal-ai-rules/mississippi`, "verified as of
  June 2026") says Mississippi has **no** AI- or technology-specific CLE requirement.
  Direct contradiction on a verifiable point.
- **Disposition:** Quarantine. This is exactly the failure the gate exists to catch —
  a plausible-sounding SEO claim that is either stale, misreported, or fabricated.
  Do not admit until confirmed against the Mississippi Bar's CLE page directly.
- **What it cost us:** The competence fault line gets New Jersey (well-corroborated)
  instead, which is fine.

## 2. Whiting v. City of Athens (6th Cir., 2026) — real but imprecise date + already dense

- **What:** "Stiffest Rule 38 penalty available" — attorneys to reimburse appellee fees,
  pay double costs, and $15,000 each in punitive sanctions for 24+ fake citations.
- **Problem:** (a) day-of-month not confirmable from the reporting I pulled;
  (b) the feed already carries the Q1 2026 "$145K wave" item (T3) *and* the record
  Oregon/appellate-fine note, so this risks volume-over-authority on the same fault line.
- **Disposition:** Candidate for next pass. Pull the primary opinion from CourtListener
  (T1) to nail the date, then admit as a distinct ruling (it is — 6th Cir., Rule 38).

## 3. "Architectural Defect Doctrine" / Farris-CoCounsel asymmetry commentary — punditry, not a ruling

- **What:** Scholarship (aistandardofcare.com, scilit.com) arguing for strict product
  liability against legal-AI vendors and predicting a "Farris-pattern verdict within five
  years."
- **Problem:** Rule 5 — this is prediction and advocacy, not a holding. The *underlying
  Farris ruling* (attorney removed, denied compensation) is a real L2 fact, but the
  "vendor should be liable" framing is a T4/T5 opinion and must not smuggle in as evidence
  that vendor_liability has moved.
- **Disposition:** Reject as evidence. If added, only as T5/pundit with `conflict:true`
  (author advocates a specific liability regime). The EU PLD + AI LEAD Act items carry
  the real vendor_liability weight instead.

## 4. Raine v. OpenAI (wrongful-death / product liability) — real, but out of scope

- **What:** Federal court allowed a wrongful-death claim against OpenAI to proceed;
  framed as product liability.
- **Problem:** Consumer-AI harm, not legal-practice AI. It doesn't touch a fault line in
  this taxonomy (no lawyer duty stressed). Admit would be scope-drift.
- **Disposition:** Quarantine for scope. Note in coverage_notes as a general-AI vendor
  liability signal if the radar ever widens beyond legal-practice duties.

## 5. Thomson Reuters "90% accurate" rebuttal to Stanford — vendor self-defense

- **What:** TR publicly contested the Stanford finding, claiming ~90% accuracy internally.
- **Problem:** Vendor contradicting a study about its own product → `conflict:true`,
  T5, ~1/100 weight. The Stanford study already carries the signal; adding the rebuttal
  adds a conflicted echo, not independent evidence.
- **Disposition:** Reject. The Stanford "Hallucination-Free?" study (already in feed as
  the 34%/17% item) is the primary; this is the vendor's response and adds noise.

## 6. California COPRAC Practical Guidance (Nov 2023) — near-duplicate

- **Problem:** The feed already carries "California updated Practical Guidance for
  Generative AI" (2026-05-14). The original Nov 2023 COPRAC would be a near-duplicate of
  the same bar's guidance.
- **Disposition:** Drop. One row per authority per event; the updated item stands.
