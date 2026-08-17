"""
Agent runtime for the simulation.

Each agent is an LLM call wrapped with persistent state.
Agents do NOT know which track they're in — they respond to their
environment, incentives, psychological profile, and the matter in front of them.

Key design decisions:
- Agents are stateless in the LLM sense (each call is independent)
- Structured state (trust, stress, exhaustion) is maintained externally
- Agent decisions are typed JSON responses, validated and parsed
- Psychological profile affects behavior through prompt construction,
  not through post-hoc modification of the decision
"""

import json
import re
import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Any

from ..models.profiles import Role, PsychologicalProfile
from ..models.matters import Matter, WorkflowStep, MatterStatus
from ..models.metrics import MetricSnapshot
from .prompts import build_system_prompt, build_task_prompt, build_climate_block
from .dynamics import TrustState


def _extract_json_object(text: str) -> str:
    """Return the first balanced {...} object in `text`, or raise ValueError.

    Belt-and-suspenders for a model that prefixes the JSON with prose. Tracks brace
    depth while respecting string literals and escapes so braces inside strings don't
    fool it."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found")
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    raise ValueError("unbalanced JSON object")


@dataclass
class AgentDecision:
    """A structured decision produced by an agent for a single matter."""
    matter_id: str
    step_name: str
    agent_role_id: str
    agent_name: str
    track: str  # "A" or "B" — for logging only, agent doesn't use this

    decision: str  # "approve", "reject", "escalate", "request_info", "defer", "accept_ai", "override_ai"
    reasoning: str
    concerns: list[str] = field(default_factory=list)
    next_step: Optional[str] = None

    # AI interaction
    used_ai: bool = False
    ai_was_correct: Optional[bool] = None
    ai_confidence: Optional[float] = None

    # Agent's emotional response to this decision
    stress_delta: float = 0.0       # -1.0 to 1.0
    ai_trust_delta: float = 0.0     # -1.0 to 1.0
    emotion_note: str = ""

    # Metadata
    processing_time_sprints: float = 0.0
    exception_raised: bool = False
    # R2: translation_incident is STATE-DERIVED (the handoff into this step was not
    # standardized: not step.context_complete). This makes translation debt respond
    # mechanically to seam completion (the codify_seams lever) and stay stable across seeds,
    # instead of depending on incidental word choice in the LLM's prose.
    translation_incident: bool = False  # structural: received an incomplete/gappy handoff
    translation_incident_prose: bool = False  # secondary: reasoning had reconciliation language
    surfaced_gap: bool = False  # did the agent notice missing/unclear context (Type 2 emergence)?

    # Full LLM trace (raw prompt + response) — empty for mock runs, populated on real LLM.
    raw_prompt: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "matter_id": self.matter_id,
            "step_name": self.step_name,
            "agent_role_id": self.agent_role_id,
            "agent_name": self.agent_name,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "concerns": self.concerns,
            "next_step": self.next_step,
            "used_ai": self.used_ai,
            "ai_was_correct": self.ai_was_correct,
            "ai_confidence": self.ai_confidence,
            "stress_delta": self.stress_delta,
            "ai_trust_delta": self.ai_trust_delta,
            "emotion_note": self.emotion_note,
            "exception_raised": self.exception_raised,
            "translation_incident": self.translation_incident,
            "translation_incident_prose": self.translation_incident_prose,
            "surfaced_gap": self.surfaced_gap,
            "raw_prompt": self.raw_prompt,
            "raw_response": self.raw_response,
        }


@dataclass
class AgentState:
    """Mutable state for a single agent, evolving over the simulation."""
    role_id: str
    stress: float                        # 0-1, starts from neuroticism / 5
    ai_confidence: float                  # 0-1, trust in AI systems
    change_exhaustion: float              # 0-10
    decisions_made: int = 0
    positive_ai_experiences: int = 0
    negative_ai_experiences: int = 0
    neutral_ai_experiences: int = 0
    exceptions_handled: int = 0
    translation_incidents: int = 0        # times this agent had to repair meaning
    matters_processed_this_sprint: int = 0
    active: bool = True                   # False if departed

    def update_from_decision(self, decision: AgentDecision):
        """Update agent state based on a single decision."""
        self.decisions_made += 1
        self.matters_processed_this_sprint += 1

        # Stress update — capped at [0, 1]
        self.stress = max(0.0, min(1.0, self.stress + decision.stress_delta))

        # AI trust update — capped at [0, 1]
        self.ai_confidence = max(0.0, min(1.0, self.ai_confidence + decision.ai_trust_delta))

        # Record AI experience quality
        if decision.used_ai:
            if decision.ai_was_correct is True:
                self.positive_ai_experiences += 1
            elif decision.ai_was_correct is False:
                self.negative_ai_experiences += 1
            else:
                self.neutral_ai_experiences += 1

        if decision.exception_raised:
            self.exceptions_handled += 1
        if decision.translation_incident:
            self.translation_incidents += 1
            # Friction erodes trust — a translation incident is a negative AI experience
            self.negative_ai_experiences += 1

    def reset_sprint_counters(self):
        """Reset per-sprint counters at the start of each sprint."""
        self.matters_processed_this_sprint = 0
        self.positive_ai_experiences = 0
        self.negative_ai_experiences = 0
        self.neutral_ai_experiences = 0

    def summary(self) -> str:
        return (
            f"{self.role_id}: stress={self.stress:.2f}, ai_trust={self.ai_confidence:.2f}, "
            f"exhaustion={self.change_exhaustion:.1f}, decisions={self.decisions_made}, "
            f"ai_exp=+{self.positive_ai_experiences}/-{self.negative_ai_experiences}/~{self.neutral_ai_experiences}"
        )


@dataclass
class AgentStates:
    """Collection of all agent states for one track."""
    states: dict[str, AgentState] = field(default_factory=dict)

    def get(self, role_id: str) -> Optional[AgentState]:
        return self.states.get(role_id)

    def get_or_create(self, role_id: str, role: Role) -> AgentState:
        if role_id not in self.states:
            self.states[role_id] = AgentState(
                role_id=role_id,
                stress=role.profile.ocean.neuroticism / 5.0,
                ai_confidence=role.profile.change_state.ai_confidence,
                change_exhaustion=role.profile.change_state.change_exhaustion,
            )
        return self.states[role_id]

    def reset_all_sprint_counters(self):
        for state in self.states.values():
            state.reset_sprint_counters()

    def all_active(self) -> list[AgentState]:
        return [s for s in self.states.values() if s.active]

    def to_trust_state(self) -> TrustState:
        """Convert to TrustState for cascade propagation."""
        ts = TrustState()
        for role_id, state in self.states.items():
            ts.confidence[role_id] = state.ai_confidence
        return ts

    def update_from_trust_state(self, ts: TrustState):
        """Pull updated trust values back from cascade propagation."""
        for role_id, confidence in ts.confidence.items():
            if role_id in self.states:
                self.states[role_id].ai_confidence = confidence


class AgentRuntime:
    """
    Manages agent lifecycle: receiving workflow events, producing decisions,
    and updating agent state.
    """

    def __init__(self, track: str, states: AgentStates):
        self.track = track
        self.states = states
        # E1 — system-prompt cache. The system prompt depends only on (role, sprint,
        # trust-snapshot); trust is snapshotted per batch, so it's constant within a sprint.
        # Rebuilding it for every one of ~thousands of matter-steps is wasted work and defeats
        # provider prefix-caching. Key on (role_id, sprint, rounded confidence).
        self._sys_prompt_cache: dict = {}

    async def process_matter_step(
        self,
        role: Role,
        matter: Matter,
        step: WorkflowStep,
        previous_decisions: list[dict],
        env_params: dict,
        llm_call: callable,
        semaphore: Optional[asyncio.Semaphore] = None,
        trust_snapshot: Optional[dict] = None,
    ) -> AgentDecision:
        """
        Process one matter through one workflow step with one agent.
        """
        agent_state = self.states.get_or_create(role.id, role)

        if trust_snapshot is not None:
            confidence = trust_snapshot.get(role.id, agent_state.ai_confidence)
        else:
            confidence = agent_state.ai_confidence

        # The system prompt holds only static, per-role content now, so it's identical
        # across every sprint and matter for a role — cache on role.id alone. Volatile
        # state (climate, stress, trust) moved to the user message via build_climate_block.
        system_prompt = self._sys_prompt_cache.get(role.id)
        if system_prompt is None:
            system_prompt = build_system_prompt(role=role)
            self._sys_prompt_cache[role.id] = system_prompt
        climate_block = build_climate_block(
            role=role,
            env_context=env_params,
            trust_state={"confidence": confidence},
        )
        task_prompt = build_task_prompt(
            role=role,
            matter=matter,
            step=step,
            previous_decisions=previous_decisions,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": climate_block + "\n" + task_prompt},
        ]

        try:
            if semaphore is not None:
                async with semaphore:
                    raw_response = await asyncio.to_thread(llm_call, messages)
            else:
                raw_response = await asyncio.to_thread(llm_call, messages)
            decision = self._parse_decision(raw_response, role, matter, step)
            decision.raw_prompt = json.dumps(messages)
            decision.raw_response = raw_response
        except Exception as e:
            # Keep the prompt AND the raw response even on failure — discarding them
            # here is what hid a ~90% parse-failure rate on the v4 runs (only the 8%
            # that parsed were logged). raw_response is exactly what you need to debug
            # a truncated/empty completion, and to seed replay.
            decision = AgentDecision(
                matter_id=matter.id,
                step_name=step.name,
                agent_role_id=role.id,
                agent_name=role.name,
                track=self.track,
                decision="escalate",
                reasoning=f"LLM call failed: {str(e)}. Escalating to be safe.",
                concerns=["LLM error — manual review required"],
                exception_raised=True,
                raw_prompt=json.dumps(messages),
                raw_response=locals().get("raw_response", "") or "",
            )

        agent_state.update_from_decision(decision)

        # Update matter state
        matter.decisions.append(decision.to_dict())
        if decision.exception_raised:
            matter.exceptions_raised += 1
        if decision.translation_incident:
            matter.translation_incidents += 1

        return decision

    def _parse_decision(
        self,
        raw_response: str,
        role: Role,
        matter: Matter,
        step: WorkflowStep,
    ) -> AgentDecision:
        """Parse the LLM's JSON response into an AgentDecision."""
        json_str = raw_response
        if "```json" in raw_response:
            json_str = raw_response.split("```json")[1].split("```")[0]
        elif "```" in raw_response:
            json_str = raw_response.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_str.strip())
        except json.JSONDecodeError:
            # Fallback: extract the first balanced {...} object from the text. Handles a
            # model that wraps the JSON in prose or a preamble. A genuinely empty/
            # truncated completion still raises here → caught upstream and logged with raw.
            data = json.loads(_extract_json_object(raw_response))

        valid_decisions = {"approve", "reject", "escalate", "request_info", "defer", "accept_ai", "override_ai"}
        decision_str = data.get("decision", "defer")
        if decision_str not in valid_decisions:
            decision_str = "defer"

        concerns = data.get("concerns", [])
        reasoning = data.get("reasoning", "")

        # R2 — STATE-DERIVED translation incident, but PROBABILISTIC per matter. A gappy hand-off
        # (not step.context_complete) garbles SOME matters, not all — the chance scales with the
        # seam's risk score, so debt/redline/handoff read as smooth RATES instead of pegging at
        # 0% or 100%. Deterministic (hash of matter+step, no RNG) to keep runs cross-process
        # reproducible. Codifying the seam (context_complete=True) drops the rate to zero.
        if getattr(step, "context_complete", True):
            translation_incident = False
        else:
            rate = 0.2 + 0.7 * getattr(step, "seam_risk", 0.5)
            roll = int(hashlib.md5(f"seam:{matter.id}:{step.name}".encode()).hexdigest()[:8], 16) / (16 ** 8)
            translation_incident = roll < rate

        translation_keywords = [
            "unclear", "missing information", "doesn't match", "inconsistent",
            "had to reconcile", "assumed", "inferred", "guessed", "wasn't sure",
            "couldn't verify", "conflicting", "ambiguous", "incomplete",
            "not in the system", "had to ask", "needed clarification"
        ]
        translation_incident_prose = any(kw in reasoning.lower() for kw in translation_keywords)

        gap_keywords = [
            "missing information", "incomplete", "not in the system", "couldn't verify",
            "needed clarification", "had to ask", "unclear", "ambiguous", "not guaranteed",
            "assumed", "inferred", "guessed", "wasn't sure",
        ]
        surfaced_gap = (decision_str == "request_info") or any(
            kw in reasoning.lower() for kw in gap_keywords
        )

        exception_raised = decision_str in ("escalate", "request_info", "override_ai")

        emotional = data.get("emotional_state", {})
        ai_interaction = data.get("ai_interaction", {})

        return AgentDecision(
            matter_id=matter.id,
            step_name=step.name,
            agent_role_id=role.id,
            agent_name=role.name,
            track=self.track,
            decision=decision_str,
            reasoning=reasoning,
            concerns=concerns,
            next_step=data.get("next_step"),
            used_ai=ai_interaction.get("used_ai", False),
            ai_was_correct=ai_interaction.get("ai_was_correct"),
            ai_confidence=ai_interaction.get("ai_confidence_in_this_case"),
            stress_delta=max(-0.1, min(0.1, emotional.get("stress_change", 0.0))),
            ai_trust_delta=max(-0.1, min(0.1, emotional.get("ai_trust_change", 0.0))),
            emotion_note=emotional.get("note", ""),
            exception_raised=exception_raised,
            translation_incident=translation_incident,
            translation_incident_prose=translation_incident_prose,
            surfaced_gap=surfaced_gap,
        )


