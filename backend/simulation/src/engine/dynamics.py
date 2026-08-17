"""
Organizational dynamics — feedback loops and contagion processes.

Unlike environmental events (random, external, identical to both tracks),
these dynamics are internal, state-driven, and evolve independently in each track.

Two core dynamics:
1. Attrition contagion — departures cascade through departments
2. Trust cascade — AI confidence propagates through influence networks
"""

import math
from dataclasses import dataclass, field
from random import Random
from typing import Optional

from ..models.profiles import Role, Relationship
from ..models.company import CompanyState


# === ATTRITION CONTAGION ===

# Baseline PER-SPRINT attrition probabilities per role type.
# (Previously these were quarterly-calibrated but applied every sprint, producing
# ~6x too much attrition and mass departure by sprint 4. Rescaled so the same
# annual turnover numbers hold across a 16-sprint run.)
BASELINE_ATTRITION = {
    # High-turnover roles — the up-or-out tournament sheds associates every year
    "junior_associate": 0.022,      # ~30% annual — first-years, NALP-confirmed structural churn
    "associate": 0.012,             # ~19% annual — NALP 2025 average (mid/senior)
    "it_director": 0.010,           # ~18% annual — legal-tech market competitive
    # Moderate-turnover roles
    "paralegal": 0.008,             # ~15% annual
    "conflicts_analyst": 0.008,     # ~15% annual — back-office, replaceable
    "billing_partner": 0.005,       # ~10% annual
    # Low-turnover roles
    "km_partner": 0.004,            # ~8% annual — deep tenure, holds the tacit knowledge
    "practice_group_leader": 0.004, # ~8% annual
    "partner": 0.003,               # ~6% annual — partners leave via poaching, not baseline
    "rainmaker_partner": 0.001,     # ~2% annual — departure is event-driven (lateral poaching)
}

# Role-type classification for attrition lookup
ROLE_ATTRITION_TYPE = {
    "managing_partner": "partner",
    "rainmaker_partner": "rainmaker_partner",
    "service_partner": "partner",
    "practice_group_leader": "practice_group_leader",
    "senior_associate": "associate",
    "mid_associate": "associate",
    "junior_associate": "junior_associate",
    "paralegal": "paralegal",
    "km_partner": "km_partner",
    "conflicts_analyst": "conflicts_analyst",
    "billing_partner": "billing_partner",
    "it_director": "it_director",
}

# Contagion multiplier: each departure in the same department increases
# probability of another departure in the next sprint.
CONTAGION_MULTIPLIER = 1.1          # 10% increase per prior departure (was 1.5 — too aggressive)
CONTAGION_DECAY = 0.5               # contagion decays by half each sprint
MAX_CONTAGION_MULTIPLIER = 2.0      # cap the contagion effect (was 4.0)

# Stress sensitivity: how much does environmental stress increase attrition?
STRESS_ATTRITION_SENSITIVITY = 0.3  # stress_factor of 1.5 → ~15% higher attrition

# Labor market sensitivity: tighter labor market = more poaching
LABOR_MARKET_ATTRITION_SENSITIVITY = 0.25


@dataclass
class AttritionEvent:
    """Record of an agent departure."""
    sprint: int
    role_id: str
    role_name: str
    department: str
    reason: str           # "voluntary", "retirement", "poached", "burnout"
    replacement_profile: Optional[str] = None  # profile of the replacement


@dataclass
class AttritionState:
    """Track-specific attrition state."""
    departures: list[AttritionEvent] = field(default_factory=list)
    department_contagion: dict[str, float] = field(default_factory=dict)  # dept → contagion multiplier
    active_agents: set[str] = field(default_factory=set)  # role_ids that haven't departed


