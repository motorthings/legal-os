# Legal AI Operating System — Platform Summary

## A governed platform for building, deploying, and measuring AI across the legal enterprise. Nine functions. Harvey agent monitoring. One governance layer. Every decision auditable, explainable, and traceable.

**Deployed:** Backend on Fly.io (`legal-os-api.fly.dev`), frontend on Vercel (`legal.sickofancy.ai`). 52 backend tests passing. 89 help docs indexed.

---

## The Business Case

Law firms face three structural problems that will determine which firms thrive and which become cautionary tales:

**Shadow AI is already inside the firm.** 69% of legal professionals use generative AI for work — most without firm knowledge or approval. Every associate with a ChatGPT tab open is a confidentiality event waiting to happen. You cannot govern what you pretend is not happening. The platform provides a safe, governed alternative that replaces shadow tools with auditable, enterprise-grade AI.

**Most firms have fake governance.** 43% of firms have no AI policy and no plans to create one. The remaining 57% mostly have a document nobody read after week one. ABA Formal Opinion 512 is clear: the duty of competence now includes understanding the benefits and risks of relevant technology. A policy document is not governance. Governance is structural — it lives in the database, not in a PDF. The platform makes governance the architecture, not the afterthought.

**The billable hour model is under structural pressure.** 85% of clients say firms should disclose when AI is used on their matters. 64% of in-house teams expect to depend less on outside counsel. The premium for routine work is evaporating. The firms that thrive will be the ones that use AI to deliver faster, better work — and can prove it with an audit trail. The platform turns AI from a margin threat into a competitive differentiator.

**The ROI imperative.** 85% of firms do not track AI ROI. The platform captures telemetry at the invocation level — every function call logs who used it, for which client, how long it took, what model was used, what it cost, and how much human time was saved. ROI reporting is a query, not a research project. Every quarter, every client gets a report showing exactly what AI saved — with the math to back it up.

---

## The Architecture

The platform is a five-layer operating model. Each layer is independent — replace one without rebuilding the others.

### Layer 0 — Knowledge Foundation

**What it is:** A unified knowledge base combining precedent libraries, clause libraries, document management, and search infrastructure. Everything the AI functions need to reason over — inside the trust boundary.

**Why it matters:** Without this layer, every AI function starts from zero. With it, institutional knowledge compounds. Two centuries of firm memory becomes searchable in seconds. This is the layer most firms skip — and the reason most legal AI projects stall after the demo. The model can reason. It cannot reason over what it cannot see.

**How it works:** Every document the firm has ever produced — briefs, memoranda, deal summaries, reviewed contracts, partner research notes — is ingested, chunked, embedded, and indexed. Enterprise LLM agreements cover all API calls: no training on client data, no retention, no leakage between clients. Embedding and analysis run within the firm's enterprise infrastructure.

### Layer 1 — Governance & Trust

**What it is:** The non-negotiable foundation. Seven pillars, structurally enforced — not a policy document, but database-level controls that cannot be bypassed.

**The three non-negotiable pillars:**

- **Auditability:** Every evaluation captures the full prompt, the full response, the model version, the rubric version, and the scoring formula. When a partner questions a classification six months later — or when a client's outside counsel guidelines audit asks for proof — the full decision context is retrievable. Full prompt capture. Response and reasoning chain. Deterministic score replay. Structured JSONL logging. Immutable.

- **Explainability:** Every AI output includes its chain of reasoning — visible to the reviewer, not hidden in a vector. Classification decisions cite the specific clause, signal, or pattern that drove the result. Risk scores decompose into their weighted dimensions. The attorney understands *why* before they decide *whether*. Chain of reasoning. Source attribution. Dimension-level score decomposition. Visible, not hidden.

- **Traceability:** Who ran the evaluation. When. Which model version. Which rubric version. What the score was. Whether a human overrode it, and why. Full chain of custody from upload through review. Compliance-ready artifacts on demand — SOC 2, ISO 42001, EU AI Act, ABA 512, client audit requests. The answer to "prove it" is always one query away.

