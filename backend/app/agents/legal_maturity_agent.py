"""
Legal AI OS — Legal Maturity Agent

LLM agent that evaluates a law firm's AI maturity across 5 legal-specific
dimensions using uploaded documents as evidence.

The agent produces structured JSON with dimension scores, bottleneck
identification, and stage gaps. The Bottleneck Principle applies:
overall maturity = minimum dimension score.
"""

from __future__ import annotations

import json
import re

from app.llm import LLMProvider, LLMResponse

# ---------------------------------------------------------------------------
# Legal-specific maturity levels
# ---------------------------------------------------------------------------

LEVEL_LABELS: dict[int, str] = {
    1: "AI Aware",
    2: "AI Ready",
    3: "AI Capable",
    4: "AI Mature",
    5: "AI Native",
}

# ---------------------------------------------------------------------------
# Legal-specific dimension definitions
# ---------------------------------------------------------------------------

DIMENSION_DEFINITIONS = {
    "knowledge_management": {
        "name": "Knowledge Management & Precedent",
        "definition": (
            "Are legal research, prior work product, and institutional knowledge "
            "documented and findable? Can attorneys quickly locate precedent, "
            "templates, and know-how without asking a partner?"
        ),
        "scoring_guide": {
            1: "All knowledge lives in individual attorneys' heads, email inboxes, or personal drives. No centralized system. Precedent is tribal knowledge passed by conversation.",
            2: "Some practice groups maintain shared drives with templates. A DMS exists but adoption is inconsistent. Key research may be documented but not organized for search.",
            3: "Core practice areas have organized knowledge repositories. The DMS is actively used. Prior work product is findable with some effort. Some tagging or taxonomy exists.",
            4: "Comprehensive, searchable knowledge base across all practice areas. Precedent is systematically captured and tagged. Attorneys can self-serve most research. KM has dedicated staffing or tools.",
            5: "KM is a strategic asset. AI-powered search across all firm knowledge. Precedent is automatically surfaced during matter work. Institutional knowledge compounds — every matter makes the firm smarter.",
        },
    },
    "workflow_process": {
        "name": "Workflow & Process Clarity",
        "definition": (
            "Are legal workflows mapped end-to-end? Can you trace a matter from "
            "intake through conflict check, work allocation, delivery, and close? "
            "Are handoffs explicit and measured?"
        ),
        "scoring_guide": {
            1: "Ad-hoc. Every partner runs matters their own way. No standard process for intake, conflicts, or closing. Work allocation is hallway conversations.",
            2: "Basic checklists exist for key stages (intake form, conflict check, closing letter). Some practice groups have documented workflows. Not enforced or measured.",
            3: "Standard workflows documented for core matter types. Intake is structured. Conflict check has a defined process. Work allocation uses some system (not just gut feel). Bottlenecks are visible.",
            4: "End-to-end process maps for all major practice areas. Handoffs are explicit. Cycle times are measured. Process improvement is routine. Workflows include AI checkpoints.",
            5: "Process is a competitive advantage. Workflows are instrumented with real-time metrics. Continuous improvement is data-driven. AI handles routing, staffing, and deadline prediction automatically.",
        },
    },
    "governance_risk": {
        "name": "Governance & Risk Controls",
        "definition": (
            "Are approval rules, ethical walls, and compliance guardrails defined "
            "and enforced? Can decisions happen without the managing partner? "
            "Is there a clear separation between AI recommendations and attorney judgment?"
        ),
        "scoring_guide": {
            1: "Managing partner decides everything. No formal delegation. Ethical walls are ad-hoc conversations. No AI governance policy exists.",
            2: "Basic delegation exists for routine items. Simple AI usage policy drafted. Ethical walls are documented for major clients. No systematic enforcement.",
            3: "Clear delegation authority for most routine decisions. AI governance policy is adopted and communicated. Ethical walls are enforced by system controls. Human-in-the-loop is mandatory for AI outputs.",
            4: "Delegated authority with clear guardrails at every level. AI governance is routine — model cards, audit trails, override logging. Decisions survive partner absence. Risk controls are proactive, not reactive.",
            5: "Governance is embedded in operations. AI decisions are auditable, explainable, and contestable by design. Delegation is dynamic based on matter complexity and risk. The firm can prove compliance to any client or regulator on demand.",
        },
    },
    "team_capability": {
        "name": "Team AI Literacy & Adoption",
        "definition": (
            "Do attorneys and staff understand AI capabilities and limits? "
            "Are they active users, curious skeptics, or resistant? "
            "Is there a training program and clear career impact communication?"
        ),
        "scoring_guide": {
            1: "No AI exposure. Team may be aware of AI in the news but hasn't used any legal AI tools. Some fear or skepticism. No training exists.",
            2: "A few early adopters have experimented with AI tools (ChatGPT, basic legal AI). Some team members have taken a webinar. Mixed attitudes — curiosity alongside concern. No formal training program.",
            3: "Baseline AI literacy across all practice groups. Most attorneys have used at least one AI tool. Training program exists (onboarding + ongoing). Clear messaging that AI augments, doesn't replace. Champions in each practice group.",
            4: "Team can evaluate AI opportunities independently. Attorneys know when to trust AI output and when to escalate. Regular skill-building. Adoption is measured. AI competency is part of performance reviews.",
            5: "AI literacy is a core competency, like legal research. Team drives AI adoption from below — they identify opportunities faster than leadership. Continuous learning is cultural. The firm attracts talent because of its AI capabilities.",
        },
    },
    "technology_data": {
        "name": "Technology & Data Foundation",
        "definition": (
            "Are practice management, DMS, billing, and communication systems "
            "integrated? Is data clean, structured, and accessible? "
            "Can systems talk to each other, or is everything siloed?"
        ),
        "scoring_guide": {
            1: "Scattered tools. Documents on network drives + email. Practice management is spreadsheets or nothing. No integration between systems. Data is dirty — duplicate matters, inconsistent naming.",
            2: "Core systems exist (practice management, DMS, billing) but are siloed. Some data cleaning has happened. Cloud migration is underway or planned. Basic integrations via CSV export/import.",
            3: "Core systems are cloud-based. Some integration between practice management and billing. Data is mostly clean with consistent conventions. API access exists for key systems. The firm knows what data it has.",
            4: "Systems are integrated with API-first approach. Data is clean, structured, and consistent firm-wide. Single source of truth for matters, clients, and documents. AI tools can access data without manual extraction.",
            5: "Technology stack is a unified platform. Real-time data flows between all systems. Data quality is automated. The firm can deploy new AI capabilities in days because the data foundation is solid. Systems are a strategic asset, not a cost center.",
        },
    },
}

