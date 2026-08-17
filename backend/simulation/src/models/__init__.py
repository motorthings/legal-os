"""
Simulation models for the legal AI transformation simulation.

Archetypal AmLaw 100 commercial-litigation firm. Systems-of-work grounded.
Every parameter sourced (survey benchmark) or flagged [INFERRED]/[ASSUMPTION]
for sensitivity analysis.
"""

from .profiles import (
    PsychologicalProfile, OceanProfile, BiasProfile, MotivationProfile,
    ChangeState, CareerStage, DecisionStyle, PriorAIExposure,
    Role, Relationship,
    ROLES, RELATIONSHIPS,
)

from .matters import (
    Matter, MatterComplexity, MatterStatus, WorkflowStep,
    LITIGATION_WORKFLOW, WORKFLOW_STEP_MAP, WORKFLOW_REGISTRY,
    route_matter, get_seams, INFORMAL_CONTROLS, SEAM_GAPS,
)

from .events import (
    WorldEngine, EnvironmentalState, EnvironmentalEvent,
    MarketPhase, EventSeverity, ALL_EVENTS,
)

from .metrics import (
    Metric, MetricType, MetricSnapshot, MetricHistory,
    METRICS, OUTCOME_METRICS, ACTIVITY_METRICS,
    TRANSLATION_METRICS, LEADING_METRICS, LAGGING_METRICS,
)

from .company import (
    Department, CompanyState, DEPARTMENTS, create_company,
)

__all__ = [
    # Profiles
    "PsychologicalProfile", "OceanProfile", "BiasProfile", "MotivationProfile",
    "ChangeState", "CareerStage", "DecisionStyle", "PriorAIExposure",
    "Role", "Relationship", "ROLES", "RELATIONSHIPS",
    # Matters
    "Matter", "MatterComplexity", "MatterStatus", "WorkflowStep",
    "LITIGATION_WORKFLOW", "WORKFLOW_STEP_MAP", "WORKFLOW_REGISTRY",
    "route_matter", "get_seams", "INFORMAL_CONTROLS", "SEAM_GAPS",
    # Events
    "WorldEngine", "EnvironmentalState", "EnvironmentalEvent",
    "MarketPhase", "EventSeverity", "ALL_EVENTS",
    # Metrics
    "Metric", "MetricType", "MetricSnapshot", "MetricHistory",
    "METRICS", "OUTCOME_METRICS", "ACTIVITY_METRICS",
    "TRANSLATION_METRICS", "LEADING_METRICS", "LAGGING_METRICS",
    # Company
    "Department", "CompanyState", "DEPARTMENTS", "create_company",
]