**Supporting architecture:**

- **Confidentiality Architecture:** Row-Level Security at the database layer. Client A's data cannot touch Client B's models. Employment legal walled from commercial legal. Practice group scoping enforced structurally — by PostgreSQL RLS policies, not application logic.

- **Human-in-the-Loop Gating:** AI recommends. Humans decide. Confidence below 70% triggers automatic escalation. Red flags are mandatory review regardless of confidence. No autonomous legal decision, ever. Every override is logged with who and why.

- **Model Governance:** Every AI agent evaluated before deployment. Multi-agent scoring across safety, bias, instruction quality, and ethics. Hard veto rules: any agent failing a critical dimension cannot ship. Drift detection monitors ongoing performance and flags degradation.

- **Compliance Readiness:** ABA Formal Opinion 512 (duty of competence, confidentiality, supervision). SOC 2 Type 2. ISO 42001. EU AI Act. Outside Counsel Guidelines. State Bar Ethics Opinions. All covered by the architecture, not a policy document.

### Layer 2 — Legal AI Functions

Eight standalone applications. Each owns its UI, workflow, and data. Each exposes a governance contract so the governance layer can verify compliance without coupling to implementation. Functions are independent — replace one without touching the others.

### Layer 3 — Program Operations

**What it is:** The bridge between AI capability and organizational adoption — the layer where the K&I Program Manager lives. Six components, all built and deployed:

- **Portfolio Dashboard:** KPI cards (hours saved, cost avoided, net ROI, adoption rate). Function-by-function breakdown with tooltips showing calculation methodology. Quality metrics section (accuracy rate, override rate, false positive rate). Hours-saved bar chart. Period selector (30/90/365 days).
- **ROI Framework:** Cost impact = time saved × billable rate from configurable rate cards (client, practice group, rate type). Quality tracked via structured attorney reviews: accuracy rate, override rate, false positive rate, agreement scores. Adoption = active users / eligible users with 30-day rolling window. Calibrated baselines with documented methodology, sample size, and confidence level. Net ROI = cost avoided − AI cost (including multi-step pipeline costs: router → evaluator → hallucination check → parallel verification → scoring).
- **POC Pipeline Tracker:** Kanban board: Discovery → Build → Review → Graduated (or Cancelled). Project cards with client and practice group assignment. Feedback log per project. Auto-timestamped status transitions. "Lead end-to-end delivery of AI-enabled client projects from concept through implementation."
- **Harvey Agent Monitoring:** Independent 4-dimension evaluation of Harvey AI outputs — ported from the AESOP evaluation engine. Accuracy, Safety, Bias scored at 1.5x weight (Tier 1); Compliance at 1.0x (Tier 2). Hard veto at 75 on any Tier 1 dimension caps the final score at 74.9. Certification: Platinum 90+, Gold 85+, Silver 80+, Bronze 75+. Drift detection across 6 types (tone, scope, refusal, instruction erosion, hallucination, safety). Agent registry with baseline system prompt snapshots. Weekly drift checks. Auto-generated alerts at 51+ severity. 21 dedicated tests. **Key principle:** Harvey agents live in Harvey — Legal-OS does not host them, it evaluates their outputs independently. Technology owns the agent. Legal-OS owns the measurement.
- **Enablement Kit:** 60-minute workshop deck outline. Prompt engineering guide with five rules for legal prompting. Adoption playbook with champion network design. AI literacy FAQ. Client conversation deck outline. RFP response templates. Technical FAQ for client CISOs.
- **Agentic Help System:** RAG-powered chat — Voyage AI embeddings → pgvector similarity search → LLM-generated answer with source references. 11 indexed help docs, 89 vector chunks. Slide-out panel with suggested questions and thumbs up/down feedback. Local FAQ fallback when API unreachable. Same architecture as the AESOP help system. Deployed at `/api/help/ask`.

