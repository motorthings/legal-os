# Legal-AI Market Inventory — 2023→mid-2026

Dated, source-cited evidence feed for the Fault-Line Radar momentum signal.
Generated 2026-09-07 via deep-research harness (106 agents, 24 sources, 94 claims, 25 adversarially verified → 20 confirmed → 9 synthesized).

Companion machine feed: `docs/radar-market-inventory.jsonl`

## Headline

Three dated movements converge across 2023–mid-2026, but only two of the three stack layers populated. Capital and method are dense and verifiable; the **model-access layer came back empty** — no surviving dated claim captures a frontier-model unlock (long-context, agentic reasoning, tool-use, low-hallucination on legal queries). That is a hole in the momentum model, not a research miss.

## Confirmed findings

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2025-02 | Harvey Series D ~$100M, $3B, Sequoia-led | harvey.ai/blog | T4 | convergence | continuation |
| 2025-06-23 | Harvey Series E $300M, $5B, Kleiner Perkins/Coatue | Fortune | T4 | convergence | continuation |
| 2025-10-29 | Harvey Series F ~$160M, $8B, a16z; cum >$1B | Bloomberg/Forbes | T4 | convergence | continuation |
| 2026-03-25 | Harvey Series G ~$200M, $11B, GIC+Sequoia; ~$190M ARR | Bloomberg/CNBC/GIC | T4 | convergence | continuation |
| 2025-10-30 | Legora Series C $150M, $1.8B | BusinessWire/Sifted | T4 | convergence | continuation |
| 2026-03-10 | Legora Series D $550M, $5.55B, Accel-led | CNBC/Crunchbase | T4 | convergence | continuation |
| 2026-04 | Legora ~$50M ext (Nvidia+Atlassian) → ~$5.6B; 5 acqs | tech.eu/Bloomberg | T4 | convergence | direction_shift |
| 2026-05-07→07-27 | Digital Omnibus: Annex III → 2026-12-02, Annex I → 2028-08-02 | licentium.io | T1 | vendor_liability | direction_shift |
| 2026-05-19 | Commission draft: agentic systems = single high-risk system | arthurcox.com | T2 | agentic | origination |
| 2026-03 (~) | CNA firmwide-AI playbook anchors ABA 1.1/1.6/3.3/1.5 | pabarinsurance.com | T3 | confidentiality | origination |
| 2026 | LPL AI exclusions + affirmative AI cover | ABA Journal/Bloomberg | T3 | insurance | origination |
| 2025-07-23 | Manasco reprimands 3 Butler Snow lawyers (5 fake cites) | abajournal.com | T1 | verification | continuation |
| 2025-10 | Simon OSC re Green Building Initiative (Buchalter) | abajournal.com | T1 | verification | continuation |
| 2025-11-10 | LG Darmstadt zeroes AI-drafted expert fee (19 O 527/16) | chambers.com | T1 | competence | origination |
| 2025-08-08 | Ebers "LawGPT" — UPL-by-LLM live question | cambridge.org | T4 | vendor_liability | origination |

### Date-uncertain / single-source flags

- **CNA playbook** — date is only "~March 2026" (path-inferred); primary PDF is AES-256 encrypted, "closed loop" sentence not OCR-verifiable (the only split vote, 2-1).
- **Harvey Series F** — leaked as $150M (Oct 2025), officially $160M (Dec 2025).
- **Legora extension** — co-led Nvidia NVentures + Atlassian, not Nvidia-only.
- **LPL taxonomy** ("absolute vs limited at renewal") — single-source commentary, not primary policy text.
- **Ebers chapter** — single primary-publisher source (Cambridge), though it is the book itself.

## Killed by verification (do NOT feed)

- "Annex III deferral benefits GPAI/HR/credit/biometric operators" — 0-3, overreach.
- "Harvey and Legora are both pure agentic-workflow, not foundation-model bets" — 0-3, bifurcation claim unsupported.
- Manasco "July 30, 2025 disqualification" — 1-2; it was reprimand + bar referral, not disqualification.
- "EU AI Act will materially affect legal tech market" (Ebers chapter) — 0-3.
- "BRAO §43e(1) is the only German legal-profession AI anchor" — 0-3.

