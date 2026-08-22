"""
Prompt construction for simulation agents.

Each agent prompt is built from:
1. Role definition (title, department, KPIs, authority)
2. Psychological profile (OCEAN, biases, motivations, change state)
3. Relationship context (who they trust, who influences them, who they depend on)
4. Environmental context (active events, market conditions, stress level)
5. Workflow context (current step, matter data, previous decisions)
6. Task specification (what they need to decide/do)

The agent never sees the levers or the firm signature directly. It only responds
to its environment, incentives, and constraints — so its behavior is an emergent
consequence of the firm's configuration, not a scripted response to it.
"""

from typing import Optional

from ..models.profiles import Role, PsychologicalProfile, Relationship, CareerStage
from ..models.matters import Matter, WorkflowStep, MatterComplexity
from ..models.metrics import Metric


def build_system_prompt(
    role: Role,
    company_name: str = "Aldrich & Vale LLP",
    env_context: Optional[dict] = None,
    trust_state: Optional[dict] = None,
) -> str:
    """Build the system prompt — the persistent identity layer, constant per role."""
    env = env_context or {}
    trust = trust_state or {}

    parts = []

    # === IDENTITY ===
    parts.append(f"You are {role.name}, {role.title} at {company_name}.")
    parts.append(f"You work in the {role.department} practice.")
    if role.reports_to:
        parts.append(f"You report to {role.reports_to}.")
    if role.direct_reports > 0:
        parts.append(f"You manage {role.direct_reports} direct reports.")
    parts.append("")

    # === WHAT YOU ACTUALLY CARE ABOUT ===
    parts.append("=== WHAT YOU ARE MEASURED ON ===")
    parts.append("Your performance is evaluated on these metrics (ordered by importance):")
    for kpi, weight in sorted(role.kpis.items(), key=lambda x: x[1], reverse=True):
        parts.append(f"  - {kpi}: {weight*100:.0f}% of your performance evaluation")
    parts.append(f"Your annual compensation: ${role.salary_band[0]/1000:.0f}K-${role.salary_band[1]/1000:.0f}K")
    parts.append(f"Variable/origination comp: up to {role.variable_comp_pct*100:.0f}% — tied to your book and realization.")
    parts.append("")

    # === YOUR AUTHORITY AND CONSTRAINTS ===
    parts.append("=== WHAT YOU CAN AND CANNOT DO ===")
    for auth in role.formal_authority:
        parts.append(f"  - {auth}")
    if role.authority_threshold:
        parts.append(f"  - You can make autonomous decisions up to ${role.authority_threshold:,.0f}")
        parts.append(f"  - Above ${role.authority_threshold:,.0f}, you must escalate to {role.reports_to or 'the managing partner'}")
    parts.append("")

    # === YOUR INFORMATION ===
    parts.append("=== WHAT YOU CAN SEE ===")
    for access in role.information_access:
        parts.append(f"  - {access}")
    parts.append("")

    # === PSYCHOLOGICAL PROFILE ===
    parts.append(role.profile.to_system_prompt_fragment())
    parts.append("")

    # === RELATIONSHIPS ===
    from ..models.profiles import get_relationships_for
    relationships = get_relationships_for(role.id)
    if relationships:
        significant = [r for r in relationships if r.trust >= 0.6 or r.influence >= 0.5 or r.dependency >= 0.5]
        if significant:
            parts.append("=== YOUR KEY RELATIONSHIPS ===")
            for rel in significant:
                parts.append(rel.to_prompt_fragment())
            parts.append("")

    # NOTE: Volatile per-sprint state (firm climate, stress, trust) is intentionally
    # NOT in the system prompt — it lives in build_climate_block(), prepended to the
    # task/user message. Keeping the system prompt free of anything that changes
    # per sprint makes it byte-identical across every call for a role, so DeepSeek's
    # automatic prefix cache serves it at the discounted rate instead of re-billing
    # ~1,000 tokens on all 480 matters. The model sees the same information either
    # way — only its position moves.

    # === RESPONSE FORMAT ===
    parts.append("=== HOW YOU COMMUNICATE ===")
    parts.append("Respond only in structured JSON, parsed by the workflow engine — not read by a human.")
    parts.append("Express personality through your decision and reasoning, not alongside them.")

    return "\n".join(parts)


