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
