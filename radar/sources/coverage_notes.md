# Coverage Notes — what's thin, and where the next pass digs

## Fault lines with no recent L3 (adoption) evidence

- **benchmark** — only L1/L2: the two Stanford studies. No *adoption* signal yet: no
  named certification standard adopted by a bar, insurer, or client, no minimum-competence
  benchmark being *required* anywhere. NERVE is internal to this project, not market
  evidence. **Next pass:** hunt for an actual "cert" event (a bar adopting a tool
  certification, an insurer requiring a specific benchmark, an RFP naming one).

- **judicial_analytics** — one item (France Art. 33, 2019). No US source at all this pass.
  The France ban is real but seven years old and non-US. **Next pass:** target US
  state/federal activity on judge analytics, outcome prediction, persona simulation, or
  jury research — this fault line is high-value (agentic strategy tools are cheapening
  named-actor prediction fast) and currently rests on a single foreign statute.

- **agentic** — only the AI AGENT Act (proposed, T3). No *actual* agentic-deployment
  ruling, UPL action, or supervision order found. **Next pass:** look for a real order
  involving an autonomous agent (not a drafting assistant), UPL-by-proxy scholarship that
  a court picked up, or an agent-scope mandate.

- **fees** — was empty; now carries Virginia LEO 1901 + Withers' fee context. Still thin:
  no *fee-transparency rule* or *value-based-billing mandate* with hard data. **Next pass:**
  the billable-hour→value shift is a second-order business-model line; source any court or
  bar actually *requiring* value measurement, not just opining on reasonableness.

## Jurisdictions not sourced this pass

- **Canada** — Federation of Law Societies / provincial law society AI guidance exists but
  no primary source pulled.
- **Australia** — courts/law societies have issued AI guidance; not sourced.
- **Singapore** — a Sept 2025 High Court case labeled unverified AI output "improper,
  unreasonable and negligent" (per secondary reporting). Not confirmed to primary; could
  be a strong L2 verification item for a non-US common-law jurisdiction. **Next pass.**
- **Federal standing orders** — the feed references "300+ judges" but carries no *named*
  standing order (e.g., Judge Brantley Starr, N.D. Tex., 2023). Adding one concrete
  standing order would give the disclosure fault line a T2 anchor with a primary URL.

## URL / date flags on admitted items

- **All primary URLs verified 200** (judiciary.uk, capitol.texas.gov, eur-lex.eu,
  vacourts.gov, arxiv.org) — 2026-09-05.
- **Withers v. Aberdeen** — dated 2026-06-01, day-of-month not confirmed (June 2026 is
  solid from multiple outlets). Tighten the exact date from CourtListener before relying
  on it in a backtest.
- **New Jersey tech CLE** — dated 2025-04-01, month-precise (approved April 2025); the
  effective date 2027-01-01 is well-corroborated.

## Structural note for the next pass

- The scorer matches fault lines by **substring `signals` in `title`+`text`** — it does
  *not* read the `fault_lines` field. Every new item's `text` must contain the target
  fault line's signal words or it scores as dead weight. This pass wrote `text` accordingly;
  keep that discipline in the harvester.