**Six questions this layer answers:** What AI do we have deployed? Who is using it? What is it saving? Is it getting better or worse? What POCs are in the pipeline? How do we prove the value to clients?

### Layer 4 — Organizational Model

**What it is:** Maps AI functions to practice groups, divisions, and strategic priorities. Corporate gets contract review and due diligence. Litigation gets matter intake and regulatory monitoring. IP gets KM intelligence with the highest confidentiality walls. Every group gets what it needs, and nothing it should not see.

---

## The Nine Functions

Every function follows the same architecture pattern: Router classifies. Evaluator reasons. Programmatic layer scores. Audit trail captures everything. The LLM provides reasoning. The system provides judgment. Never the reverse.

---

### 1. Matter Intake & Triage

**The business case:** Every new client engagement starts with intake. Conflicts, staffing, risk appetite, billing arrangements — all decided in the first hours. Getting it wrong means malpractice exposure, profitability loss, or missed business. Getting it right, consistently, is structural competitive advantage. At a large firm, intake is not one process — it is hundreds of processes spread across practice groups. Standardizing intake evaluation is the highest-leverage operational move the firm can make.

**What it does:** Accepts a matter summary and returns a structured evaluation in under 10 seconds.

**Inputs:** A matter summary — unstructured text describing the potential engagement, parties involved, jurisdiction, urgency, and any known conflicts or concerns.

**Process:**
1. **Router** classifies the matter by practice area, urgency, and jurisdiction — low temperature, focused classification, returns structured JSON with confidence scoring.
2. **Evaluator** scores across five weighted dimensions with detailed reasoning.
3. **Programmatic scoring layer** applies weights, thresholds, and rules — never trusts the LLM directly.

**Outputs:**
- Practice area classification with confidence scoring and cross-practice elements flagged
- Conflict check triggers — adverse parties, business conflicts, prior representations
- Urgency and risk assessment across regulatory, financial, and reputational dimensions
- Staffing recommendation with role, hours estimate, and specialty requirements
- Data integrity check — what is missing from the intake, surfaced explicitly
- Overall risk badge: low / medium / high
- Full audit trail: every prompt, every response, every rubric version captured

**Value delivered:**
- Partners spend less time routing and more time lawyering
- Conflicts are flagged before the engagement letter goes out, not after
- Staffing recommendations are consistent across practice groups, not dependent on who is doing intake that day
- Every decision has an immutable audit trail — when the client asks, you can show your work
- The system gets smarter with every evaluation as the standards library grows

**Time saved:** ~30 minutes per matter (down from 30 minutes of attorney review to under 10 seconds).

---

### 2. Contract Review & Analysis

**The business case:** Contract review is the highest-volume knowledge task in any law firm. Every attorney does it. Most do it from scratch each time. The firm's accumulated wisdom about what is acceptable, what is risky, and what needs escalation lives in individual partner judgment — not in a system that gets better with every review. This function captures that judgment, applies it consistently, and surfaces only what needs human attention.

**What it does:** Analyzes any contract against 30+ configurable legal standards using five specialized AI agents — one per contract type.

**Inputs:** A contract document (PDF, DOCX, or plain text).

**Process:**
1. **Text extraction** from the uploaded document.
2. **Router** classifies the contract type: vendor, customer, employment, DPA, or general — returning classification with confidence and key signals.
3. **Specialized agent** performs clause-by-clause analysis against the firm's legal standards — each agent trained on domain-specific evaluation criteria for its contract type.
4. **RAG-powered knowledge base** retrieves firm-specific best practices, precedent language, and negotiation history for context.
5. **Programmatic risk scoring** across five dimensions: Financial Exposure (25%), Compliance & Legal (25%), Operational Risk (20%), Ambiguity & Clarity (15%), Term Favorability (15%). Red flags add weighted points. One critical flag = automatic high risk.
6. **Human-in-the-loop checkpoints** at every stage — AI recommends, human decides.

