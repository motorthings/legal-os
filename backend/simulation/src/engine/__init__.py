"""
Simulation engine — agent runtime, world engine, dynamics, prompts, and state management.
"""

from .dynamics import (
    AttritionEvent, AttritionState,
    compute_attrition_probability, process_attrition,
    TrustState, update_trust_from_experience, propagate_trust_cascade,
    compute_trust_divergence, get_trust_polarization,
)
from .prompts import (
    build_system_prompt, build_task_prompt,
)
from .agents import (
    AgentDecision, AgentState, AgentStates, AgentRuntime, MockLLM,
)
from .state import (
    SprintLog, SimulationRun, StateSerializer,
)

__all__ = [
    # Dynamics
    "AttritionEvent", "AttritionState",
    "compute_attrition_probability", "process_attrition",
    "TrustState", "update_trust_from_experience", "propagate_trust_cascade",
    "compute_trust_divergence", "get_trust_polarization",
    # Prompts
    "build_system_prompt", "build_task_prompt",
    # Agents
    "AgentDecision", "AgentState", "AgentStates", "AgentRuntime", "MockLLM",
    # State
    "SprintLog", "SimulationRun", "StateSerializer",
]
