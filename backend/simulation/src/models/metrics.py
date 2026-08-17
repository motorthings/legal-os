"""
Metric definitions for the legal simulation.

Every metric must connect to a business lever a partner would recognize. Activity
metrics (licenses, training, logins) are explicitly flagged as "activity" not
"outcome" — guard against confusing them with actual value.

The single optimizing number for a law firm is Profit Per Partner (PPP) — the
"combined ratio" analog. Everything ladders to it. Financial baselines are
grounded in published AmLaw 100 survey benchmarks (Thomson Reuters State of the
Legal Market, Altman Weil Law Firms in Transition, NALP, Clio Legal Trends,
Citi-Hildebrandt). Tags: [SURVEY] = published benchmark, [INFERRED] = derived,
[ASSUMPTION] = modeled (vary in sensitivity analysis).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MetricType(str, Enum):
    OUTCOME = "outcome"      # Business result that actually matters
    ACTIVITY = "activity"    # Process metric — easy to measure, easy to confuse with value
    LEADING = "leading"      # Predicts future outcomes
    LAGGING = "lagging"      # Confirms past outcomes
    TRANSLATION = "translation"  # Translation debt metric


@dataclass
class Metric:
    """A metric tracked across the simulation."""
    id: str
    name: str
    description: str
    type: MetricType
    unit: str                      # %, days, count, $, ratio, hours
    direction: str                 # "higher_is_better" or "lower_is_better"
    baseline: float                # starting value (AmLaw-100 calibrated)
    target: Optional[float]        # target value (if known)
    caution: Optional[str] = None  # a specific caution about this metric

    def improve(self, current: float) -> float:
        """Return the improvement from baseline as a signed value
        (positive = improvement, negative = degradation)."""
        if self.direction == "lower_is_better":
            return self.baseline - current
        else:
            return current - self.baseline


# === METRICS ===
# The firm's single optimizing number is PPP. Everything ladders to it.

METRICS = {
    # --- FINANCIAL OUTCOMES (the "combined ratio" tier) ---

    "ppp": Metric(
        id="ppp",
        name="Profit Per Partner",
        description="Net income / equity partners. The single number a firm optimizes. AmLaw 100 average $3.59M (2025, +14% YoY); the archetype is a mid-AmLaw-100 firm, so baseline is below the top-skewed average. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="$",
        direction="higher_is_better",
        baseline=3_000_000,     # mid-AmLaw-100 archetype (avg $3.59M is top-skewed) [SURVEY]
        target=3_800_000,
        caution=None,
    ),

    "rpl": Metric(
        id="rpl",
        name="Revenue Per Lawyer",
        description="Total revenue / total lawyers. The top-line productivity measure. AmLaw 100 average $1.39M (2025, +8.7% YoY); mid-firm archetype lower. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="$",
        direction="higher_is_better",
        baseline=1_200_000,     # mid-AmLaw-100 archetype (avg $1.39M) [SURVEY]
        target=1_400_000,
        caution="RPL rises when leverage falls. Measure it against realization, never alone.",
    ),

    "realization_rate": Metric(
        id="realization_rate",
        name="Realization Rate",
        description="Percentage of billed hours actually collected. The gap between what's billed and what's paid — the firm's translation debt in dollar form. AmLaw 100 average 81.5% (FY2025); a well-run litigation firm targets higher. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="%",
        direction="higher_is_better",
        baseline=85.0,          # archetype above the 81.5% average [SURVEY]
        target=91.0,
        caution=None,
    ),

    "matter_profit_margin": Metric(
        id="matter_profit_margin",
        name="Matter Profit Margin",
        description="Matter revenue less matter cost (associate time, AI cost, overhead) / revenue. The per-matter economics. [INFERRED]",
        type=MetricType.OUTCOME,
        unit="%",
        direction="higher_is_better",
        baseline=30.0,          # [INFERRED]
        target=40.0,
        caution="Per-matter margin can rise while total profit falls if volume drops. Measure total, not per-unit in isolation.",
    ),

    # --- OPERATIONAL OUTCOMES ---

    "matter_cycle_time": Metric(
        id="matter_cycle_time",
        name="End-to-End Matter Cycle Time",
        description="Intake to close. The economic unit is the full lifecycle, not task speed. 'The real question is whether work moves more cleanly across the system.' Commercial litigation average ~18 months. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="months",
        direction="lower_is_better",
        baseline=18.0,          # [SURVEY]
        target=12.0,
        caution="Task speed ≠ cycle time. Speeding drafting can increase total cycle time if partner review is the real constraint.",
    ),

    "collection_cycle": Metric(
        id="collection_cycle",
        name="Collection Cycle",
        description="Days from invoice to payment. The lagging indicator of realization — if the client won't pay, this shows it. Average ~90 days. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="days",
        direction="lower_is_better",
        baseline=90.0,          # [SURVEY]
        target=60.0,
        caution=None,
    ),

    "wip_aging": Metric(
        id="wip_aging",
        name="WIP Aging",
        description="Days of unbilled work-in-progress. Unbilled time is unpriced work — the same 'unpriced work' that is translation debt. Average ~75 days. [SURVEY]",
        type=MetricType.OUTCOME,
        unit="days",
        direction="lower_is_better",
        baseline=75.0,          # [SURVEY]
        target=45.0,
        caution=None,
    ),

    "utilization": Metric(
        id="utilization",
        name="Associate Utilization",
        description="Billable hours per associate per year. The leverage model's engine — and the metric AI drafting directly threatens (hours fall even as realization improves). First-years log ~2,300 billable; blended average ~2,000. [INFERRED]",
        type=MetricType.OUTCOME,
        unit="hours",
        direction="higher_is_better",
        baseline=2000.0,        # blended average; first-years ~2300 [INFERRED]
        target=2100.0,
        caution="Utilization measures hours, not value. AI that cuts hours while improving realization is an improvement this metric will misread as a loss.",
    ),

    # --- TRANSLATION DEBT METRICS (the translation-debt tier — the dependent variable) ---

    "translation_debt_index": Metric(
        id="translation_debt_index",
        name="Translation Debt Index",
        description="Composite: handoff failures + reconciliation incidents + rework per 100 matters. 'The unpriced work required to make fragmented organizations function as one system.' In law this is concentrated at the partner↔associate and associate↔paralegal seams. [ASSUMPTION — calibrate in baseline]",
        type=MetricType.TRANSLATION,
        unit="incidents/100 matters",
        direction="lower_is_better",
        baseline=100.0,
        target=30.0,
        caution=None,
    ),

    "exception_rate": Metric(
        id="exception_rate",
        name="Exception Rate",
        description="Matters requiring partner rescue beyond the designed process. 'The tail becomes supervision, escalation, recovery, stitching.' In law the tail is the partner re-doing the associate's work. [ASSUMPTION — calibrate in baseline]",
        type=MetricType.TRANSLATION,
        unit="%",
        direction="lower_is_better",
        baseline=15.0,
        target=5.0,
        caution="A low exception rate achieved by narrowing the AI's scope is not improvement. It's avoidance.",
    ),

    "handoff_failure_rate": Metric(
        id="handoff_failure_rate",
        name="Handoff Failure Rate",
        description="Matters where information is lost, misinterpreted, or requires rework at a role-to-role boundary (partner↔associate, associate↔paralegal). 'Every transfer point is a place where meaning can blur.' [ASSUMPTION — calibrate in baseline]",
        type=MetricType.TRANSLATION,
        unit="%",
        direction="lower_is_better",
        baseline=12.0,
        target=3.0,
        caution=None,
    ),

    "redline_rework_rate": Metric(
        id="redline_rework_rate",
        name="Redline Rework Rate",
        description="Percentage of AI drafts the partner substantially rewrites. THE law-specific translation-debt signal — AI automates the 80% of drafting that was never the value; the partner's redlines are the 20% that is. High rate = the AI output looks done but isn't. [ASSUMPTION — calibrate in baseline]",
        type=MetricType.TRANSLATION,
        unit="%",
        direction="lower_is_better",
        baseline=60.0,
        target=20.0,
        caution="A falling drafting-time with a flat redline-rework rate is the signature of automating the wrong thing.",
    ),

    "first_pass_accuracy": Metric(
        id="first_pass_accuracy",
        name="First-Pass Accuracy",
        description="Matters resolved without exceptions, translation incidents, or partner rework. Operational quality measure. [ASSUMPTION — calibrate in baseline]",
        type=MetricType.OUTCOME,
        unit="%",
        direction="higher_is_better",
        baseline=70.0,
        target=90.0,
        caution=None,
    ),

    "informal_control_points_surfaced": Metric(
        id="informal_control_points_surfaced",
        name="Informal Control Points Surfaced",
        description="Count of 'Diana situations' — the partner's redlines, the paralegal's clause library, the senior partner's conflicts memory, the billing partner's write-off judgment — that become visible and are addressed. 'AI doesn't break processes. It reveals them.'",
        type=MetricType.LEADING,
        unit="count",
        direction="higher_is_better",
        baseline=0.0,
        target=None,
        caution=None,
    ),

    # --- LEARNING VELOCITY ---

    "learning_loop_closure_rate": Metric(
        id="learning_loop_closure_rate",
        name="Learning Loop Closure Rate",
        description="Discoveries that result in structural change within 2 sprints. 'The objective isn't to defend the original plan. It's to increase the rate at which the organization discovers where value actually exists.'",
        type=MetricType.LEADING,
        unit="%",
        direction="higher_is_better",
        baseline=0.0,
        target=80.0,
        caution=None,
    ),

    "pattern_reuse_rate": Metric(
        id="pattern_reuse_rate",
        name="Pattern Reuse Rate",
        description="Decisions in deployment N+1 informed by evidence from deployment N. 'The next implementation shouldn't begin from fresh opinions.'",
        type=MetricType.LEADING,
        unit="%",
        direction="higher_is_better",
        baseline=0.0,
        target=70.0,
        caution=None,
    ),

    # --- ACTIVITY METRICS (these are NOT outcomes) ---

    "license_activation_rate": Metric(
        id="license_activation_rate",
        name="AI License Activation Rate",
        description="Percentage of attorneys who have activated their legal-AI tool license (Harvey/CoCounsel/Westlaw AI). 'Usage means people have access. Absorption means the organisation can carry what AI changes.'",
        type=MetricType.ACTIVITY,
        unit="%",
        direction="higher_is_better",
        baseline=0.0,
        target=95.0,
        caution="License activation ≠ value. It's the most misleading metric in legal AI.",
    ),

    "training_completion_rate": Metric(
        id="training_completion_rate",
        name="AI Training Completion Rate",
        description="Percentage of attorneys who completed AI training modules. 'Training as proxy for behavior change.'",
        type=MetricType.ACTIVITY,
        unit="%",
        direction="higher_is_better",
        baseline=0.0,
        target=90.0,
        caution="Training completion ≠ capability. Partners complete training and change nothing.",
    ),

    "ai_assisted_matter_pct": Metric(
        id="ai_assisted_matter_pct",
        name="AI-Assisted Matter Percentage",
        description="Matters where AI touched any step of the workflow. [INFERRED — legal AI adoption is early vs insurance's ~55%]",
        type=MetricType.ACTIVITY,
        unit="%",
        direction="higher_is_better",
        baseline=5.0,           # legal AI adoption is early vs insurance's 55% [INFERRED]
        target=60.0,
        caution="AI touch ≠ AI value. A matter can be 'AI-assisted' with zero improvement in outcomes.",
    ),

    # --- EVIDENCE & GOVERNANCE (generic, carry over) ---

    "evidence_completeness": Metric(
        id="evidence_completeness",
        name="Evidence Completeness",
        description="Percentage of AI decisions with a complete audit trail. 'Serious AI-enabled work has to leave a trail where the work happens.' [ASSUMPTION — calibrate in baseline]",
        type=MetricType.OUTCOME,
        unit="%",
        direction="higher_is_better",
        baseline=30.0,
        target=95.0,
        caution=None,
    ),

    "interruption_readiness": Metric(
        id="interruption_readiness",
        name="Interruption Readiness",
        description="Can named individuals stop, narrow, or override the AI within one business day? 'Delegation without an owner is not autonomy. It is unmanaged risk.' [ASSUMPTION — calibrate in baseline]",
        type=MetricType.OUTCOME,
        unit="boolean (0-1 scale)",
        direction="higher_is_better",
        baseline=0.3,
        target=1.0,
        caution=None,
    ),

    "trust_polarization": Metric(
        id="trust_polarization",
        name="Trust Polarization",
        description="Standard deviation of AI trust across agents × 10. High = the firm is split into partner-skeptics and associate-advocates. Low = aligned. [ASSUMPTION — calibrate in baseline]",
        type=MetricType.TRANSLATION,
        unit="0-10 scale",
        direction="lower_is_better",
        baseline=2.0,
        target=1.0,
        caution="Declining polarization is good only if trust is rising. Low polarization + low trust = uniform despair.",
    ),

    # --- PEOPLE METRICS ---

    "associate_attrition": Metric(
        id="associate_attrition",
        name="Associate Attrition (annual)",
        description="Voluntary turnover of associates. BigLaw churn is structural — the up-or-out tournament sheds associates every year. NALP Foundation 2025: 19% average (down from 20% in 2024); 83% of departures leave within 5 years. [SURVEY]",
        type=MetricType.LAGGING,
        unit="%",
        direction="lower_is_better",
        baseline=20.0,          # NALP Foundation 2025: 19% [SURVEY]
        target=14.0,
        caution=None,
    ),

    "partner_ai_trust": Metric(
        id="partner_ai_trust",
        name="Partner Trust in AI Systems",
        description="Composite trust score from partner agents. Partners start MORE skeptical than associates — their comp is the status quo, and AI threatens the leverage model. Deliberately seeded lower (3.5 vs 5.5). [ASSUMPTION — the bimodality is a modeled mechanism, see BUILD_PLAN §7.4a]",
        type=MetricType.LEADING,
        unit="0-10 scale",
        direction="higher_is_better",
        baseline=3.5,           # [ASSUMPTION — encode the partner-skepticism gradient deliberately]
        target=7.0,
        caution="Trust earned through reliable performance ≠ trust manufactured through communications.",
    ),

    "associate_ai_trust": Metric(
        id="associate_ai_trust",
        name="Associate Trust in AI Systems",
        description="Composite trust score from associate agents. Associates are digital natives with less invested in the leverage model — they adopt faster. Deliberately seeded higher (5.5 vs 3.5). [ASSUMPTION — see BUILD_PLAN §7.4a]",
        type=MetricType.LEADING,
        unit="0-10 scale",
        direction="higher_is_better",
        baseline=5.5,           # [ASSUMPTION]
        target=8.0,
        caution="The associate/partner trust gap is the experiment's engine — the people with the most power have the least openness.",
    ),
}


# Metric groups for dashboard organization
OUTCOME_METRICS = [m for m in METRICS.values() if m.type == MetricType.OUTCOME]
ACTIVITY_METRICS = [m for m in METRICS.values() if m.type == MetricType.ACTIVITY]
TRANSLATION_METRICS = [m for m in METRICS.values() if m.type == MetricType.TRANSLATION]
LEADING_METRICS = [m for m in METRICS.values() if m.type == MetricType.LEADING]
LAGGING_METRICS = [m for m in METRICS.values() if m.type == MetricType.LAGGING]



@dataclass
class MetricSnapshot:
    """A measurement of a metric at a point in time."""
    metric_id: str
    sprint: int
    value: float
    confidence: float     # 0-1: how confident are we in this measurement?
    notes: str = ""


@dataclass
class MetricHistory:
    """Time series of a metric across sprints for a single firm."""
    metric: Metric
    values: list[MetricSnapshot] = field(default_factory=list)

    def latest(self) -> Optional[MetricSnapshot]:
        return self.values[-1] if self.values else None

    def improvement_from_baseline(self) -> Optional[float]:
        latest = self.latest()
        if latest is None:
            return None
        return self.metric.improve(latest.value)