**Outputs:**
- Contract type classification with confidence score
- Clause-by-clause analysis with risk flags (critical, high, medium, yellow)
- Weighted risk score (0-100) with dimension-level decomposition
- Specific clause language that triggered each flag
- Recommended actions and negotiation positions
- Full audit trail from upload through final review

**Value delivered:**
- 360 contracts processed per hour — production throughput, not demo speed
- Consistent application of firm legal standards across all reviewers
- Junior associates learn from the system's reasoning — it is a training tool as well as a review tool
- Risk scoring is transparent and auditable — when a client asks why a clause was flagged, the reasoning is right there
- The knowledge base compounds: every reviewed contract enriches the clause library

**Time saved:** ~2 hours per contract (down from 2 hours of full attorney review to approximately 45 seconds of AI processing plus targeted human review of flagged clauses only).

---

### 3. Employment Legal Agents

**The business case:** Employment law involves some of the most sensitive documents in the firm — separation agreements, compensation data, personnel matters. These documents require maximum confidentiality (walled from commercial legal) and multi-jurisdiction accuracy (US, EMEA, Australia — each with different rules). The volume is moderate (~100 agreements per year) but the stakes per document are extremely high.

**What it does:** Three specialized agents serving the employment law function.

**Separation Agreement Generator:**

- **Inputs:** Employee details (name, role, location, length of service, reason for separation, compensation data).
- **Process:** Routes to the correct jurisdiction template. Populates the agreement with jurisdiction-specific language. Calculates severance based on country and length of service. Validates proposed amounts against policy. Flags discrepancies.
- **Outputs:** A jurisdiction-specific separation agreement ready for attorney review. Severance calculation with policy validation. Flagged discrepancies requiring human judgment.
- **Value:** Consistency across jurisdictions. Policy compliance enforced structurally, not manually. Maximum confidentiality — RLS walls employment data from commercial legal at the database layer.
- **Time saved:** ~2-4 hours per agreement (down from 2-4 hours of manual drafting to approximately 30 seconds of AI generation plus attorney review).

**Legal Metrics Analysis Agent:**

- **Inputs:** Natural-language query about legal operational data.
- **Process:** Parses the query. Routes to the correct data source. Retrieves and formats the data.
- **Outputs:** Outside counsel spend by firm and practice area. Procurement and revenue-contract execution volumes. Any legal ops metric the team tracks.
- **Value:** Replaces manual pulls across Tableau, spreadsheets, and billing systems. Restricted to Legal Leadership and Legal Ops only — not firm-wide.
- **Time saved:** ~30-60 minutes per query (down from manual data pulls to natural-language query in seconds).

**State Annual Report Filing Agent:**

- **Inputs:** Corporate data (officers, addresses, tax status) for each registered state.
- **Process:** Populates each state's specific form with the core data. Tracks filing status and due dates.
- **Outputs:** Completed state annual report forms ready for review. Filing status dashboard with approaching deadlines.
- **Value:** Low stakes, high repetition — the exact profile where AI delivers disproportionate value. Failure to file means loss of good standing — the agent tracks deadlines so nobody has to remember.
- **Time saved:** ~1-2 hours per filing cycle (down from manual form population and deadline tracking).

---

### 4. Cowork Legal Plugin

**The business case:** In-house legal teams need AI that works where they already work — in their existing tools, not in a separate platform they have to learn. The plugin provides nine legal-specific skills directly inside Claude and Claude Code, configured with the organization's negotiation playbook. No new tool to adopt. No new login to remember. Just the legal AI showing up where the legal team already is.

**What it does:** Nine skills for in-house legal teams, accessible directly from Anthropic's Claude.