def compute_attrition_probability(
    role_id: str,
    department: str,
    company: CompanyState,
    attrition_state: AttritionState,
    retirement_horizon: float = 10.0,
) -> float:
    """
    Calculate the probability a specific agent departs this sprint.

    Factors:
    1. Baseline attrition for their role type
    2. Department contagion (previous departures in same department)
    3. Environmental stress (from events)
    4. Labor market tightness (from events)
    5. Retirement horizon (partners near retirement depart, dissolving the rainmaker veto)
    6. Track-specific factors (AI reducing grind vs AI adding overhead)
    """
    if role_id not in ROLE_ATTRITION_TYPE:
        return 0.01  # unknown role, low default

    role_type = ROLE_ATTRITION_TYPE[role_id]
    baseline = BASELINE_ATTRITION.get(role_type, 0.03)

    # Department contagion
    contagion = attrition_state.department_contagion.get(department, 1.0)
    contagion = min(contagion, MAX_CONTAGION_MULTIPLIER)

    # Environmental stress
    stress_factor = company.env_params.get("stress_factor", 1.0)
    stress_effect = 1.0 + (stress_factor - 1.0) * STRESS_ATTRITION_SENSITIVITY

    # Labor market sensitivity: tighter labor market = more poaching.
    # Applied when LABOR_MARKET_TIGHTENING event is active (captured via stress_factor).
    labor_effect = 1.0 + (stress_factor - 1.0) * LABOR_MARKET_ATTRITION_SENSITIVITY

    # Does AI reduce grind or add overhead? When AI is working well, associate AI
    # confidence is high → lower attrition; when it adds overhead → higher attrition.
    ai_confidence = company.agent_ai_confidence.get(role_id, 0.5)
    ai_grind_factor = 1.0
    if role_type in ("junior_associate", "associate"):
        # For high-grind roles, AI confidence above 0.6 = work is getting easier
        if ai_confidence > 0.6:
            ai_grind_factor = 0.85   # 15% lower attrition — AI is reducing grind
        elif ai_confidence < 0.3:
            ai_grind_factor = 1.15   # 15% higher attrition — AI is adding frustration

    probability = baseline * contagion * stress_effect * labor_effect * ai_grind_factor

    # Retirement horizon [INFERRED]: partners near retirement depart faster, dissolving the
    # rainmaker veto. Gentle multiplier (not additive) so a short horizon raises partner churn
    # without collapsing the partner_review step within a 16-sprint run.
    if role_type in ("partner", "rainmaker_partner", "km_partner", "billing_partner"):
        probability *= 1.0 + max(0.0, (5.0 - retirement_horizon) / 5.0)  # 1.0x (>=5yr) -> 2.0x (0yr)

    # Cap at 50% per sprint — no role has >50% quarterly attrition
    return min(probability, 0.50)


def process_attrition(
    company: CompanyState,
    attrition_state: AttritionState,
    sprint: int,
    rng: Random,
    retirement_horizon: float = 10.0,
) -> list[AttritionEvent]:
    """
    Determine which agents (if any) depart this sprint.
    Applies contagion for the NEXT sprint.
    """
    events = []

    # Check each active agent. `active_agents` is a set of string role_ids — iterate in a
    # SORTED order so the RNG draws below map to roles deterministically regardless of
    # PYTHONHASHSEED (set iteration order is randomized per process). This is what makes a
    # same-seed run reproducible across separate invocations.
    for role_id in sorted(attrition_state.active_agents):
        role = company.get_role(role_id)
        if role is None:
            continue

        dept = company.get_department_for_role(role_id)
        dept_name = dept.name if dept else "unknown"

        prob = compute_attrition_probability(role_id, dept_name, company, attrition_state, retirement_horizon)

        if rng.random() < prob:
            # Determine reason
            if role.profile.change_state.career_stage.value == "late":
                reason = "retirement" if rng.random() < 0.5 else "voluntary"
            elif company.env_params.get("urgency_elevated", False):
                reason = "burnout" if rng.random() < 0.6 else "voluntary"
            else:
                reason = "poached" if rng.random() < 0.3 else "voluntary"

            event = AttritionEvent(
                sprint=sprint,
                role_id=role_id,
                role_name=role.name,
                department=dept_name,
                reason=reason,
            )
            events.append(event)
            attrition_state.departures.append(event)
            attrition_state.active_agents.discard(role_id)

    # Apply contagion for next sprint
    # Decay existing contagion
    for dept in attrition_state.department_contagion:
        attrition_state.department_contagion[dept] = (
            1.0 + (attrition_state.department_contagion[dept] - 1.0) * CONTAGION_DECAY
        )

    # Add fresh contagion from this sprint's departures
    for event in events:
        if event.department not in attrition_state.department_contagion:
            attrition_state.department_contagion[event.department] = 1.0
        attrition_state.department_contagion[event.department] *= CONTAGION_MULTIPLIER

    return events


# === TRUST CASCADE ===

# How quickly does AI confidence converge through the influence network?
# Fraction per sprint — trust doesn't shift instantly.
TRUST_CONVERGENCE_RATE = 0.15        # 15% movement toward influencer's confidence per sprint

# How much does direct experience matter vs social influence?
# Higher = agents trust their own experience more than what the KM partner thinks.
DIRECT_EXPERIENCE_WEIGHT = 0.6       # 60% own experience, 40% social influence

# How much does each AI interaction change confidence?
# A single positive interaction moves confidence by this much.
EXPERIENCE_DELTA = 0.03              # small per-interaction effect — trust builds slowly

# Trust inertia: agents with low openness resist changing their mind
# regardless of evidence. Captured by openness score.


@dataclass
class TrustState:
    """Track-specific trust in AI systems, per agent."""
    confidence: dict[str, float] = field(default_factory=dict)  # role_id → 0-1

    def initialize_from_company(self, company: CompanyState):
        """Set initial trust from agent profiles."""
        for role_id, confidence in company.agent_ai_confidence.items():
            self.confidence[role_id] = confidence

    def get(self, role_id: str) -> float:
        return self.confidence.get(role_id, 0.5)