## Gaps that matter for the signal

1. **Model-access layer empty.** Stream 2 (frontier unlocks) returned zero dated, surviving claims. The stack has no "AI capability" input yet.
2. **Named vendors dropped.** Thomson Reuters/Casetext, Clio/vLex, Relativity, Ironclad all absent from synthesis — four distinct origination signals (legacy-platform M&A, practice-management M&A, e-discovery, CLM workflow).
3. **Fault-line taxonomy drift.** Workflow emitted `regulatory room` as a fault line, which isn't in the canonical list. Remapped to `vendor_liability`/`agentic` here; decide whether "regulatory room" is a fourth input layer or folds into `vendor_liability`.

## Open questions

- Are Harvey ($11B) / Legora ($5.55B) entering a correction phase? Model-owned vs workflow-owned bifurcation unresolved.
- Will carriers move from firm-internal policy to requiring certified AI-tool standards at LPL renewal?
- Do the EU deferral (widens runway) and anti-splitting rule (narrows loophole) net looser or tighter for legal-AI vendors?

---

## Second pass (2026-09-07) — model-access layer + Clio/vLex

Fills the two gaps from the first pass. 105 agents, 23 sources, 83 claims, 25 verified (24 survived, 1 killed).

### Target A — frontier model unlocks ("model access")

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2023-11-21 | Claude 2.1: 200K context + beta tool use | anthropic.com | T5 | competence | origination |
| 2024-03-04 | Claude 3: first Claude vision/document input | anthropic.com | T5 | competence | origination |
| 2024-10-22 | Claude 3.5 Sonnet: first frontier computer-use public beta | anthropic.com | T5 | agentic | origination |
| 2025-02-24 | Claude 3.7 Sonnet hybrid reasoning + Claude Code preview | anthropic.com | T5 | agentic | direction_shift |
| 2025-03-11 | OpenAI Responses API + Agents SDK (third-party agentic) | techcrunch.com | T4 | agentic | direction_shift |
| 2025-05-22 | Claude Code GA (1.0.0) | github.com/anthropics | T5 | agentic | direction_shift |
| 2025-05-23 | OpenAI Operator upgraded to o3, global research preview | venturebeat.com | T4 | agentic | continuation |
| 2025-07-29 | Vals legal_bench: GPT-5 84.6% #1 of 63 models | vals.ai | T5 | benchmark | origination |
| 2025-08-12 | Claude 1M-token context public beta (Sonnet 4) | claude.com | T5 | competence | direction_shift |
| 2025 | JURIX 2025: frontier LLMs era-biased/citation-hallucinating (GPT-5 35.29% pre-1881; best 73.31%) | arxiv 2510.20941 | T3 | verification | origination |
| 2025 | LRAGE: legal RAG gains corpus/backbone-dependent | arxiv 2504.01840 | T3 | competence | continuation |
| 2026-03-13 | Claude 1M context GA (Opus 4.6/Sonnet 4.6) | claude.com | T5 | competence | direction_shift |
| 2026-05 (~) | Etymolt trademark-clearance hallucination benchmark | github.com/etymolt | T5 | verification | origination |
| 2026-08-19 | Claude computer-use + browser-use GA | platform.claude.com | T5 | agentic | direction_shift |

### Target B — Clio/vLex (only vendor to survive verification)

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2023-10 | vLex Vincent AI launched (GPT-4) | legaltechnology.com | T4 | convergence | origination |
| 2025-06-30 | Clio definitive agreement to acquire vLex, $1B | clio.com | T4 | convergence | direction_shift |
| 2025-11-10 | Clio closes vLex ($1B) + $500M Series G (NEA) @ $5B | abajournal.com | T4 | convergence | direction_shift |

### Second-pass caveats