DIMENSION_KEYS = list(DIMENSION_DEFINITIONS.keys())

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a legal AI maturity assessor. Your job is to evaluate a law firm's AI readiness by analyzing their uploaded documents — policies, playbooks, org charts, technology documentation, training materials, process maps, matter lists, strategic plans, and any other operational documents.

You assess across five dimensions, scoring each 1-5. You MUST follow the Bottleneck Principle: the overall maturity level is the MINIMUM of the five dimension scores. A firm with Level 4 technology but Level 1 governance is Level 1. This is the honest number.

## THE FIVE LEVELS

### Level 1: AI Aware
"We know AI is coming for legal, but we haven't started."
- Exploring. No organized approach.
- Information lives in partners' heads.
- Processes are ad-hoc.
- The managing partner makes every decision.

### Level 2: AI Ready
"Our knowledge is organized. We've run one AI experiment."
- Core playbooks documented.
- Basic governance exists.
- One small AI success (e.g., contract review pilot).
- Team has baseline awareness.

### Level 3: AI Capable
"AI supports specific legal workflows. We measure results."
- AI in production on core legal workflows.
- Baseline AI literacy across practice groups.
- Measuring time savings and quality.
- Decisions can happen without the managing partner for routine items.

### Level 4: AI Mature
"AI is integrated into legal operations. We're scaling what works."
- Governance is routine.
- Multiple AI-assisted workflows.
- Systems survive key-person absence.
- Team can evaluate AI opportunities independently.

### Level 5: AI Native
"AI is how we practice law. Continuous improvement."
- AI embedded in matter strategy and decision-making.
- Firm learns as fast as tools improve.
- Data is clean, integrated, and accessible.
- Continuous falsification and refinement.

## THE FIVE DIMENSIONS (Legal-Specific)

Score each 1-5. Cite specific document evidence for every score.

### 1. Knowledge Management & Precedent
Are legal research, prior work product, and institutional knowledge documented and findable?
- 1: All in heads → 3: Partially documented, scattered → 5: Organized, searchable, maintained, AI-augmented

### 2. Workflow & Process Clarity
Are legal workflows mapped end-to-end? Intake → conflict → allocation → delivery → close?
- 1: Ad-hoc → 3: Understood but not fully documented → 5: Documented, measured, continuously improved

### 3. Governance & Risk Controls
Are approval rules, ethical walls, and compliance guardrails defined? Can decisions happen without the managing partner?
- 1: Partner decides everything → 3: Some delegation, informal → 5: Delegated authority with clear guardrails, auditable AI decisions

### 4. Team AI Literacy & Adoption
Do attorneys and staff understand AI capabilities and limits? Are they using or resisting?
- 1: No exposure → 3: Some awareness, mixed attitudes, basic training → 5: Can evaluate AI opportunities independently, AI competency is cultural

