"""
Company model for the archetypal AmLaw 100 commercial-litigation firm — the
simulation substrate.

This module ties together:
- Organizational structure (departments, roles)
- Psychological profiles (from profiles.py)
- Matter workflows (from matters.py)
- Environmental events (from events.py)
- Metric definitions (from metrics.py)

The firm is ARCHETYPAL, not a real firm: ~900 attorneys, 3 offices, 65%
litigation / 35% transactional, ~$1.9B revenue. No ticker (partnership).
Calibrated from published survey benchmarks (Thomson Reuters, Altman Weil,
NALP, Clio, Citi-Hildebrandt), not filings — firms don't file 10-Qs.
Parameters tagged [SURVEY] / [INFERRED] / [ASSUMPTION] for sensitivity analysis.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

from .profiles import (
    Role, ROLES, PsychologicalProfile, Relationship, RELATIONSHIPS,
    get_relationships_for,
)
from .matters import (
    LITIGATION_WORKFLOW, WORKFLOW_STEP_MAP, WORKFLOW_REGISTRY,
    Matter, MatterComplexity, MatterStatus, route_matter, get_seams,
    INFORMAL_CONTROLS,
)
from .events import (
    WorldEngine, EnvironmentalState, EnvironmentalEvent,
    MarketPhase, EventSeverity, ALL_EVENTS,
)
from .metrics import Metric, MetricSnapshot, MetricHistory, METRICS


@dataclass
class Department:
    """A department (practice group / business function) in the firm."""
    name: str
    headcount: int                     # total attorneys/staff
    budget_pct: float                  # % of total operating budget
    roles: list[str]                   # role_ids in this department
    description: str
    kpis: list[str]                    # metric_ids this department is measured on


# The archetypal AmLaw 100 firm's organizational structure.
# v1 models the LITIGATION practice area end-to-end; transactional is present
# for realism but has no active agents (one practice area, one workflow).
DEPARTMENTS = {
    "litigation": Department(
        name="Litigation",
        headcount=585,               # ~65% of 900 attorneys
        budget_pct=0.55,
        roles=["rainmaker_partner", "service_partner", "practice_group_leader",
               "senior_associate", "mid_associate", "junior_associate", "paralegal"],
        description="Commercial litigation. The core practice area and the v1 modeled workflow. Partner-heavy, tacit-knowledge-concentrated.",
        kpis=["realization_rate", "matter_profit_margin", "utilization", "redline_rework_rate"],
    ),
    "transactional": Department(
        name="Corporate / Transactional",
        headcount=315,               # ~35% of 900 attorneys
        budget_pct=0.20,
        roles=[],                     # no v1 agents — modeled for realism only
        description="M&A, finance, corporate. Present for firm realism; not modeled in v1.",
        kpis=["rpl", "realization_rate"],
    ),
    "knowledge_mgmt": Department(
        name="Knowledge Management / Library",
        headcount=40,
        budget_pct=0.03,
        roles=["km_partner"],
        description="The precedent database, clause library, and institutional memory. The tacit-knowledge gate — where the 'Diana' role lives in law.",
        kpis=["translation_debt_index", "handoff_failure_rate"],
    ),
    "legal_ops": Department(
        name="Legal Operations",
        headcount=35,
        budget_pct=0.04,
        roles=["conflicts_analyst", "billing_partner"],
        description="Conflicts, billing, collections, matter management. Back-office, below the line of sight — where the highest-leverage elimination candidates hide.",
        kpis=["realization_rate", "collection_cycle", "wip_aging"],
    ),
    "it_innovation": Department(
        name="IT / Innovation",
        headcount=50,
        budget_pct=0.05,
        roles=["it_director"],
        description="Legal-tech selection and deployment. Overcommitted — everyone's bottleneck.",
        kpis=["evidence_completeness", "ai_assisted_matter_pct"],
    ),
    "executive": Department(
        name="Executive Committee",
        headcount=18,
        budget_pct=0.13,
        roles=["managing_partner"],
        description="Managing partner and the equity-partner committee. The leverage model's guardians.",
        kpis=["ppp", "rpl", "realization_rate"],
    ),
}


@dataclass
class CompanyState:
    """
    The complete state of the simulated firm. One firm, one state; it inherits
    its events from the WorldEngine.
    """

    name: str = "Aldrich & Vale LLP"
    ticker: Optional[str] = None     # partnerships have no ticker

    # Structural
    departments: dict[str, Department] = field(default_factory=lambda: DEPARTMENTS)
    roles: dict[str, Role] = field(default_factory=lambda: deepcopy(ROLES))
    relationships: list[Relationship] = field(default_factory=lambda: RELATIONSHIPS)
    workflow: list = field(default_factory=lambda: LITIGATION_WORKFLOW)
    workflows: dict = field(default_factory=lambda: dict(WORKFLOW_REGISTRY))  # all active workflows
    workflow_state: dict = field(default_factory=lambda: deepcopy(WORKFLOW_STEP_MAP))  # mutable per-run copy

    # Agent state (evolves each sprint)
    agent_stress: dict[str, float] = field(default_factory=dict)       # role_id → 0-1
    agent_ai_confidence: dict[str, float] = field(default_factory=dict)  # role_id → 0-1
    agent_change_exhaustion: dict[str, float] = field(default_factory=dict)  # role_id → 0-1

    # Governance / adoption state
    steering_committee_decisions: list[dict] = field(default_factory=list)
    roadmap_phases_completed: list[str] = field(default_factory=list)
    adoption_dashboard: dict[str, float] = field(default_factory=dict)  # role_id → adoption %

    # Workflow state
    active_matters: list[Matter] = field(default_factory=list)

    # Budget
    transformation_budget: float = 10_000_000  # $10M initial
    budget_remaining: float = 10_000_000

    # Metrics
    metric_history: dict[str, MetricHistory] = field(default_factory=dict)

    # Environmental context (set by WorldEngine each sprint)
    env_params: dict = field(default_factory=dict)

    # Macro forces (mechanisms, not shocks). These are the structural pressures AI hits.
    pricing_model: str = "hourly"       # "hourly" | "fixed_fee" | "value_based" — the AI Profit Paradox hinge
    absorb_vs_pass: str = "absorb"      # "absorb" (margin-rich, client sees no benefit) | "pass" (competitive, margin-thin)
    leverage_target: float = 3.5        # leverage ratio target (3:1–5:1; shrinking as AI replaces juniors)
    nonequity_tier: bool = False        # nonequity partner tier expanded to protect PEP

    def shift_pricing_model(self, toward: str):
        """Move the pricing model one notch toward `toward` (hourly→fixed_fee→value_based)."""
        order = ["hourly", "fixed_fee", "value_based"]
        try:
            i, j = order.index(self.pricing_model), order.index(toward)
        except ValueError:
            return
        if j > i:
            self.pricing_model = order[i + 1]
        elif j < i:
            self.pricing_model = order[i - 1]

    def initialize_agent_states(self):
        """Set initial agent states from their profiles."""
        for role_id, role in self.roles.items():
            self.agent_stress[role_id] = role.profile.ocean.neuroticism / 5.0  # normalize to 0-1
            self.agent_ai_confidence[role_id] = role.profile.change_state.ai_confidence
            self.agent_change_exhaustion[role_id] = role.profile.change_state.change_exhaustion / 10.0

    def get_role(self, role_id: str) -> Optional[Role]:
        return self.roles.get(role_id)

    def get_department_for_role(self, role_id: str) -> Optional[Department]:
        for dept in self.departments.values():
            if role_id in dept.roles:
                return dept
        return None

    def get_relationships(self, role_id: str) -> list[Relationship]:
        return get_relationships_for(role_id)

    def get_seams(self) -> list[dict]:
        return get_seams()

    def record_metric(self, metric_id: str, sprint: int, value: float, confidence: float = 1.0):
        """Record a metric measurement for this firm."""
        if metric_id not in self.metric_history:
            self.metric_history[metric_id] = MetricHistory(metric=METRICS[metric_id])

        snapshot = MetricSnapshot(
            metric_id=metric_id,
            sprint=sprint,
            value=value,
            confidence=confidence,
        )

        self.metric_history[metric_id].values.append(snapshot)


def create_company() -> CompanyState:
    """Create the firm (a single, parameterized company)."""
    company = CompanyState()
    company.initialize_agent_states()
    return company