- **Target B still thin.** Relativity, Ironclad, Robin AI, Luminance, EvenUp, Spellbook, Paxton, Leya, e-discovery, CLM — none survived three-vote verification. Treat vendor-capital as *under-covered*, not as evidence those vendors raised nothing. A third pass on those named vendors is required before the vendor-capital track is complete.
- **Benchmark evidence is the most decision-relevant.** None of it certifies legal reliability; it quantifies persistent hallucination and shallow reasoning on historical authority. This is the core risk signal, not a "capability unlock" signal.
- **Time-sensitive figures.** Vals' 84.6% GPT-5 is a stale single-date snapshot (live leaderboard now ~88.6% Claude Fable 5). Operator folded into "ChatGPT agent" ~Jul 2025. Clio $5B reflects only announced financing as of Sept 2026.
- **Single-source precision caveats.** Model enumeration on the Aug 19 2026 computer-use GA (Opus 5/Sonnet 5 vs 4.8) rests on one vendor source. arXiv 2510.20941 drives three findings — internally the strongest verification signal, but single-source per claim (peer-reviewed JURIX 2025, public data).
- **"Origination"/"direction shift" on Anthropic/OpenAI agentic tiers** is defensible only as model-access unlocks, not product inventions (Claude Code, operator-style agents, tool-use all had non-Anthropic/OpenAI precursors).

### Remaining open questions

- Do the era-bias/citation-hallucination results (73.31% best; GPT-5 35.29% pre-1881) replicate on post-2000 authority, or is degradation specific to pre-1980 case law?
- Is there any vendor-independent (non-Etymolt, non-Vals) legal eval at high confidence?
- Does Clio/vLex $5B set a new benchmark tier for practice-management (CLM) valuations, and what does CLM+research convergence imply for pure-play research-AI (vLex-like) standalone valuations?

---

## Third pass (2026-09-08) — dropped vendors

Targeted the nine named vendors. 104 agents, 22 sources, 83 claims, 25 verified (24 survived). Cross-corroboration now exists for five of nine.

### Confirmed this pass

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2023-06-26 | Thomson Reuters acquires Casetext, $650M cash (closed 2023-08-17) | thomsonreuters.com | T4 | convergence | direction_shift |
| 2024-01-03 | Robin AI $26M Series B, Temasek-led | robinai.com | T5 | convergence | continuation |
| 2024-09-26 | Relativity aiR for Review GA (genAI e-discovery) | edrm.net | T5 | verification | origination |
| 2025-10-09 | Spellbook $50M Series B, Khosla-led, $350M post-money | spellbook.legal | T5 | convergence | continuation |
| 2026-03-04 | Spellbook $40M RBCx debt facility (acquirer, not acquired) | theglobeandmail.com | T4 | convergence | direction_shift |
| 2025-12-04 | Harvey Series F officially confirmed $160M @ $8B (a16z) | techcrunch.com | T4 | convergence | continuation |

### Still unverified (do NOT infer rounds)

**Ironclad, Luminance, EvenUp, Paxton AI, Leya** — no surviving claim verified a dated round, valuation, or acquisition. This is a sourcing-depth limitation, not proof of inactivity.

Two of them have real rounds that failed the 3-vote bar only because they were single-source vendor blogs:
- **EvenUp** — a $135M Series D exists on evenuplaw.com (Oct 2024, Bain Capital Ventures, ~$1B valuation) but did not survive adversarial verification.
- **Luminance** — a $75M Series C led by Point72 Private Investments exists on luminance.com (Apr 2024) but was single-source.

Both are almost certainly real and should be re-verified against an independent outlet (TechCrunch/Bloomberg/press release wire) rather than trusted as-is.

### Third-pass caveats

- **Relativity** — only the aiR product launch is dated. Funding, valuation, and M&A history remain unverified (it is private-equity-backed; a ~$3.6B Silver Lake-era valuation from 2021 surfaced in sources but is outside the 2023–2026 window and unverified for that period).
- **Harvey "$818M across four 2025 rounds"** is a single-outlet (Artificial Lawyer) aggregation that bundles the EQT strategic investment as a "round" — medium confidence. The individual rounds (Series D/E/F) are independently confirmed.
- **Spellbook acquisition plan** (up to five deals, $60M) is forward-looking CEO intent as of March 2026, not completed fact.
- **"First-ever" / "25,000 agents" / "Autonomous Contract Management"** are T5 vendor-marketing superlatives, attributed not measured.

