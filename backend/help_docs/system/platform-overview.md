# Legal AI OS Platform Overview

Legal AI OS is a governed AI platform for legal enterprises operating across five layers.

## Architecture

### Layer 0: Knowledge Foundation
Client documents, precedents, playbooks, regulatory sources, and organizational context. RLS-enforced walls between clients. Vector-indexed for semantic search.

### Layer 1: Governance & Trust
- **Audit Trail** — Every LLM call, every decision, every override is recorded
- **Explainability** — LLM provides reasoning; system provides judgment
- **Traceability** — Full lineage from input to output to attorney review
- **Confidentiality** — Row-Level Security enforces client data isolation
- **Human-in-the-Loop Gating** — Configurable thresholds for mandatory human review
- **Compliance Readiness** — ABA Formal Opinion 512, SOC 2, ISO 42001 alignment

### Layer 2: Legal AI Functions (8 POC Demos)
Matter Intake, Contract Review, Employment, Due Diligence, Regulatory Monitor, KM Intelligence, Value Reporting, Cowork Legal Plugin, AI Maturity Assessment

### Layer 3: Program Operations
- **Portfolio Dashboard** — Hours saved, cost avoided, net ROI, adoption
- **ROI Framework** — Cost impact (time × rate), quality metrics, adoption tracking
- **POC Pipeline** — Kanban board: Discovery → Build → Review → Graduated/Cancelled
- **Harvey Agent Monitoring** — 4-dimension independent evaluation + drift detection
- **Enablement Kit** — Workshop materials, prompt guides, adoption playbook, client conversation pack

### Layer 4: Organizational Model
K&I Program Manager role definition, interface maps (Technology, L&D, Pricing/LPM, Client Teams), 12-month success metrics, legal business fluency checklist.

## Pipeline Pattern

Every function follows the same governed pipeline:

```
Input → Router (classify) → Evaluator (reason) → Scoring (judge) → Audit Trail (record)
```

The LLM provides reasoning. The system provides judgment. Never the reverse. Every decision is auditable, explainable, and traceable — by architecture, not by policy.

## Key Design Decisions

- **No client data used for training** — The LLM provider (DeepSeek) does not train on API data
- **RLS-enforced client isolation** — Technical walls, not policy promises
- **Programmatic scoring** — The system never trusts an LLM's self-assessment
- **Calibrated baselines** — Every time-saved number has a documented methodology
- **Independent evaluation** — Harvey outputs are scored by separate evaluator agents, not Harvey itself