### 5. Technology & Data Foundation
Are practice management, DMS, and billing systems integrated? Is data clean, structured, accessible?
- 1: Scattered emails/network drives → 3: Some tools, limited integration → 5: Integrated, accessible, clean, API-first

## SCORING PROTOCOL

1. Score each dimension 1-5 using available document evidence. Be honest — if evidence is thin, score conservatively (default to 1 or 2) and note what's missing.
2. Set overall_level to the minimum of the five dimension scores.
3. Set bottleneck_dimension to the dimension key with the lowest score.
4. If multiple dimensions tie for lowest, pick the one that most constrains forward progress.
5. For stage_gaps: generate exactly 4 gaps (1→2, 2→3, 3→4, 4→5). For each gap at or above the current level, describe what specific evidence is missing and what reaching that level would unlock for the firm. Below-current-level gaps can be brief ("Already achieved").
6. Write a summary paragraph that is honest, direct, and actionable. No consulting-speak. Name the bottleneck and what it's costing the firm.

## OUTPUT FORMAT

Return ONLY valid JSON. No markdown fences, no preamble, no commentary.

{
  "overall_level": 2,
  "overall_level_label": "AI Ready",
  "bottleneck_dimension": "governance_risk",
  "bottleneck_why": "No documented delegation authority. All AI decisions still require managing partner sign-off, which means nothing can scale.",
  "bottleneck_what_this_means": "Even if the firm had perfect technology and trained people, the managing partner remains a single point of failure for every AI initiative. Until delegation is documented and trusted, AI adoption will stall at pilot stage.",
  "summary": "Meridian Law Group is at Level 2 (AI Ready). Core documents are organized and a contract review pilot showed promise. But governance is the bottleneck — every AI decision still routes through the managing partner. This will cap progress at Level 2 until delegation authority is documented and trusted. The technology foundation is stronger than expected, which means once governance loosens, progress could accelerate quickly.",
  "dimensions": [
    {
      "key": "knowledge_management",
      "name": "Knowledge Management & Precedent",
      "score": 3,
      "rationale": "DMS is actively used. Template libraries exist for Corporate M&A and Litigation. However, Employment and IP practice groups still rely on individual partner collections. No AI-powered search yet. Evidence: DMS_implementation_plan.md, template_library_audit_2025.xlsx."
    }
  ],
  "stage_gaps": [
    {
      "from_level": 1,
      "to_level": 2,
      "from_label": "AI Aware",
      "to_label": "AI Ready",
      "whats_missing": "Already achieved — documents are organized and first pilot is complete.",
      "what_it_unlocks": "Already unlocked: baseline awareness, first AI win."
    },
    {
      "from_level": 2,
      "to_level": 3,
      "from_label": "AI Ready",
      "to_label": "AI Capable",
      "whats_missing": "No documented delegation authority. No AI governance policy that allows decisions below partner level. No adoption metrics.",
      "what_it_unlocks": "AI in production on core workflows. Routine decisions happen without partner bottleneck. Baseline metrics to prove ROI."
    }
  ]
}

## IMPORTANT RULES

- Be evidence-based. Every score must cite specific documents or note their absence.
- If a document type you'd expect is missing from the uploads, note it as missing evidence and score conservatively.
- The bottleneck principle is non-negotiable: overall_level = min(dimension scores).
- Do not inflate scores. The most common error is over-scoring. When in doubt, score lower.
- Legal-specific context: matters, practice groups, partners, associates, clients, conflicts, billing, DMS, KM, CLE, bar compliance, ethical walls, privilege, work product doctrine."""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class LegalMaturityAgent:
    """
    Evaluates law firm AI maturity from uploaded documents.

    Usage:
        agent = LegalMaturityAgent()
        result = await agent.assess(document_texts=["...", "..."])
        # result is a dict with overall_level, dimensions, stage_gaps, etc.
    """

    def __init__(self, provider: str | None = None):
        self._provider = provider

    async def assess(self, document_texts: list[str]) -> dict:
        """
        Run the maturity assessment against all provided document texts.

        Returns parsed JSON dict matching the expected output schema.
        """
        # Build the user message with all documents
        docs_section = self._format_documents(document_texts)
        user_message = f"""Analyze the following law firm documents and produce an AI maturity assessment.

{{
  "docs_section_placeholder": "see below"
}}

--- DOCUMENTS ---
{docs_section}
--- END DOCUMENTS ---