### Residual open question

EvenUp and Luminance (and the still-dark Ironclad/Paxton/Leya) need one more targeted pass against independent wire/outlet sources before the vendor-capital track is genuinely complete.

---

## Fourth pass (2026-09-08) — final vendor-capital closure

Targeted the five dark vendors + Relativity against independent outlets (no vendor blogs). 101 agents, 19 sources, 67 claims, 25 verified (24 survived). **Vendor-capital track is now closed — all nine originally-named vendors resolved.**

### Confirmed this pass

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2024-04-02 | Luminance $40M Series B, March Capital-led | Reuters/CNBC | T4 | convergence | continuation |
| 2024-07-17 | Leya $25M Series A, **Redpoint**-led (not Benchmark) | siliconangle.com | T4 | convergence | continuation |
| 2024-10-08 | EvenUp $135M Series D, Bain Capital Ventures, $1B+ unicorn | crunchbase.com | T4 | agentic | origination |
| 2025-01-29 | Paxton AI $22M Series A, Unusual Ventures, total $28M | legaltechnology.com | T4 | verification | continuation |
| 2025-02-18 | Luminance $75M Series C, Point72; valuation not disclosed | techcrunch.com | T4 | convergence | origination |
| 2025-10-06 | Relativity "Rel Labs" investment arm (~$170M R&D) — not a raise | manilatimes/PRNewswire | T4 | disclosure | origination |
| — | Ironclad: no 2023–2026 priced round; $3.2B (Jan 2022) stands | bloomberglaw.com | T4 | convergence | continuation |

### Corrections from this pass

- **Luminance date was wrong.** The $75M Point72 round is the Series C, announced **Feb 18 2025**, not April 2024. April 2024 was a separate $40M Series B (March Capital). Series C valuation was never disclosed; the ~$400M figure is a Forbes/PitchBook database estimate, not fact.
- **Leya's lead was wrong.** Benchmark did *not* lead the Series A; **Redpoint** did (July 17 2024). Benchmark led the earlier $10.5M seed.
- **EvenUp cleared at $1B+ unicorn** (Oct 8 2024, Bain Capital Ventures) — the single-source vendor blog from pass 3 was real.

### Negative findings (do NOT treat as "no activity" — treat as "no priced round")

- **Ironclad** — no down round, no markdown, no 2023–2026 priced round on record. Its Sept 2025 "Unattributed VC" entry on CB Insights has no amount/valuation and was refuted as a funding event (0-3).
- **Relativity** — no in-window equity raise/valuation/acquisition. "Rel Labs" is an internal R&D arm backing *other* startups, not capital into Relativity. PE-backed, so non-public rounds may exist undisclosed.

### Track status

Vendor-capital evidence stream is complete across four passes: Harvey, Legora, Clio/vLex, Thomson Reuters/Casetext, Robin AI, Spellbook, Relativity (product + Labs), EvenUp, Luminance, Paxton AI, Leya, Ironclad. Residual open items are all forward-looking (Leya/Paxton post-2024 rounds, Luminance real valuation, Ironclad secondary/insider moves) — no unverified *dated* rounds remain.

---

## Stream 5 + 6 (2026-09-08) — docket feed + certification watch

The two leading streams from the upgrade roadmap. 103 agents, 21 sources, 82 claims, 25 verified (24 survived).

### Stream 5 — judicial/regulatory docket feed (enforcement)