def build_climate_block(
    role: Role,
    env_context: Optional[dict] = None,
    trust_state: Optional[dict] = None,
) -> str:
    """The volatile per-sprint state — firm climate and the agent's state of mind.

    Split out of the system prompt so the system prompt stays cacheable. Prepended
    to the task prompt (user message) at call time."""
    env = env_context or {}
    trust = trust_state or {}
    parts = []

    parts.append("=== CURRENT FIRM CLIMATE ===")
    if env:
        market = env.get("market_phase", "normal")
        parts.append(f"Legal market: {market}")
        parts.append(f"Matter volume is {env.get('matter_volume_factor', 1.0):.1f}x normal")
        parts.append(f"Budget is at {env.get('budget_factor', 1.0)*100:.0f}% of plan")
        parts.append(f"Organizational stress level: {env.get('stress_factor', 1.0):.1f}x normal")
        parts.append(f"Regulatory/ethics scrutiny: {env.get('regulation_factor', 1.0):.1f}x normal")

        if env.get("transformation_paused"):
            parts.append("ALL transformation/change initiatives are currently PAUSED due to external events.")
        if env.get("it_frozen"):
            parts.append("ALL IT changes are FROZEN. No system changes, no deployments, no integrations.")
        if env.get("urgency_elevated"):
            parts.append("Leadership urgency is ELEVATED. There is pressure to show results faster.")

        active_events = env.get("active_event_names", [])
        if active_events:
            parts.append("Active events affecting the firm:")
            for event_name in active_events:
                parts.append(f"  - {event_name}")
    else:
        parts.append("Business as usual. No significant environmental events.")
    parts.append("")

    current_stress = role.profile.ocean.neuroticism / 5.0
    if env:
        current_stress *= env.get("stress_factor", 1.0)
    parts.append(f"Your current stress level: {current_stress:.1f}/1.0")
    parts.append(f"Your current trust in AI systems: {trust.get('confidence', role.profile.change_state.ai_confidence):.1f}/1.0")
    parts.append(f"Your change exhaustion: {role.profile.change_state.change_exhaustion:.0f}/10")
    parts.append("")

    return "\n".join(parts)


def _ai_recommendation(matter, step) -> dict:
    """Produce a concrete AI recommendation for an AI-assisted step, deterministically
    flawed at the step's error rate so agents have something real to accept or override (R3)."""
    import hashlib
    roll = int(hashlib.md5(f"rec:{getattr(matter, 'id', '?')}:{step.name}".encode()).hexdigest()[:8], 16) / (16 ** 8)
    flawed = roll < max(0.05, getattr(step, "ai_error_rate", 0.0) or 0.05)
    dt = step.decision_type
    amt = getattr(matter, "amount_in_dispute", None)
    if dt in ("assess", "verify"):
        proposed = "Accept the inputs as complete and consistent; proceed."
        flag = ("One supporting field looks inferred rather than confirmed — the AI may have "
                "filled a gap it couldn't verify.") if flawed else ""
    elif dt == "approve":
        base = f"Approve at the computed amount{f' (~${amt:,.0f})' if isinstance(amt,(int,float)) else ''}."
        proposed = base
        flag = ("The computed amount sits right at an authority boundary — worth checking "
                "before you sign off.") if flawed else ""
    elif dt in ("classify", "pay"):
        proposed = "Route/process per the standard path for these attributes."
        flag = ("Attributes are borderline between two routes; the AI picked the more common one.") if flawed else ""
    else:
        proposed = "Proceed with the AI-suggested action."
        flag = ("The AI's rationale skips a case-specific factor.") if flawed else ""
    return {"proposed": proposed, "confidence": (0.72 if flawed else 0.93), "flag": flag}


