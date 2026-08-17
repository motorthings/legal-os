"""
Workflow schema — the domain-agnostic step definition.

The `WorkflowStep` dataclass is the one reusable piece of the original insurance
build; the domain-specific workflow tables lived here and have been removed. The
legal domain defines its workflow in `matters.py`
(`LITIGATION_WORKFLOW`, `WORKFLOW_REGISTRY`, `SEAM_GAPS`, `INFORMAL_CONTROLS`), which
imports only `WorkflowStep` from here.

The schema models the seams — handoff points where translation debt
accumulates, informal control points operate, and bottlenecks migrate.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkflowStep:
    """A single step in a workflow (domain-agnostic schema)."""
    name: str
    description: str
    role_responsible: str       # role_id
    inputs_required: list[str]  # what information must be available
    decision_type: str          # "classify", "assess", "verify", "approve", "negotiate", "pay"
    ai_capable: bool            # can AI perform this step?
    ai_confidence_required: float  # 0-1 threshold for AI to proceed without human review
    typical_duration_sprints: float  # how long this step typically takes
    handoff_to: list[str]       # next step(s)
    exception_path: Optional[str] = None  # where do exceptions go?
    seam_risk: float = 0.0      # 0-1: how likely is translation debt at this handoff?
    ai_error_rate: float = 0.0  # 0-1: AI auto-processing failure rate at this step
    # Seam completeness — whether the handoff INTO this step carries standardized,
    # complete context. Encodes "the seam is gappy" as *data* the agent observes,
    # not as a post-hoc detector's judgment. The firm closes seams via the codify_seams lever.
    handoff_context: list[str] = field(default_factory=list)  # fields a complete handoff should carry
    context_complete: bool = True  # True = the handoff INTO this step is standardized/complete
    # Seam tacitness — how much of the knowledge needed to do this handoff correctly is
    # discoverable ONLY through use (tacit) vs. codifiable upfront (explicit). 0 = fully
    # codifiable (schema/threshold/rail), 1 = lives in an expert's head (judgment,
    # negotiation, precedent). DELIBERATELY ORTHOGONAL to seam_risk: a seam can be
    # high-risk yet codifiable, or high-risk and tacit.
    # A-priori standardization nails low-tacitness seams; evidence-built fixes are needed for
    # high-tacitness ones. [ASSUMPTION — vary in sweep.]
    # REQUIRED: a None sentinel (not a neutral 0.5 default) so a step that forgets to score
    # tacitness fails loudly at construction instead of silently skewing the results.
    # (Kept as a keyword field with a sentinel because it follows other defaulted fields.)
    seam_tacitness: Optional[float] = None
    # §7.9 — fraction of the step the active legal-AI tool still leaves to human judgment
    # (0 = fully codifiable by the tool, 1 = the tool does not reduce the human load). Set
    # per-run by orchestrator._apply_tool_profile from the tool's operation spec.
    tacit_residual: Optional[float] = None

    def __post_init__(self):
        if self.seam_tacitness is None:
            raise ValueError(
                f"WorkflowStep '{self.name}' is missing seam_tacitness. Score it via the "
                f"rubric in docs/track-b-parity-spec-2026-08-13.md (0=codifiable, 1=tacit)."
            )
        if not (0.0 <= self.seam_tacitness <= 1.0):
            raise ValueError(
                f"WorkflowStep '{self.name}' seam_tacitness={self.seam_tacitness} out of [0,1]."
            )