| Skill | What it does | Input | Output |
|-------|-------------|-------|--------|
| Contract Review | Playbook-based clause-by-clause analysis with GREEN/YELLOW/RED classification and redline generation | Contract text + context | Flagged clauses, risk classification, proposed redlines, negotiation strategy |
| NDA Triage | NDA pre-screening with standard carveout checks | NDA document | GREEN/YELLOW/RED classification with specific issues flagged |
| Compliance Check | Regulatory compliance review across GDPR, CCPA, HIPAA, and other frameworks | Policy or practice description + regulatory framework | Compliance gaps, risk level, recommended actions |
| Risk Assessment | Severity × Likelihood matrix scoring with structured classification | Risk scenario description | Risk matrix placement, severity rating, likelihood rating, mitigation options |
| Legal Response | Templated responses for data subject requests, discovery holds, vendor questions, NDAs, subpoenas | Request type + context | Draft response ready for attorney review |
| Meeting Briefing | Structured briefings for deal reviews, board meetings, vendor calls, litigation prep | Meeting type + participants + context | Structured briefing document with key issues, questions, and recommendations |
| Vendor Check | Existing vendor agreement status lookup | Vendor name + context | Agreement status, key terms, renewal dates, flagged issues |
| Signature Request | E-signature routing with pre-signature checklist | Document + signatories + routing rules | Signature request ready to send, checklist completed |
| Daily Briefing | Team daily briefings, topic briefings, incident briefings | Briefing type + scope | Structured briefing summarizing key items |

**The playbook:** `legal.local.md` is the control document — the organization's standard positions, acceptable ranges, and escalation triggers. Every skill references it. Change the playbook, and every skill's behavior updates. The playbook is the control. The plugin is the interface.

**Value delivered:**
- No new tool adoption — the legal team uses AI where they already work
- Playbook-driven consistency — every review applies the same standards
- Attorney reviews every output before it leaves the firm — the plugin recommends, the attorney decides
- Nine skills covering the highest-frequency in-house legal tasks

---

### 5. Due Diligence Accelerator

**The business case:** Transactional practices — corporate M&A, finance, real estate — spend thousands of hours reviewing contracts for target-standards alignment. A single deal can involve hundreds of documents. Most of them are boilerplate. The reviewer's job is to find the ones that are not. This function automates the boilerplate review so the reviewer sees only what needs attention.

**What it does:** Ingests hundreds of documents for a deal, classifies each, compares every clause against deal-specific target standards, and surfaces only the deviations.

**Inputs:**
- A set of documents (contracts, agreements, amendments — PDF, DOCX)
- Deal-specific target standards (what the client or counterparty requires)
- Deal metadata (deal name, client, practice area, target close date)

**Process:**
1. **Batch ingestion** of all documents in the deal.
2. **Parallel classification** of each document by contract type.
3. **Clause-by-clause comparison** against deal-specific target standards.
4. **Identical clause grouping** — if 50 supply agreements all have the same indemnification clause, the reviewer sees it once, not 50 times.
5. **Deviation ranking** by severity and materiality.
6. **Delta-only presentation** — the reviewer sees only deviations, not 10,000 pages of boilerplate.

**Outputs:**
- Consolidated deviation report organized by clause type and severity
- Each deviation shows: the target standard, the actual clause language, the gap, the severity rating
- Identical clauses grouped — unique deviations only
- Deal summary: total documents, total deviations, risk distribution, estimated review time saved

**Value delivered:**
- Some contract types already compressible to 2 hours from 15-20 hours of manual review
- Reviewer attention focused on what actually differs from the standard — not on confirming boilerplate
- Consistent comparison — every document measured against the same target standards
- Deal-level audit trail — every comparison, every flag, every reviewer decision captured

**Time saved:** ~13-18 hours per document set (down from 15-20 hours of manual review to approximately 2 hours of AI processing plus targeted human review of deviations only).

---

### 6. Regulatory Change Monitor

**The business case:** Multi-year, multi-jurisdiction matters — energy projects, infrastructure deals, financial services regulation — are exposed to regulatory change risk across every jurisdiction they touch. A rule change in one jurisdiction can cascade across a portfolio of active engagements. Currently, tracking this is manual: partners read trade publications, associates monitor agency websites, and the firm hopes nothing gets missed. This function makes regulatory monitoring systematic, automated, and tied directly to active matters.