Six dated events beyond the four seed cases. Venue-broadening cascade: district → circuit → state-bar discipline.

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2024-01-30 | Park v. Kim (2d Cir.): LR 46.2 referral, nonexistent AI case | courtlistener.com | T1 | verification | origination |
| 2025-10-29 | Mezu v. Mezu (Md. App.): AGC referral for non-lawyer clerk ChatGPT delegation | courtlistener.com | T1 | verification | origination |
| 2026-02-09 | Amarsingh (10th Cir.): $1,000 FRAP 38, 7 fake cites + MD bar referral | ca10.uscourts.gov | T1 | verification | continuation |
| 2026-03-13 | Whiting (6th Cir.): two lawyers $15k each + double costs + referral | courtlistener.com | T1 | verification | continuation |
| 2026-03 | Alabama Bar Public Reprimand of Matthew Reeves (Butler Snow) | alabar.org | T2 | competence | continuation |
| 2026-04-06 | Gamez (E.D. Cal.): OSC **naming product OpenCase** | law360.com | T1 | vendor_liability | origination |

**Two origination signals that matter beyond the count:**
- **Mezu** — the failure mechanism is *delegation to a non-lawyer clerk*, not personal AI use. That's a new `competence`/supervision fault line, distinct from the "lawyer didn't verify" pattern.
- **Gamez** — first OSC that names a specific legal-AI *product* (OpenCase) as the source of fabricated cites. This is the first `vendor_liability` datapoint in the docket feed, and it's the one your engine should weigh heaviest.

### Stream 6 — certification / benchmark-standard adoption (origination watch)

All confirmed items are ethics opinions and rulemakings, not third-party benchmark or insurer-vendor certifications. That absence is itself a finding.

| date | event | source | tier | fault_line | flag |
|---|---|---|---|---|---|
| 2024-04-25 | Missouri Informal Op 2024-11 (pre-ABA GenAI guidance) | mo-legal-ethics.org | T2 | competence | origination |
| 2024-07-29 | ABA Formal Op 512 "Generative AI Tools" | americanbar.org | T2 | benchmark | origination |
| 2025-01-01 | Illinois SC policy: disclosure of AI use NOT required | illinoiscourts.gov | T2 | disclosure | origination |
| 2026-03-13 | California COPRAC: AI duties woven into 6 RPCs | calbar.ca.gov | T2 | benchmark | origination |

**The three things this stream tells the engine:**

1. **Op 512 is the named standard** (Jul 29 2024), and it's the origination of the voluntary→required crossing: it explicitly reserves that lawyers "may eventually have to use [GAI] to competently complete certain tasks." That's a direction-shift signal embedded in a T2 source.
2. **California COPRAC (Mar 13 2026) is the strongest origination** — first state bar to propose *enforceable* (not advisory) AI-specific rules, weaving verification/disclosure duties into six Rules of Professional Conduct. Still in a second comment round (closed Aug 6 2026), not final. When/if the CA Supreme Court adopts it, that's the conversion event your model is watching for.
3. **The negative finding:** no insurer has yet made a certified AI tool an LPL renewal condition, and no bar has adopted a named third-party benchmark (LegalBench/ISO/ANSI/NIST). The method layer has not yet crossed from *opinion* to *enforceable certification* — the origination is still open. That's the single most valuable "watch this space" signal in the whole feed.

### Date/source flags

- **Alabama Reeves reprimand** — no published disciplinary date, only Winter/March 2026 newsletter.
- **Gamez** — date rests on order PDF filename + Law360 "~Apr 6-7."
- **Whiting** — one secondary said "refund client fees" but the actual order is to reimburse the *opponent* (City), not the lawyer's own client. 2-1 vote.
- **Killed:** Shawnee County KS "Rule 3.125" AI-disclosure court rule — 1-2, refuted as single-source. Do not feed.
- **Illinois "disclosure not required"** holds statewide but some individual circuit judges issued contrary standing orders.

### Residual open questions

- Any *final* California Supreme Court action on COPRAC after Aug 6 2026?
- Any insurer actually conditioning LPL renewal on a certified tool (the Target 2 sub-claim that surfaced nothing)?
- Disposition of the Mezu/Amarsingh Maryland AGC referrals and the Whiting/Park disciplinary referrals?