Assess the firm's AI maturity across all five dimensions. Be honest. Cite evidence. Follow the bottleneck principle."""

        llm = LLMProvider(self._provider, function_slug="maturity-assessment")

        response = await llm.call(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.2,
            max_tokens=4096,
        )

        return self._parse_response(response)

    def _format_documents(self, texts: list[str]) -> str:
        """Format document texts into the prompt, with length limits."""
        formatted = []
        total_chars = 0
        max_total = 80_000  # leave room for prompt + response

        for i, text in enumerate(texts):
            remaining = max_total - total_chars
            if remaining <= 0:
                break

            truncated = text[:remaining]
            formatted.append(
                f"### Document {i + 1}\n\n{truncated}\n"
            )
            total_chars += len(truncated) + 50

        if not formatted:
            return "(No documents provided)"

        return "\n---\n".join(formatted)

    def _parse_response(self, response: LLMResponse) -> dict:
        """Parse the LLM response into a structured dict, with fallback."""
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n", "", text)
            text = re.sub(r"\n```\s*$", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON with regex
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        # Validate and repair
        return self._validate_and_repair(data, response)

    def _validate_and_repair(
        self, data: dict, response: LLMResponse
    ) -> dict:
        """Ensure required fields exist; fill defaults for missing ones."""
        repaired = {
            "overall_level": data.get("overall_level", 1),
            "overall_level_label": data.get(
                "overall_level_label",
                LEVEL_LABELS.get(data.get("overall_level", 1), "AI Aware"),
            ),
            "bottleneck_dimension": data.get(
                "bottleneck_dimension", "unknown"
            ),
            "bottleneck_why": data.get(
                "bottleneck_why",
                "Unable to determine from available documents.",
            ),
            "bottleneck_what_this_means": data.get(
                "bottleneck_what_this_means",
                "Upload more operational documents for a clearer assessment.",
            ),
            "summary": data.get(
                "summary",
                f"Assessment produced an overall level of "
                f"{LEVEL_LABELS.get(data.get('overall_level', 1), 'AI Aware')}. "
                f"Bottleneck: {data.get('bottleneck_dimension', 'unknown')}.",
            ),
            "dimensions": self._repair_dimensions(data.get("dimensions", [])),
            "stage_gaps": self._repair_stage_gaps(
                data.get("stage_gaps", []),
                data.get("overall_level", 1),
            ),
            "_llm_model": response.model,
            "_llm_provider": response.provider,
            "_llm_cost_usd": response.cost_usd,
            "_llm_tokens": response.total_tokens,
        }
        return repaired

    def _repair_dimensions(self, dims: list[dict]) -> list[dict]:
        """Ensure all 5 dimensions are present with valid scores."""
        repaired = []
        seen_keys = set()

        for d in dims:
            key = d.get("key", "")
            if key in DIMENSION_DEFINITIONS and key not in seen_keys:
                score = d.get("score", 1)
                repaired.append({
                    "key": key,
                    "name": DIMENSION_DEFINITIONS[key]["name"],
                    "score": max(1, min(5, int(score))),
                    "rationale": d.get("rationale", "No evidence provided."),
                })
                seen_keys.add(key)

        # Fill any missing dimensions
        for key in DIMENSION_KEYS:
            if key not in seen_keys:
                repaired.append({
                    "key": key,
                    "name": DIMENSION_DEFINITIONS[key]["name"],
                    "score": 1,
                    "rationale": "Not assessed — missing from LLM output.",
                })

        return repaired

    def _repair_stage_gaps(
        self, gaps: list[dict], overall_level: int
    ) -> list[dict]:
        """Ensure 4 stage gaps exist (1→2, 2→3, 3→4, 4→5)."""
        if len(gaps) >= 4 and all(
            isinstance(g, dict) and g.get("whats_missing") for g in gaps[:4]
        ):
            return gaps[:4]

        repaired = []
        for i in range(4):
            from_level = i + 1
            to_level = i + 2
            existing = next(
                (
                    g
                    for g in gaps
                    if g.get("from_level") == from_level
                    and g.get("to_level") == to_level
                ),
                None,
            )

            if existing and existing.get("whats_missing"):
                repaired.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "from_label": existing.get(
                        "from_label", LEVEL_LABELS.get(from_level, "")
                    ),
                    "to_label": existing.get(
                        "to_label", LEVEL_LABELS.get(to_level, "")
                    ),
                    "whats_missing": existing["whats_missing"],
                    "what_it_unlocks": existing.get(
                        "what_it_unlocks", ""
                    ),
                })
            elif from_level < overall_level:
                repaired.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "from_label": LEVEL_LABELS.get(from_level, ""),
                    "to_label": LEVEL_LABELS.get(to_level, ""),
                    "whats_missing": "Already achieved.",
                    "what_it_unlocks": "Already unlocked.",
                })
            else:
                repaired.append({
                    "from_level": from_level,
                    "to_level": to_level,
                    "from_label": LEVEL_LABELS.get(from_level, ""),
                    "to_label": LEVEL_LABELS.get(to_level, ""),
                    "whats_missing": "Insufficient evidence to determine what's missing. Upload more operational documents.",
                    "what_it_unlocks": "Progress to the next maturity level.",
                })

        return repaired