**What it does:** Monitors regulatory sources across jurisdictions, extracts structured changes, maps them to active client matters, and notifies responsible teams.

**Inputs:**
- Regulatory sources (SEC, FTC, ICO, CNIL, EU Official Journal, state AGs, agency guidance, enforcement actions — configurable per firm)
- Active matter data (jurisdiction, practice area, industry, responsible partner)

**Process:**
1. **Scheduled polling** of all configured regulatory sources — daily for high-frequency sources, weekly for lower-priority ones.
2. **Change extraction** via LLM — new publications are compared against the last known state, and structured changes are extracted: what regulation changed, in which jurisdiction, effective when, affecting which industries.
3. **Matter matching** — each regulatory change is matched against active matters by jurisdiction, practice area, and industry.
4. **Severity classification** — core business impact, enforcement surge, approaching deadline, transfer mechanism change.
5. **Notification** — Slack, email, or webhook to the responsible partner and client team.

**Outputs:**
- Structured regulatory update: regulation name, jurisdiction, change type, effective date, summary, affected industries, action required
- Matter impact report: which active matters are affected, severity per matter, compliance deadlines
- Regulatory dashboard: active changes, mapped matters, approaching deadlines, jurisdiction filters

**Value delivered:**
- Regulatory changes that would have been caught weeks later (or missed entirely) are surfaced within 24 hours
- Matter mapping means partners are not reading every regulatory update — the system tells them which ones affect their matters
- Compliance deadlines are tracked and escalated — the system remembers so nobody has to
- For energy, environment, and financial services practices — where regulatory change is the #1 operational risk — this is not a nice-to-have. It is a malpractice prevention tool.

**Time saved:** Effectively infinite (continuous monitoring that is impossible to replicate manually — a human would need to read every regulatory publication from every relevant agency, every day, and cross-reference against every active matter).

---

### 7. KM & Precedent Intelligence

**The business case:** Law firms sell knowledge. The firm's accumulated experience — every brief argued, every deal structured, every contract negotiated — is its most valuable asset. But that asset is currently stored in partner memory and individual document silos. When an associate needs to know "have we done this before, and what did we argue?" — the answer depends on which partner they ask, and whether that partner remembers. This function makes institutional memory searchable in seconds.

**What it does:** Semantic search across the firm's entire knowledge base — briefs, memoranda, deal summaries, reviewed contracts, partner research notes. Clause libraries that learn from every reviewed contract.

**Inputs:**
- Natural-language query (e.g., "Have we done a cross-border M&A deal involving German manufacturing assets where the target had pending environmental litigation?")
- Optional filters: practice area, document type, date range, client, author

**Process:**
1. **Query refinement** via LLM — expands the natural-language query to include synonyms, related concepts, and jurisdiction-specific variants.
2. **Semantic search** across the vector index — finds documents that are conceptually similar, not just keyword matches.
3. **Source enrichment** — matching documents are enriched with metadata: how this document was used in past matters, what decisions it informed, what outcomes it contributed to.
4. **Results ranking** by relevance, recency, and usage history.

**Outputs:**
- Ranked search results with: matching text excerpt, source document name, date, practice area, author, matter context
- "How this was used" summary — if the source was a past analysis, what decision did it inform?
- Related documents — documents frequently referenced together with the matched results
- Practice area and date range filters for refinement

**Value delivered:**
- "Have we done this before?" answered in seconds, not by hoping the right partner is available
- Associates can find precedent without knowing which partner worked on which deal in which year
- The firm's knowledge compounds instead of walking out the door when partners retire
- Post-merger knowledge unification — when two firms become one, two centuries of institutional memory become searchable as a single corpus
- Clause libraries that learn: every analyzed contract enriches the knowledge base — not just the text, but how it was classified, what risks were flagged, what negotiation position was taken, and how it resolved