def build_task_prompt(
    role: Role,
    matter: Matter,
    step: WorkflowStep,
    previous_decisions: Optional[list[dict]] = None,
) -> str:
    """Build the task-specific prompt for a single matter + workflow step."""
    parts = []

    parts.append("=== WORKFLOW CONTEXT ===")
    parts.append(f"Current step: {step.name} — {step.description}")
    parts.append(f"Your role in this step: {step.role_responsible}")
    parts.append("")

    # === MATTER DETAILS ===
    parts.append("=== MATTER ===")
    parts.append(f"Matter ID: {matter.id}")
    parts.append(f"Type: {matter.matter_type}")
    parts.append(f"Complexity: {matter.complexity.value}")
    parts.append(f"Amount in dispute: ${matter.amount_in_dispute:,.2f}")
    parts.append(f"Client: {matter.client_name}")
    parts.append(f"Jurisdiction: {matter.jurisdiction}")
    parts.append(f"Privilege involved: {'Yes' if matter.involves_privilege else 'No'}")
    parts.append(f"Prior precedent: {'Yes' if matter.has_prior_precedent else 'No'}")
    parts.append(f"Opposing counsel known: {'Yes' if matter.opposing_counsel_known else 'No'}")
    parts.append(f"Pipeline: {matter.pipeline or 'Not yet assigned'}")
    parts.append(f"Current status: {matter.status.value}")
    parts.append(f"Exceptions raised so far: {matter.exceptions_raised}")
    parts.append("")

    # === PREVIOUS DECISIONS ===
    # Only the most recent few — the accumulated state (exceptions, status) already lives in
    # the matter fields above, so re-sending every prior step's reasoning is redundant and is
    # what blew the prompt to ~6,400 tokens on deep matters. Cap at the last 3.
    if previous_decisions:
        recent = previous_decisions[-3:]
        parts.append(f"=== WHAT HAPPENED BEFORE THIS REACHED YOU ({len(previous_decisions)} prior steps, showing last {len(recent)}) ===")
        for i, decision in enumerate(recent):
            parts.append(f"Step — {decision.get('step', 'unknown')}:")
            parts.append(f"  Agent: {decision.get('agent', 'unknown')}")
            parts.append(f"  Decision: {decision.get('decision', 'unknown')}")
            parts.append(f"  Reasoning: {decision.get('reasoning', 'none provided')[:200]}")
            if decision.get('concerns'):
                parts.append(f"  Concerns raised: {decision['concerns']}")
        parts.append("")

        # === HANDOFF CONTEXT STATE ===
        # Present the *actual* information state of the seam the agent just received,
        # and let the agent react as a real attorney reacts to a clean vs. gappy handoff.
        if getattr(step, "context_complete", True):
            if getattr(step, "handoff_context", None):
                parts.append("=== HANDOFF CONTEXT ===")
                parts.append(f"The handoff into this step is standardized. The following fields were provided:")
                for field in step.handoff_context:
                    parts.append(f"  - {field}")
                parts.append("")
        else:
            parts.append("=== HANDOFF CONTEXT ===")
            parts.append("Handoff context not yet standardized — the following fields are not guaranteed to be present:")
            for field in getattr(step, "handoff_context", []):
                parts.append(f"  - {field}")
            parts.append("")

    # === WHAT YOU NEED TO DECIDE ===
    parts.append("=== YOUR TASK ===")
    parts.append(f"Decision type: {step.decision_type}")
    parts.append(f"Required inputs: {', '.join(step.inputs_required)}")

    # Step-specific authority context
    if step.decision_type in ("assess", "verify"):
        parts.append("Your role here is ASSESSMENT, not final disposition. Your authority is to evaluate accuracy and completeness — dollar thresholds for settlement do NOT apply at this step. Focus on: is the information correct and sufficient for the next step?")
    elif step.decision_type == "approve":
        parts.append("Your role here is APPROVAL. You are deciding whether to sign off on the work product.")
        if role.authority_threshold:
            parts.append(f"If the matter amount exceeds ${role.authority_threshold:,.0f}, you must escalate.")

    pipeline = getattr(matter, 'pipeline', None)
    if pipeline == "tacit":
        parts.append("This is a judgment-led process. No AI assistance is available for this decision. You are making this determination based on your own expertise and the information provided. Your 'used_ai' field should be false.")
    elif step.ai_capable and pipeline in ("codifiable", None):
        parts.append("This step is AI-assisted. An AI recommendation has been pre-computed — review it for accuracy, not authority.")
        parts.append(f"AI confidence threshold for autonomous action: {step.ai_confidence_required:.0%}")
        rec = _ai_recommendation(matter, step)
        parts.append("")
        parts.append("=== AI RECOMMENDATION (pre-computed — your job is to check it) ===")
        parts.append(f"  Proposed: {rec['proposed']}")
        parts.append(f"  AI stated confidence: {rec['confidence']:.0%}")
        if rec["flag"]:
            parts.append(f"  Note: {rec['flag']}")
        parts.append("If the recommendation is sound, accept_ai. If it is wrong, incomplete, "
                     "or unsafe for THIS matter, override_ai and state what you'd do instead.")
    parts.append("")

    # === STRUCTURED RESPONSE FORMAT ===
    # Concise output: reasoning is logged, not read by a human, and the metrics derive from
    # the decision fields — so cap prose hard. Output tokens bill at full rate, and reasoning
    # was the dominant cost on real runs.
    parts.append("=== YOUR RESPONSE (JSON only, terse) ===")
    parts.append("{")
    parts.append('  "decision": "approve|reject|escalate|request_info|defer|accept_ai|override_ai",')
    parts.append('  "reasoning": "1-2 sentences, specific to THIS matter.",')
    parts.append('  "concerns": ["Reservations or risks, if any"],')
    parts.append('  "next_step": "Which workflow step should this matter go to next?",')
    parts.append('  "ai_interaction": {')
    if step.ai_capable:
        parts.append('    "used_ai": true|false,')
        parts.append('    "ai_was_correct": true|false|null,')
        parts.append('    "ai_confidence_in_this_case": 0.0-1.0')
    else:
        parts.append('    "used_ai": false,')
        parts.append('    "ai_was_correct": null,')
        parts.append('    "ai_confidence_in_this_case": null')
    parts.append("  },")
    parts.append('  "emotional_state": {')
    parts.append('    "stress_change": -0.1 to 0.1,')
    parts.append('    "ai_trust_change": -0.1 to 0.1,')
    parts.append('    "note": "One short phrase."')
    parts.append("  }")
    parts.append("}")

    return "\n".join(parts)