- The `order` field is currently advisory (scorer doesn't consume it); it's worth a
  deliberate decision in `ingest.py` whether L1 (capability) items should be scored in a
  *separate lane* rather than fed through the ruling-pressure meter, per backlog #3.

## Resolved 2026-09-07
- **Colorado feed item corrected.** The old "Colorado AI Act takes effect" item asserted a
  risk-based regime (risk management systems, conformity, impact assessments) that never took
  effect: SB 24-205 was repealed May 14 2026 by SB 26-189 (narrower transparency/consumer-rights
  law, eff. Jan 2027) before its duties came into force. Replaced with an accurate 2026-05-14
  item; the convergence line now reflects the retreat from the EU-style risk-based model.
- **California Rule of Court 10.430 added** (T1, 2025-07-18): first statewide court rule requiring
  courts to adopt generative-AI policies (confidentiality, accuracy, bias, disclosure, human
  review; no autonomous AI decisions). Maps to convergence/disclosure/verification.

## Enablement (E) lane added 2026-09-07 — next-pass hunting ground
The E meter (market deployability, docs/radar-design.md §9) is wired but has ZERO `enable`-class
evidence yet, so every reading equals its seed. **Next pass:** hunt for real deploy_scale (firm-wide
deployment at scale), standard (a bar adopting a tool certification / benchmark), provider
(dedicated vendor category with capital/M&A), and client_pull (RFP/GC requirements) items from the
§5.2 backlog: tool consolidation (Harvey/Clio-vLex), A&O Shearman + Harvey at 5,000 lawyers, the
RFP % rise, e-discovery/contract-review maturity.

## Enable evidence added 2026-09-07 (first tranche)
Tagged existing items: Stanford error study -> enable=standard (benchmark); CNA questionnaire ->
enable=playbook (insurance). Added: A&O Shearman + Harvey firm-wide agentic deployment ->
enable=deploy_scale (agentic, 2025-04-07); PLI legal-AI competency framework -> enable=standard
(competence, 2026-05-05). E now differentiates on benchmark/competence/insurance/disclosure/agentic.
**Known artifacts (v1 substring matcher):** (a) disclosure signal "certif" matches "uncertified" in
the CNA text, so disclosure picks up CNA as spurious playbook evidence (E 7.2 partly inflated);
(b) new matched items also feed the L2 ruling meter via the G5 lane-conflation, nudging competence/
agentic pressure slightly. The real unlock is attributing enable/market/capability by curated
fault_lines instead of substring signals.

## Attribution changed to curation-first 2026-09-07
The scorer now attributes every item to a fault line via its curated `fault_lines` field
(fallback to signal match only for uncurated items), instead of substring-signal matching. Fixes
signal leakage: the "certif" signal matching "uncertified" in the CNA text no longer feeds
disclosure, and benchmark/capability items no longer leak into competence/disclosure via stray
words in their text. Several meters normalized DOWN as a result (e.g. disclosure capability 6.7 ->
5.5 seed, competence capability 4.5 -> 2.5 seed, benchmark pressure 7.2 -> 6.7): those were
leakage-inflated, not real signal. Calibration unchanged (0.67). **Consequence:** per-line evidence
is now exactly as complete as each item's curated `fault_lines` — audit/complete curation if a line
reads under-evidenced.

## Curation audit 2026-09-07
Reviewed all 28 items' curated fault_lines against their actual content. Finding: curation is
largely sound. One high-confidence fix: Cal. Rule of Court 10.430 (item) now also lists
confidentiality (its text explicitly covers it) -> confidentiality nEv 6->7, L2 steady at 9.7
(saturated). Deliberately did NOT guess-add lanes from theme (that is the noise curation-first
removed). Left as-is pending source text if revisited: the two error-rate studies are tagged
inconsistently (Stanford Westlaw/Lexis = benchmark only; Stanford RegLab = benchmark + verification);
ABA 512 lists no 'fees' though Op 512 touches Rule 1.5 billing (Virginia LEO 1901 carries fees).

## Enable evidence expanded + E gated on deploy 2026-09-07
Enable evidence now covers 6 lines (feed = 30): added deploy_scale e-discovery/contract-review
maturity -> verification, and provider no-training/data-governance -> confidentiality (alongside
existing benchmark/insurance/competence/agentic enable items). **Enable evidence is now NON-decaying**
(market supply is a persistent fact, like capability), so a 2025 deploy-at-scale event no longer
fades to ~14% weight. E now reads: benchmark 8.3, verification 8.1, competence 7.4, insurance 6.9,
confidentiality 6.7, agentic 6.5, disclosure 6.0 (seed), rest seed. **E is a hard gate on the deploy
axis only** (ENABLE_READY=6.0 in advisory.py): deploy-now requires E>=6; GOVERN is never gated on E.
Currently latent (all deploy-eligible lines E>=6) — correct, binds only if market supply drops.
Calibration unchanged (0.67).