**Time saved:** ~30-60 minutes per research query (down from asking multiple partners, searching multiple document systems, and manually reviewing results — to a single query returning ranked, contextualized results in seconds).

---

### 8. Client Value Reporting

**The business case:** 85% of clients say firms should disclose when AI is used on their matters. This is simultaneously a compliance obligation and a competitive opportunity. The firms that can say "here is exactly what AI saved you this quarter, with the audit trail to prove it" will retain and win more business than the firms that cannot answer the question. This function turns the disclosure obligation into a retention asset.

**What it does:** Generates client-facing quarterly reports demonstrating measurable AI value — fully backed by the audit trail.

**Inputs:**
- Client ID and reporting period
- Configurable time-saved baselines (per function, per client)
- Configurable cost baselines (hourly rates, overhead multipliers)

**Process:**
1. **Data aggregation** across all function databases — every invocation logged with client_id, matter_id, function_id, timestamps, tokens, scores, and processing time.
2. **Time-saved calculation** — for each invocation: actual processing time subtracted from the configured manual-equivalent baseline.
3. **Cost-avoided calculation** — time saved multiplied by the configured hourly rate.
4. **Risk distribution** — risk levels across all matters processed for the client.
5. **Governance documentation assembly** — model governance summary, ABA 512 compliance statement, data privacy architecture, confidentiality architecture.
6. **Report generation** — structured report with executive summary, metrics overview, function-by-function breakdown, governance documentation, and audit trail samples.

**Outputs:**
- **Executive summary:** One page. Total matters processed. Total time saved. Total cost avoided. Highlight metrics.
- **Function-by-function breakdown:** Per function: invocations, time saved, risk distribution, model used.
- **Governance documentation:** Model governance summary. ABA 512 compliance statement. Data privacy and confidentiality architecture. SOC 2 / ISO 42001 compliance status.
- **Audit trail sample:** Representative examples showing the full decision chain — input, AI reasoning, programmatic scoring, human review decision.

**Value delivered:**
- Client trust: "Here is what AI saved this quarter, with the audit trail to prove it" is a more compelling client conversation than "we use AI responsibly"
- RFP response: governance documentation is pre-assembled — responding to a client's AI use questionnaire is pulling a report, not scrambling to write one
- Internal accountability: the same reports that go to clients go to the managing partner and practice group leaders — AI value is measured, not asserted
- Competitive differentiation: when 85% of clients want AI disclosure and 85% of firms cannot prove AI ROI, the firm that can do both wins

---

### 9. AI Maturity Assessment

**The business case:** Before deploying AI, a firm needs to understand where it stands — across governance, technology, data, culture, and process. Most firms skip this step and wonder why adoption stalls. The maturity assessment provides a baseline measurement and a prioritized improvement roadmap.

**What it does:** Evaluates organizational AI readiness across five dimensions, producing a scored assessment with gap analysis and prioritized recommendations.

**Process:**
1. **Assessment input** — organizational context, current AI usage, governance posture, technology inventory
2. **Multi-dimension scoring** — Governance, Technology, Data, Culture, Process — each scored against a defined maturity rubric
3. **Gap analysis** — where the organization is vs. where it needs to be for each dimension
4. **Recommendations** — prioritized by impact and feasibility

**Value delivered:**
- Baseline measurement before AI investment — you cannot improve what you have not measured
- Identifies the specific blockers to adoption before they become expensive surprises
- Provides the K&I PM with an evidence-backed roadmap for the first 90 days

---

## How It All Connects

### The Function Pipeline

Every function invocation flows through the same governed pipeline:

```
Input → Router (classify) → Evaluator (reason) → Programmatic Scoring (judge) → Metrics Capture (measure) → Audit Trail (record)
```

The LLM provides reasoning. The system provides judgment. Never the reverse.

### The Harvey Evaluation Loop

Harvey agents deploy through Technology. Legal-OS pulls their outputs into an independent evaluation pipeline:

```
Harvey Agent (external, Technology-owned)
  → Legal-OS Ingest (user prompt + Harvey response)
  → 4 Parallel Evaluators (Accuracy, Safety, Bias, Compliance)
  → Weighted Scoring Engine (Tier 1 at 1.5x, Tier 2 at 1.0x, veto at 75)
  → Certification (Platinum → Bronze)
  → Drift Detection (weekly baseline comparison, 6 drift types)
  → Alerts (if drift > 50, severity: moderate → high → critical)
  → Dashboard (scores feed into portfolio view)
  → Client Reports (certification status included in governance pack)
```

**Technology owns the agent. Legal-OS owns the measurement.** Harvey cannot grade its own homework — the same system that generates an output cannot reliably evaluate that output. Legal-OS provides the independent evaluation layer.

### The Help System Loop

```
User question
  → Voyage AI embedding (512-dim)
  → pgvector similarity search (match_help_chunks, threshold 0.3)
  → Top 5 document chunks as context
  → LLM generates answer with source references
  → Fallback: local FAQ keyword matching if API unreachable
  → Feedback: thumbs up/down on every answer
```

### The Data Flow

```
AI Functions → invocation telemetry → ROI Framework
ROI Framework → aggregated metrics → Portfolio Dashboard
Harvey Monitor → evaluation scores → Dashboard + Client Reports
Dashboard + ROI → quarterly aggregation → Client Value Reports
POC Pipeline → project status → Dashboard
Governance → wraps every invocation → Audit Trail (append-only)
```

---

## Enterprise Infrastructure

**Deployed:** Backend on Fly.io (`legal-os-api.fly.dev`), frontend on Vercel (`legal.sickofancy.ai`). Supabase PostgreSQL with pgvector for embeddings and RLS for client isolation. DeepSeek as default LLM provider (~10x cheaper than Claude), Anthropic as preferred evaluation provider with automatic fallback.

**Test coverage:** 52 backend tests passing (31 ROI framework, 21 Harvey monitor). 18 E2E Playwright tests. Zero TypeScript errors.

**Provider resilience:** The Harvey evaluator tries Anthropic (Claude) first for evaluation quality. On any auth or key error, it automatically falls back to the configured default provider (DeepSeek). Evaluations complete successfully regardless of which provider is available.

Data isolation is structural, not procedural. Every row in every table has a client_id column. PostgreSQL Row-Level Security policies enforce client_id = current_user_client_id(). Additional RLS policies scope by practice group. Employment legal is walled from commercial legal at the database layer. Audit records are append-only — write once, read by authorized roles, never modified, never deleted.

---

## The Numbers

| Metric | Before | After |
|--------|--------|-------|
| Matter intake evaluation | 30 min (attorney) | <10 sec (AI + review) |
| Contract review | 2 hrs (full review) | ~45 sec AI + targeted human review |
| Due diligence (per doc set) | 15-20 hrs | ~2 hrs AI + deviation review |
| Separation agreement drafting | 2-4 hrs | ~30 sec AI + attorney review |
| Legal metrics query | 30-60 min (manual pulls) | Seconds (natural language) |
| Regulatory monitoring | Impossible (continuous) | Automated daily |
| Precedent search | 30-60 min (ask around) | Seconds (semantic search) |
| Client value report | Days (manual assembly) | Minutes (automated generation) |

**Annual impact estimate for a firm processing 5,000 matters, 10,000 contracts, and 50 due diligence deals per year:**

- Attorney time saved: ~35,000 hours
- Cost avoided (at blended rate): ~$17.5M
- Risk reduced: conflicts flagged before engagement, regulatory changes surfaced within 24 hours, every decision auditable
- Competitive advantage: provable AI ROI when 85% of peer firms cannot produce the numbers

---

Built by [Charlie Fuller](https://github.com/motorthings). Governance-first. Deterministic over LLM. Harvey can't grade its own homework — the audit trail is the product.
