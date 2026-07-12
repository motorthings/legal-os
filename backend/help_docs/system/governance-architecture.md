# Governance Architecture

Legal AI OS governs AI use through five pillars: auditability, explainability, traceability, confidentiality, and human-in-the-loop gating.

## Audit Trail

Every LLM call is recorded with:
- Full prompt and response
- Model, provider, token counts, cost
- Processing time
- Function and user context
- Human override decisions and reasons

The audit trail is append-only. Records cannot be modified or deleted. This means every decision can be reconstructed — what was asked, what was answered, who reviewed it, and what they decided.

## Explainability

The LLM provides reasoning (its analysis of the input). The system provides judgment (the programmatic scoring, risk classification, and escalation decisions). These are kept separate: the LLM's reasoning is recorded for human review but never used as the basis for automated decisions.

## Traceability

Full lineage from input to output to attorney review:
1. Original input (document, query, matter summary)
2. Router classification (practice area, risk level, function routing)
3. Evaluator analysis (LLM reasoning with structured output)
4. Programmatic scoring (risk badge, confidence score, threshold checks)
5. Human review (override, feedback, quality assessment)
6. Final disposition (approved, modified, escalated)

## Confidentiality (RLS)

Supabase Row-Level Security enforces client data isolation at the database level:
- Each client's data is in a separate partition
- RLS policies ensure users can only access their authorized clients' data
- The service role (backend) bypasses RLS but enforces client context in application logic
- No shared embedding indexes across clients

## Human-in-the-Loop Gating

Configurable thresholds determine when human review is mandatory:
- **Auto-escalation confidence** — Escalate if confidence is below this threshold (default: 70)
- **Mandatory review risk level** — Force human review for this risk tier (default: high)
- These thresholds can be adjusted per function, per client

## Compliance Readiness

### ABA Formal Opinion 512

The six duties:
1. **Competence** — Understand the AI tool's capabilities and limitations
2. **Confidentiality** — Protect client information; no training on client data
3. **Communication** — Frame AI output as AI-assisted, not AI-authored legal judgment
4. **Supervision** — Defer to attorney review for case-specific applications
5. **Candor to Tribunal** — Maintain accuracy standards in litigation contexts
6. **Reasonable Fees** — No billing for AI time at attorney rates

### SOC 2 / ISO 42001

The audit trail, RLS architecture, and programmatic governance controls provide evidence for SOC 2 and ISO 42001 compliance assessments. The platform does not self-certify — it provides the evidence framework that auditors review.
