# Fault-Line Radar — Upgrade Roadmap

Reference for "what next" questions. Current feed lives in `radar-market-inventory.md` + `radar-market-inventory.jsonl` (4 streams: vendor capital/M&A, model-access unlocks, regulatory room, method/playbook).

## Stream priority (ranked)

Decision made 2026-09-08: skip the consultancy stream, build these two instead.

### 1. Judicial / regulatory docket feed — BUILD (leading)
- **Signal:** every AI-misuse sanction, bar referral, fee reduction, disqualification, and bar formal opinion 2023–mid-2026.
- **Why it wins:** T1 (binding orders), exact dates, verifiable against CourtListener/primary dockets, fires continuously. Directly drives `verification`, `competence`, `candor` fault lines.
- **Why it's leading:** enforcement pressure is what predicts method codification — the engine's highest-frequency input.
- **Seed cases already held:** Mata v. Avianca (SDNY Jun 2023), Manasco/Butler Snow (N.D. Ala Jul 2025), Simon/Green Building Initiative (D. Or Oct 2025), LG Darmstadt (Nov 2025).

### 2. Certification / benchmark-standard adoption — BUILD (origination watch)
- **Signal:** dated adoption of a *specific, named* tool standard by a bar, insurer, or court — not firm-internal policy. Benchmark standards (LegalBench, ISO/ANSI), vendor certification programs, insurer-required certified tools, bar "AI verified" badges, ABA formal opinions.
- **Why it wins:** a single adoption event converts the method layer from soft to enforceable. It's the origination the momentum model is waiting for.
- **Fault lines:** `benchmark`, `disclosure`, `competence`, `insurance`.

### 3. Consultancy / service-tier adoption — SKIP (lagging, soft)
- **Why skip:** lagging confirmation signal, few hard dates, fails the 3-vote verification harness, maps to `convergence` (already covered via Clio/vLex + Harvey embedded teams). Shows up *after* enforcement moved, so it lags the thing the engine predicts.

## Logic (why this order)

The momentum signal predicts *continuations*. Continuations are driven by enforcement and standards — the things that make adoption compulsory. Consultancies are the voluntary tail; they lag enforcement. Build hard, verifiable, leading signals first; soft confirmation signals only if a gap opens.

## Status log

- 2026-09-07: streams 1–4 built (4 passes on vendor capital).
- 2026-09-08: streams 5 (docket feed) + 6 (certification watch) built — 10 dated rows appended to the inventory. Key findings: first `vendor_liability` docket datapoint (Gamez/OpenCase) + non-lawyer-delegation failure mode (Mezu); Op 512 = named standard, CA COPRAC = in-progress voluntary→enforceable crossing; no insurer-certified-tool LPL condition or named third-party benchmark yet (open origination).
