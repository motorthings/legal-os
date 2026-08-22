"""Model elasticities — the transfer-function coefficients that set how STRONGLY each
lever moves the numbers, made explicit, ranged, sourced, and firm-calibratable.

Running a firm's own numbers (FirmSignature) fixes the *levels* — their PPP, realization,
leverage, practice mix. It does NOT fix these coefficients: how much codifying a seam cuts
rework, how much AFA converts saved hours to margin, how fast comp lifts adoption. Those
were hardcoded literals in `_collect_metrics` / `_adoption_rate`. Hiding them made the model
look more certain than it is.

Each coefficient now carries:
- **base / low / high** — the default and a plausible range, so the report can show a
  SENSITIVITY BAND ("+$300k to +$900k") instead of a false-precise point estimate.
- **source** — [SURVEY] (published anchor), [INFERRED] (structural), [ASSUMPTION] (judgment).
- **calibration_question** — a plain-English intake question that lets the firm set the
  coefficient from their own experience, or None if it isn't askable.

> **Financial-level calibration (2026-08-16).** The three penalty coefficients
> (`realization_exception_penalty`, `margin_exception_penalty`, `margin_redline_penalty`)
> were rescaled from single-digit-point units to *per-percent-point* units to match the
> engine's actual rate scale (exception/redline rates run 30–70%, not single digits). The
> old values shredded every firm's financials to the floors from sprint 1 (default firm
> margin ~9.9%, PPP 3M→676k), which a skeptical reader rejects. Now an as-is firm stays
> within roughly ±20% of its stated baseline, and levers produce the real deltas.
"""

from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class Elasticity:
    id: str
    name: str
    base: float
    low: float
    high: float
    source: str                             # "[SURVEY] ...", "[INFERRED] ...", "[ASSUMPTION] ..."
    calibration_question: Optional[str]     # plain-English intake prompt, or None
    unit: str = ""
    lever: Optional[str] = None             # which lever this coefficient primarily governs

    def at(self, where: str) -> float:
        """Value at 'low' | 'base' | 'high' — for sweeping the sensitivity band."""
        return {"low": self.low, "base": self.base, "high": self.high}[where]


