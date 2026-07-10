# RFP Response Templates — AI & Technology Questions

Standard responses for common AI questions in client RFPs and outside counsel guidelines. Adapt per-client. Reference the firm's AI governance framework (published June 29, 2026).

---

## Q: Do you use artificial intelligence in delivering legal services?

**Standard response:**

Yes. Ashurst Perkins Coie uses artificial intelligence to enhance the efficiency, consistency, and quality of legal services delivery. Our AI tools assist with contract review, due diligence, document analysis, matter intake, and regulatory monitoring. All AI outputs are reviewed by a qualified attorney before reaching the client. AI supports our lawyers — it does not replace their judgment.

Clients may request restrictions on AI use for substantive legal work. Foundation AI (embedded in standard productivity tools) generally cannot be disabled on a per-client basis. Our full AI governance framework is available on request.

---

## Q: How do you ensure client confidentiality when using AI?

**Standard response:**

Client confidentiality is governed by architecture, not policy. Our AI infrastructure enforces the following protections:

1. **Zero Data Retention (ZDR):** All AI model providers operate under contractual agreements requiring immediate purging of client data after response generation. No client data is retained, cached, or used for model training.

2. **Row-Level Security:** Database-level access controls ensure Client A's data cannot appear in Client B's AI outputs. Ethical walls between practice groups are enforced structurally.

3. **API-Only Architecture:** Client documents are never processed through consumer-grade AI tools. All AI processing occurs through enterprise API endpoints with contractual data protection guarantees.

4. **Enterprise Infrastructure:** Embedding, analysis, and retrieval run within the firm's controlled infrastructure.

These protections are verified through SOC 2 and ISO 42001-aligned audit processes.

---

## Q: What AI tools do you use, and who are your AI vendors?

**Standard response:**

Our primary AI platform is Harvey, a legal-specific AI platform deployed firmwide. Harvey operates under enterprise agreements providing zero data retention, multi-model routing (to accommodate client conflict-of-interest requirements), and LexisNexis legal research integration.

We also deploy internally-built AI functions for contract review, matter intake, due diligence, and regulatory monitoring. These functions follow the same governance architecture — every decision auditable, explainable, and traceable.

All AI vendors are subject to the firm's vendor due diligence process, including security review, data protection assessment, and contractual zero-data-retention requirements.

---

## Q: How do you measure the value and ROI of your AI investments?

**Standard response:**

We track AI performance across three dimensions:

1. **Time Saved:** Per-matter measurement of AI-assisted task duration vs. calibrated manual baselines. Baselines are established through structured time studies with documented methodology.

2. **Cost Impact:** Time saved × appropriate billing rates = cost avoided. Tracked per function, per practice group, per client, per quarter.

3. **Quality Metrics:** Every AI output is subject to quality review. We track accuracy rate, override rate, false positive/negative rates, and reviewer agreement scores.

These metrics are aggregated into a portfolio dashboard reviewed by firm leadership and reported to clients quarterly. Our ROI tracking framework puts us in the minority of firms that can quantitatively demonstrate AI value — 85% of firms do not track AI ROI.

---

## Q: How do you train your lawyers on AI use?

**Standard response:**

All attorneys receive AI literacy training through our Learning & Development program, developed in partnership with the Knowledge & Innovation team. Training covers:

- LLM fundamentals: what AI can and cannot do
- Prompt engineering for legal tasks
- Confidentiality and security boundaries
- ABA Formal Opinion 512 compliance
- Human review requirements

Practice-group-specific workshops are led by trained AI champions within each group. Adoption is tracked and reported to practice group leadership. Ongoing office hours and feedback channels support continuous improvement.

---

## Q: Can we opt out of AI being used on our matters?

**Standard response:**

Yes. Clients may request restrictions on the use of advanced or specialized AI tools for substantive legal work. Foundation AI (embedded in standard productivity applications) generally cannot be individually disabled. We will confirm any AI-related restrictions in our engagement letter. Please discuss your preferences with your relationship partner.

---

## Q: What happens if AI makes an error on one of our matters?

**Standard response:**

Our AI governance framework ensures that no AI output reaches a client without attorney review. The AI recommends — the attorney decides. If an attorney identifies an error in AI output, it is corrected before any client deliverable is produced, and the error is logged for quality improvement.

Every AI decision is captured in an immutable audit trail: the prompt, the model response, the attorney's review decision, and any overrides. This audit trail is available for client review on request.

---

## Q: How do you handle AI and billing?

**Standard response:**

Per ABA Formal Opinion 512, all fees must be reasonable. When AI reduces the time required for a task, we bill for the actual attorney time spent reviewing and finalizing the output — not the time the AI saved. AI tool costs are treated as firm overhead unless otherwise agreed.

For fixed-fee arrangements, AI efficiency improves delivery speed and consistency while maintaining or improving margin. Our time-tracking frameworks capture the exact impact of AI on each matter, supporting transparent billing and pricing decisions.
