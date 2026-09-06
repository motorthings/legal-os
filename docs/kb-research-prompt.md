# Fault-Line Radar — KB Deep-Research Prompt

Reusable prompt for building out the radar's knowledge base (`radar/sources/feed.jsonl`).
It produces append-ready JSONL matching the engine schema, and it applies the same
anti-noise admission rules the future `ingest.py` harvester will automate.

The whole engine's honesty rests on what gets admitted and at what tier. A wrong or
overweighted item corrupts every downstream score. Run this, review the quarantine
list, then append.

---

```
Deep research task: build out the Fault-Line Radar knowledge base.

CONTEXT
The radar (/legal-os/radar) forecasts where legal-AI rules are heading by scoring
"fault lines" — places where an AI capability stresses a legal duty. It scores
evidence by SOURCE AUTHORITY, not volume, across three orders of prediction:
  L1 capability (AI can now do X) -> L2 ruling (a court/bar/statute reacts)
  -> L3 adoption (a control becomes table stakes in the market).
Your job is to find and structure real, verifiable sources to feed it. Signal,
not noise: a wrong or overweighted item corrupts every downstream score.

OUTPUT FORMAT
Return JSONL, one object per source, matching this exact schema:
  {
    "date": "YYYY-MM-DD",           // when it landed / took effect / was published
    "tier": "T1|T2|T3|T4|T5",       // source authority — see rubric below, be strict
    "title": "…",
    "source": "issuing body / court / author",
    "url": "…",                      // primary source; no paywalled aggregators if avoidable
    "empirical": true|false,         // carries hard data (error rates, counts, $ figures)?
    "conflict": true|false,          // does the source sell what it's commenting on?
    "market": "insurer|procurement|deployment|cert|process_mandate|commentary|pundit",
                                     // ONLY if it's a third-order adoption signal; else omit
    "text": "2-3 sentence factual summary — what it holds/requires, which duty it touches",
    "fault_lines": ["disclosure","verification",…],  // your best mapping; ok to leave []
    "order": 1|2|3                   // which order this is evidence for
  }

TIER RUBRIC (authority earned, weight the engine applies)
  T1 (1.0)  Binding/primary: court rulings, sanctions orders, statutes, regulations,
            rule amendments.
  T2 (0.8)  Regulatory guidance: ABA & state-bar ethics opinions, judicial standing
            orders, official practical guidance.
  T3 (0.6)  Empirical/institutional: peer-reviewed research, court-hallucination
            trackers, insurer/market actions carrying data.
  T4 (0.35) Professional commentary: law-firm client alerts, bar journals, established
            legal press.
  T5 (0.008) Vendor/marketing/opinion: vendor blogs, SEO, LinkedIn hot takes. ~1/100 of
            an ABA opinion. Set conflict:true if a vendor discusses its own category.
  When unsure between two tiers, pick the LOWER. Over-crediting is the failure mode.

THIRD-ORDER (L3) SIGNALS — weight by how binding on the MARKET, not the court:
  insurer (strongest — carriers gate coverage) > procurement/RFP attestation >
  Big Law/MSP deployment data > certification/benchmark standards >
  process_mandate (a rule/opinion mandating a *process* control) > commentary > pundit.

SCOPE (find items across all three orders, 2023–present, plus seminal earlier ones)
  - L2 rulings & sanctions: AI-hallucination sanctions, disclosure/standing orders,
    evidentiary exclusions, bar discipline, statutes (EU AI Act, state AI acts).
  - L2 guidance: ABA 512 and every state-bar AI ethics opinion you can verify.
  - L1 capability: benchmark results, error-rate studies, model/agent releases with
    legal relevance (tag order:1, keep low-weight, empirical only — no hype).
  - L3 adoption: insurer AI questionnaires/endorsements, RFP/procurement language,
    firm/MSP governance deployments, tool-certification efforts, cross-border
    convergence (conformity assessments, risk-management mandates).

RULES OF ADMISSION (anti-noise — this is the point)
  1. Primary source or it doesn't go in. Cite the ruling/opinion/statute/study itself,
     not a vendor's summary of it. If you can only find secondary coverage, tier it
     as that coverage (T3/T4) and say so.
  2. No duplicates. If several outlets report one event, submit ONE item at the
     highest-authority source; note corroboration in text, don't create N rows.
  3. Verifiable dates and URLs only. If you can't confirm the date, flag it, don't guess.
  4. Flag conflicts. Vendor-authored "research" about its own tool is conflict:true.
  5. Separate prediction from fact. Speculative "future of law" essays are T5/pundit,
     order tag aside — never smuggle them in as rulings.
  6. Quarantine, don't force-fit. If an item is real but you can't tier or map it
     confidently, put it in a separate "review" list with your uncertainty noted,
     rather than admitting it.

DELIVERABLES
  1. feed_additions.jsonl — new, deduped, schema-valid items ready to append.
  2. review_queue.md — items you found but wouldn't confidently admit, with why.
  3. coverage_notes.md — what's thin or missing (a fault line with no recent L3
     evidence, a jurisdiction you couldn't source), so the next pass knows where to dig.
```

---

## Notes before running

- **Append target:** `radar/sources/feed.jsonl`. The schema above matches the engine
  after the third-order layer was added (`market` + `order` fields). Output drops in
  as new lines — no re-keying.
- **Tier discipline is the honesty of the whole engine.** A vendor blog is ~1/100 of an
  ABA opinion by design. When torn between two tiers, pick the lower.
- **This is the manual version of the `ingest.py` harvester** (backlog #1). Running it
  by hand now also stress-tests the admission rules before they get automated.
- **After appending,** run `python radar/run.py` to re-score and regenerate the page,
  and check the calibration panel didn't move in a way you can't explain.