class MockLLM:
    """
    Mock LLM for testing without API calls.
    Produces deterministic decisions based on matter complexity and agent profile.
    Used for baseline validation runs.
    """

    def __init__(self, seed: int = 42):
        import random
        self.rng = random.Random(seed)

    def __call__(self, messages: list[dict]) -> str:
        """Generate a mock decision. Intentionally simple — tests plumbing, not results."""
        user_msg = messages[1]["content"] if len(messages) > 1 else ""

        decision = "approve"
        reasoning = "Routine matter within authority. Standard processing."

        if "=== AI RECOMMENDATION" in user_msg and "\n  Note:" in user_msg:
            decision = "override_ai"
            reasoning = "The AI recommendation is flagged and doesn't hold up for this matter — overriding and handling it myself."
        elif "=== AI RECOMMENDATION" in user_msg:
            decision = "accept_ai"
            reasoning = "The AI recommendation is consistent with the matter; accepting it."
        elif "Handoff context not yet standardized" in user_msg:
            decision = "request_info"
            reasoning = "The handoff is missing information I need to make this decision — requesting the missing context before proceeding."
        elif "Complexity: high_stakes" in user_msg or "Complexity: complex" in user_msg:
            decision = "escalate"
            reasoning = "Complex matter requires senior review."
        elif "Amount in dispute: $" in user_msg:
            import re
            amount_match = re.search(r'Amount in dispute: \$([\d,]+)', user_msg)
            if amount_match:
                amount = float(amount_match.group(1).replace(",", ""))
                if amount > 2_000_000:
                    decision = "escalate"
                    reasoning = f"Matter amount ${amount:,.0f} exceeds standard authority. Escalating."

        response = {
            "decision": decision,
            "reasoning": reasoning,
            "concerns": [],
            "next_step": None,
            "ai_interaction": {
                "used_ai": "This step is AI-assisted" in user_msg,
                "ai_was_correct": None,
                "ai_confidence_in_this_case": None,
            },
            "emotional_state": {
                "stress_change": 0.0,
                "ai_trust_change": 0.0,
                "note": "Routine processing.",
            },
        }

        return json.dumps(response)