# The coefficients, with defaults == the prior hardcoded literals. Ranges are deliberately
# WIDE where the evidence is thin (that honesty is the point) and tight where it's anchored.
_DEFS = [
    # --- PRICING lever: how AI's saved hours translate to money ---
    Elasticity(
        "margin_ai_afa_gain", "AFA margin conversion", base=0.15, low=0.08, high=0.25,
        source="[ASSUMPTION] how much of each AI-assisted point converts to margin under fixed fees",
        calibration_question="On flat-fee matters, when AI cuts the hours, roughly how much of that saving do you keep as margin vs pass to the client?",
        unit="margin pts / AI%", lever="pricing"),
    Elasticity(
        "margin_ai_hourly_drag", "Hourly AI drag", base=0.10, low=0.05, high=0.18,
        source="[INFERRED] billable-hour identity: faster AI => fewer billed hours",
        calibration_question="On hourly matters, when AI does the work faster, do you write down the saved time, or bill it? (more write-down = higher drag)",
        unit="margin pts / AI%", lever="pricing"),
    Elasticity(
        "realization_afa_leak", "Hourly-under-AFA-pressure leak", base=8.0, low=4.0, high=12.0,
        source="[ASSUMPTION] realization lost by staying hourly while clients push alternative fees",
        calibration_question="When a client pushes for alternative fees and you stay hourly, how much of the bill typically leaks to write-downs?",
        unit="realization pts", lever="pricing"),
    # --- SEAMS lever: how much codifying tacit hand-offs reduces incidents/rework ---
    Elasticity(
        "seam_incident_slope", "Seam incident sensitivity", base=0.7, low=0.4, high=0.9,
        source="[ASSUMPTION] share of a gappy hand-off's risk that shows up as a translation incident",
        calibration_question="When you've standardized a workflow before, roughly how much of the rework did it kill? (more = higher slope)",
        unit="incident rate / seam-risk", lever="seams"),
    Elasticity(
        "margin_redline_penalty", "Redline-rework margin cost", base=0.02, low=0.01, high=0.03,
        source="[ASSUMPTION] margin lost per percent-point of partner-rewrite rate (rate runs 40–80%)",
        calibration_question="When a partner substantially rewrites a draft, how much does that cost the matter's economics?",
        unit="margin pts / redline%", lever="seams"),
    # --- COMP lever: how much paying for adoption lifts it ---
    Elasticity(
        "adoption_comp_gain", "Comp -> adoption lift", base=0.65, low=0.35, high=0.85,
        source="[ASSUMPTION] adoption-ceiling lift from a full comp incentive, net of resistance",
        calibration_question="If you tied partner comp to AI use, how much would adoption actually move? (a lot = higher)",
        unit="adoption ceiling", lever="comp"),
    # --- LEVERAGE lever: how hard AI's hour-compression hits a steep pyramid ---
    Elasticity(
        "utilization_ai_cut", "AI utilization compression", base=3.0, low=1.5, high=5.0,
        source="[ASSUMPTION] billable hours cut per AI-assisted point at the archetype leverage (3.5)",
        calibration_question="As AI takes over routine associate work, how much do you expect billable hours per associate to fall?",
        unit="hours / AI%", lever="leverage"),
    # --- Cross-cutting quality->money penalties (not a single lever, but they move margin/realization) ---
    Elasticity(
        "margin_exception_penalty", "Exception margin cost", base=0.01, low=0.005, high=0.02,
        source="[ASSUMPTION] margin lost per percent-point of exception rate (rate runs 30–70%)",
        calibration_question=None, unit="margin pts / exception%", lever=None),
    Elasticity(
        "realization_exception_penalty", "Exception realization cost", base=0.03, low=0.015, high=0.05,
        source="[ASSUMPTION] realization lost per percent-point of exception rate (rate runs 30–70%)",
        calibration_question=None, unit="realization pts / exception%", lever=None),
    Elasticity(
        "attrition_trust_sensitivity", "Trust -> attrition", base=20.0, low=10.0, high=30.0,
        source="[ASSUMPTION] attrition rise as associate AI-trust falls below the neutral point",
        calibration_question="If associates lose faith in how the firm is rolling out AI, how much does that push turnover?",
        unit="attrition pts", lever=None),
]

DEFAULT_ELASTICITIES = {e.id: e for e in _DEFS}


@dataclass
class ElasticityProfile:
    """A firm's coefficient set. Starts from the defaults; `override` sets a coefficient's
    working value (e.g. from calibration) or swaps in a low/high for a sensitivity sweep.

    `calibrated` records which coefficients the FIRM itself set (via the intake/calibration
    path) as opposed to archetype defaults or sensitivity-sweep values. The report reads it
    to stamp every number as "firm-calibrated" or "archetype default" — the waterline between
    what's measured and what's assumed."""
    values: dict = field(default_factory=lambda: {k: v.base for k, v in DEFAULT_ELASTICITIES.items()})
    calibrated: frozenset = frozenset()

    def get(self, coef_id: str) -> float:
        return self.values.get(coef_id, DEFAULT_ELASTICITIES[coef_id].base)

    def with_override(self, coef_id: str, value: float) -> "ElasticityProfile":
        """Set a coefficient from firm calibration — marks it `calibrated`."""
        v = dict(self.values)
        v[coef_id] = value
        return ElasticityProfile(values=v, calibrated=self.calibrated | {coef_id})

    def with_point(self, coef_id: str, where: str) -> "ElasticityProfile":
        """Return a profile with one coefficient set to its 'low'/'base'/'high' — the unit
        of a sensitivity sweep. NOT marked calibrated: a sweep isn't a firm calibration."""
        v = dict(self.values)
        v[coef_id] = DEFAULT_ELASTICITIES[coef_id].at(where)
        return ElasticityProfile(values=v, calibrated=self.calibrated)


def default_profile() -> ElasticityProfile:
    return ElasticityProfile()