def update_trust_from_experience(
    company: CompanyState,
    trust_state: TrustState,
    role_id: str,
    ai_interactions: int,         # how many AI-touched matters this agent saw
    positive_outcomes: int,       # how many were positive (AI was right/helpful)
    negative_outcomes: int,       # how many were negative (AI was wrong/harmful)
):
    """
    Update an agent's AI trust based on direct experience this sprint.
    Called after processing the matter batch.
    """
    role = company.get_role(role_id)
    if role is None:
        return

    total = ai_interactions
    if total == 0:
        return  # no experience to update from

    # Net experience signal with loss aversion: negative experiences carry 2x weight.
    # (Losses loom larger than gains — Kahneman.) This is what makes friction/skepticism
    # a real drag on trust instead of being washed out by the AI's frequent successes.
    net_signal = (positive_outcomes - 2.0 * negative_outcomes) / max(total, 1)

    # How much this moves the needle depends on openness
    # Low openness = trust moves slowly regardless of evidence
    openness_factor = role.profile.ocean.openness / 5.0  # 0.2-1.0

    delta = net_signal * EXPERIENCE_DELTA * openness_factor * total

    current = trust_state.confidence.get(role_id, 0.5)
    trust_state.confidence[role_id] = max(0.0, min(1.0, current + delta))


def _get_influencers(company: CompanyState, role_id: str) -> list[tuple[str, float]]:
    """Find all agents who influence the given role, and how strongly.
    Scans ALL relationships where this role is the TARGET (being influenced)."""
    influencers = []
    for rel in company.relationships:
        if rel.target == role_id and rel.influence > 0:
            influencers.append((rel.source, rel.influence))
    return influencers


def propagate_trust_cascade(
    company: CompanyState,
    trust_state: TrustState,
):
    """
    Propagate AI trust through the influence network.
    Each agent's trust moves fractionally toward the trust level of
    people who influence THEM (not people they influence).

    The KM partner is the key node — high influence over associates and partners,
    and their trust (or distrust) cascades through the firm.

    This is called once per sprint AFTER direct experience updates.
    """
    # Snapshot current trust before propagation (simultaneous update)
    snapshot = dict(trust_state.confidence)

    for role_id in trust_state.confidence:
        role = company.get_role(role_id)
        if role is None:
            continue

        # Get agents who influence THIS agent (where this agent is the TARGET)
        influencers = _get_influencers(company, role_id)
        if not influencers:
            continue

        # Calculate weighted social influence on this agent
        total_influence = sum(inf[1] for inf in influencers)
        weighted_trust = sum(
            inf[1] * snapshot.get(inf[0], 0.5)
            for inf in influencers
        )

        if total_influence == 0:
            continue

        social_target = weighted_trust / total_influence

        # How much does this agent weight social influence vs own experience?
        autonomy_factor = role.profile.motivation.autonomy / 10.0    # 0-1
        authority_factor = role.profile.biases.authority / 10.0      # 0-1
        social_weight = 1.0 - DIRECT_EXPERIENCE_WEIGHT
        social_weight += authority_factor * 0.1
        social_weight -= autonomy_factor * 0.1
        social_weight = max(0.1, min(0.6, social_weight))  # clamp to [0.1, 0.6]

        # Inertia: low openness resists change regardless of source
        openness_factor = role.profile.ocean.openness / 5.0

        current = snapshot[role_id]
        movement = (social_target - current) * TRUST_CONVERGENCE_RATE * openness_factor

        trust_state.confidence[role_id] = max(0.0, min(1.0, current + movement))


def compute_trust_divergence(trust_state: TrustState) -> float:
    """
    Measure how much agents disagree about AI trust.
    High divergence = fragmented organization = translation debt.
    Low divergence = aligned (whether positive or negative).
    """
    if len(trust_state.confidence) < 2:
        return 0.0

    values = list(trust_state.confidence.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)  # standard deviation of trust


def get_trust_polarization(trust_state: TrustState) -> dict:
    """
    Categorize agents by trust level.
    Returns counts of skeptics, neutrals, and advocates.
    """
    skeptics = [rid for rid, v in trust_state.confidence.items() if v < 0.35]
    neutrals = [rid for rid, v in trust_state.confidence.items() if 0.35 <= v <= 0.65]
    advocates = [rid for rid, v in trust_state.confidence.items() if v > 0.65]

    return {
        "skeptics": skeptics,
        "neutrals": neutrals,
        "advocates": advocates,
        "skeptic_count": len(skeptics),
        "neutral_count": len(neutrals),
        "advocate_count": len(advocates),
        "km_partner_is_skeptic": "km_partner" in skeptics,
        "km_partner_is_advocate": "km_partner" in advocates,
    }
