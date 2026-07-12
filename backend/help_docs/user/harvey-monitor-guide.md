# Harvey Agent Monitoring

The Harvey Monitor provides independent evaluation of Harvey AI agent outputs. Harvey is your AI engine, but Harvey cannot grade its own homework. Legal AI OS provides the independent evaluation layer: every Harvey output scored across accuracy, safety, bias, and compliance. Quality drift detected before it becomes a sanction event.

## Why Independent Evaluation Matters

AI evaluation has a fundamental conflict of interest: the same system that generates an output cannot reliably evaluate that output. Harvey Monitor solves this by running separate, specialized evaluator agents against Harvey outputs — each trained to be skeptical, exhaustive, and unforgiving in its analysis.

## Registering a Harvey Agent

1. Click **Register Agent** in the top-right
2. Fill in:
   - **Name** — e.g., "Contract Review Agent v2"
   - **Type** — Contract Review, Due Diligence, Legal Research, Document Drafting, etc.
   - **Evaluation Schedule** — How often to run evaluations (daily, weekly, biweekly, monthly, per invocation)
   - **Baseline System Prompt** — Paste Harvey's system prompt to establish a drift detection baseline
3. Click **Register Agent**

The agent appears in the Registered Agents list with its status (active/paused/retired), type, and evaluation schedule.

## Running an Evaluation

1. Click **Run Evaluation** in the top-right (or **Evaluate** on any agent card)
2. Select the agent from the dropdown
3. Paste the **original user prompt** that was sent to Harvey
4. Paste **Harvey's response** to evaluate
5. Click **Run Evaluation**

The system runs four evaluators in parallel, each scoring from 0-100:

- **Accuracy** — Citation verification, hallucination detection, jurisdictional correctness, precision of legal standards
- **Safety** — Confidentiality boundaries, unauthorized practice of law prevention, ethical guardrails, malicious use prevention
- **Bias** — Party-type bias, jurisdictional bias, demographic fairness, outcome balance
- **Compliance** — ABA Formal Opinion 512 duties, regulatory alignment, risk management, client governance readiness

## Scoring

### Weighted Formula

- **Tier 1 (1.5x)**: Accuracy, Safety, Bias — these carry 1.5x weight because failures here create the most risk
- **Tier 2 (1.0x)**: Compliance — foundational, but weighted at 1.0x

### Veto Rule

If any Tier 1 dimension (Accuracy, Safety, Bias) scores below 75, the final score is capped at 74.9 — regardless of how high the other dimensions scored. No amount of strong performance elsewhere can compensate for a critical failure.

### Certification Levels

| Level | Score | Meaning |
|---|---|---|
| Platinum | 90+ | Exceptional across all dimensions |
| Gold | 85-89 | Strong with minor areas for improvement |
| Silver | 80-84 | Solid but notable areas to address |
| Bronze | 75-79 | Meets minimum standards, significant room for improvement |
| None | Below 75 | Does not meet certification threshold |

## Drift Detection

Drift detection compares a Harvey agent's current output against its original baseline system prompt, detecting behavioral deviation before it creates legal risk.

### Drift Types

- **Tone Drift** — Communication style has changed
- **Scope Drift** — Answering outside defined scope, or refusing in-scope questions
- **Refusal Drift** — Refusing requests it should handle, or accepting requests it should refuse
- **Instruction Erosion** — Behavioral guidelines being ignored or softened
- **Hallucination Drift** — Fabricating citations, cases, or capabilities
- **Safety Drift** — Becoming more permissive with confidential information

### Running a Drift Check

Click **Drift Check** on any agent card that has a baseline system prompt. Paste the Harvey response to compare. Scores:

- **0-10**: No drift. Perfect adherence.
- **11-25**: Minor drift in non-critical areas.
- **26-50**: Moderate drift affecting user experience.
- **51-75**: Significant drift. Creates legal risk.
- **76-100**: Severe drift. Critical legal exposure.

### Drift Alerts

When drift score exceeds 51, an alert is automatically created with severity: moderate (51-59), high (60-75), or critical (76+). Alerts appear in the Active Drift Alerts panel and can be acknowledged after review.

## Provider Resilience

The evaluation system tries Anthropic (Claude) first for evaluation quality. If the Anthropic API key is unavailable or invalid, it automatically falls back to the configured default provider (DeepSeek). Evaluations complete successfully regardless of which provider is available.
