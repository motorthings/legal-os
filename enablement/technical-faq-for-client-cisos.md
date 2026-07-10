# Technical FAQ for Client CISOs & Security Teams

Deep technical answers for the client-side security professional who asks the questions the relationship partner can't answer.

---

## Architecture Overview

```
Client Document → Enterprise API (TLS 1.3) → LLM Provider
                         ↓
                  Firm Infrastructure
                  (Vector DB, RAG, Audit)
                         ↓
                  Attorney Review
                         ↓
                  Client Deliverable
```

All processing occurs within the firm's controlled infrastructure or through enterprise API endpoints with contractual data protection. No client data traverses the public internet unencrypted. No client data touches consumer AI services.

---

## Q: How do you guarantee our data isn't used to train AI models?

**Answer:**

All LLM providers operate under enterprise agreements with contractual zero-data-retention (ZDR) clauses. Specifically:

- **API-level guarantee:** Data submitted via API is not used for model training. This is a contractual term, not a setting that can be toggled off. Unlike consumer products (ChatGPT, Claude free tier) where data may be retained and used for training, enterprise API endpoints are architecturally separated from training pipelines.

- **Immediate purge:** Prompt and response data are deleted from provider servers immediately after response generation. Agent state is scoped to the session and purged on teardown.

- **Auditable:** We maintain logs of every API call including timestamps, model version, and confirmation of ZDR compliance. These logs are available for audit.

- **BYOK where applicable:** Vector databases can deploy in customer-controlled cloud buckets with customer-managed encryption keys.

---

## Q: How do you prevent prompt injection attacks?

**Answer:**

- All AI inputs are sanitized and validated before processing
- System prompts are immutable — user inputs cannot override system-level instructions
- Rate limiting and anomaly detection at the API layer
- Attorneys review every AI output before it reaches the client — injected content would be identified during human review
- Full audit trail captures the exact prompt submitted and the exact response returned, enabling forensic investigation of any anomalous output

---

## Q: What happens to our data after the engagement ends?

**Answer:**

- **LLM provider:** No data retained — ZDR ensures data is purged immediately after response generation
- **Firm systems:** Client data retained per the firm's document retention policy and any client-specific requirements in the engagement letter
- **Vector databases:** Client-specific embeddings can be deleted on request
- **Audit trail:** Audit records are immutable and retained per regulatory requirements. Client-specific audit records can be exported and provided to the client upon request

---

## Q: How is client data isolated between matters?

**Answer:**

Row-Level Security (RLS) at the database layer enforces:

- `client_id` column on every database row
- PostgreSQL RLS policies: `client_id = current_user_client_id()`
- Additional scoping by practice group
- Employment legal data is structurally walled from commercial legal data
- API-level: vector searches are scoped by client_id — Client A's documents cannot appear in Client B's search results

This is structural, not procedural. It is enforced by the database, not application logic.

---

## Q: What certifications and audits do you maintain?

**Answer:**

- SOC 2 Type 2 — security, availability, confidentiality
- ISO 27001 certified
- ISO 42001 (AI Management System) aligned
- EU AI Act compliance program
- ABA Formal Opinion 512 compliance
- Regular third-party penetration testing
- Vendor security assessments of all AI providers

Audit reports and certifications available under NDA.

---

## Q: What models do you use, and can we restrict which models process our data?

**Answer:**

We use a multi-model architecture primarily through Harvey, which routes tasks across Anthropic, OpenAI, and Gemini models based on task requirements and client conflict considerations.

Clients may request restrictions on specific model providers. We can accommodate model-provider restrictions where they do not conflict with other client obligations. Discuss with your relationship partner.

---

## Q: How do you handle international data residency requirements?

**Answer:**

- Infrastructure deployed in regions matching client requirements
- EU client data processed within EU/EEA infrastructure where required
- Standard Contractual Clauses (SCCs) in place for cross-border data transfers
- Data Processing Agreements (DPAs) available for all clients
- Specific jurisdiction requirements (GDPR, UK DPA 2018, etc.) addressed in engagement terms

---

## Q: Can we audit your AI systems?

**Answer:**

Clients may request:
- AI governance documentation (available on demand)
- Audit trail samples for their matters
- Vendor due diligence summaries for AI providers
- SOC 2 / ISO certification reports (under NDA)

On-site audits and deeper technical reviews can be arranged for strategic client relationships. The audit trail architecture is designed to make compliance evidence exportable in minutes, not weeks.

---

## Q: What's your incident response process for an AI-related security event?

**Answer:**

Standard incident response process applies, with AI-specific additions:

1. **Detection:** Automated monitoring of API calls, anomaly detection on model outputs, and attorney-reported concerns
2. **Containment:** Immediate isolation of affected systems, suspension of AI processing for affected matters if necessary
3. **Investigation:** Full audit trail reconstruction — exact prompt, exact response, model version, all downstream actions
4. **Notification:** Client notification per engagement terms and applicable breach notification laws
5. **Remediation:** Root cause analysis, model or prompt adjustments, process changes
6. **Prevention:** Findings fed back into model governance and quality review pipeline

Because every AI action is logged immutably, forensic investigation is deterministic — we can replay exactly what happened.
