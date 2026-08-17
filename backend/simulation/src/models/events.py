"""
Environmental events model for the legal simulation.

All probabilities are grounded in the legal market's observable dynamics. Events
are drawn once per sprint and applied IDENTICALLY to both tracks.

Key sources:
- Legal demand tracks the economic cycle (recessions defer litigation/transactional work)
- Lateral partner departures are a structural fact of the BigLaw tournament
- Client AFAs / panel convergence are the dominant pricing pressure (Citi-Hildebrandt)
- Court rules (e-discovery, AI-disclosure) and bar ethics opinions govern AI use
- Legal-tech vendor cadence (Westlaw AI, Harvey, CoCounsel) is ~1-2 major releases/year
"""

from dataclasses import dataclass, field
from enum import Enum
from random import Random
from typing import Optional


class MarketPhase(str, Enum):
    """Legal market demand cycle."""
    DEMAND = "demand"                  # busy — matters flow, leverage pays off
    CONTRACTION = "contraction"        # demand drops, rate pressure, deferrals
    TRANSITIONING = "transitioning"    # moving between phases


class EventSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class EnvironmentalEvent:
    """An event that affects the simulation environment."""
    name: str
    description: str
    severity: EventSeverity
    probability_per_sprint: float          # 0-1, per quarterly sprint
    duration_sprints: int = 1
    cooldown_sprints: int = 0

    # Impact multipliers (applied to agent stress, matter volume, budget, etc.)
    matter_volume_multiplier: float = 1.0  # e.g., 2.5 = surge of matters (MDL, regulatory wave)
    budget_multiplier: float = 1.0         # e.g., 0.8 = 20% budget cut
    stress_multiplier: float = 1.0         # e.g., 1.5 = 50% more stress for affected agents
    regulation_multiplier: float = 1.0     # e.g., 2.0 = double ethics/rule scrutiny
    it_freeze: bool = False                # whether IT projects are frozen
    transformation_pause: bool = False     # whether transformation work is paused
    urgency_spike: bool = False            # whether leadership urgency increases

    affected_departments: list[str] = field(default_factory=list)


# === MARKET CYCLE ===
# Legal demand follows the economy with a lag. A busy market typically lasts
# several quarters; a contraction lasts a few. Calibrated so expected phase
# duration ~12-16 sprints.

DEMAND_TO_CONTRACTION_TRANSITION_PROB = 0.06   # ~6% per sprint
CONTRACTION_TO_DEMAND_TRANSITION_PROB = 0.08   # ~8% per sprint


# === ECONOMIC EVENTS ===

RECESSION = EnvironmentalEvent(
    name="Recession / Demand Contraction",
    description="Economic downturn — clients defer litigation and transactional work, GCs tighten budgets, fee pressure intensifies. The legal market's 'hurricane' analog: demand doesn't surge, it dries up.",
    severity=EventSeverity.HIGH,
    probability_per_sprint=0.05,    # 5% per quarter — recessions are rare but prolonged
    duration_sprints=3,
    cooldown_sprints=6,
    matter_volume_multiplier=0.6,   # fewer new matters
    budget_multiplier=0.80,         # client budgets tighten → realization pressure
    stress_multiplier=1.4,
    affected_departments=["litigation", "transactional", "executive"],
)

CLIENT_RATE_PRESSURE = EnvironmentalEvent(
    name="Client Rate Pressure",
    description="Major clients demand rate discounts, freezes, or convergence. GCs benchmark legal spend against ALSPs and AI-native providers. Margin pressure hits realization directly.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.12,    # 12% per quarter — persistent background pressure
    duration_sprints=2,
    cooldown_sprints=2,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.90,
    stress_multiplier=1.15,
    affected_departments=["litigation", "transactional", "executive"],
)

INTEREST_RATE_CHANGE = EnvironmentalEvent(
    name="Interest Rate Change (±50bp)",
    description="Rate moves affect client financing, M&A deal flow, and the firm's own capital. A large move shifts transactional demand.",
    severity=EventSeverity.LOW,
    probability_per_sprint=0.08,
    duration_sprints=1,
    cooldown_sprints=2,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.95,
    stress_multiplier=1.0,
    affected_departments=["transactional", "executive"],
)


# === COMPETITIVE / CLIENT EVENTS ===

COMPETITOR_LEGAL_AI_LAUNCH = EnvironmentalEvent(
    name="Competitor Legal AI Launch",
    description="A peer AmLaw firm publicly launches a GenAI capability — AI drafting at scale, AI-first e-discovery, or a pricing model built on AI productivity. Creates a 'we're falling behind' panic in the executive committee.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.08,    # 8% per quarter — major peer moves every ~2-3 years
    duration_sprints=1,
    cooldown_sprints=6,
    matter_volume_multiplier=1.0,
    budget_multiplier=1.0,
    stress_multiplier=1.1,
    urgency_spike=True,
    affected_departments=["executive", "litigation", "it_innovation"],
)

LATERAL_PARTNER_POACHING = EnvironmentalEvent(
    name="Lateral Partner Poaching",
    description="A rainmaker partner is recruited by a competitor and departs with a book of business. The uniquely legal failure mode: a single departure can take $20M+ of origination and destabilize a practice group. The 'key person departure' with a book-of-business multiplier.",
    severity=EventSeverity.HIGH,
    probability_per_sprint=0.06,    # 6% per quarter — lateral movement is constant
    duration_sprints=2,
    cooldown_sprints=4,
    matter_volume_multiplier=0.85,  # the departing partner takes matters with them
    budget_multiplier=0.95,
    stress_multiplier=1.5,
    affected_departments=["litigation", "executive"],
)

CLIENT_MANDATE_AFAS = EnvironmentalEvent(
    name="Client Mandates AFAs / Panel Convergence",
    description="A major client mandates alternative fee arrangements, demands a panel spot, or requires the firm to use the client's e-discovery platform. The external forcing function — the client dictates change faster than any internal program.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.10,
    duration_sprints=2,
    cooldown_sprints=3,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.90,
    stress_multiplier=1.15,
    urgency_spike=True,
    affected_departments=["litigation", "transactional", "executive"],
)

ASSOCIATE_MARKET_TIGHTENING = EnvironmentalEvent(
    name="Associate Market Tightening",
    description="A lateral-associate poaching war — competing firms raise associate comp and poach mid-levels. Attrition risk spikes; the leverage model strains as the firm must overpay to retain.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.10,
    duration_sprints=3,
    cooldown_sprints=4,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.95,
    stress_multiplier=1.3,
    affected_departments=["litigation", "transactional"],
)


# === REGULATORY / ETHICS EVENTS ===

COURT_RULE_CHANGE = EnvironmentalEvent(
    name="Court Rule Change (E-Discovery / AI Disclosure)",
    description="A federal court issues new rules on AI use — mandatory disclosure of AI-generated work product, e-discovery proportionality changes, or sanctions for unverified AI citations. Requires process changes and freezes AI deployment until compliance.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.08,
    duration_sprints=2,
    cooldown_sprints=4,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.90,
    stress_multiplier=1.25,
    regulation_multiplier=2.0,
    it_freeze=True,               # AI changes frozen during rule-change compliance
    affected_departments=["litigation", "knowledge_mgmt", "it_innovation"],
)

ETHICS_OPINION_AI = EnvironmentalEvent(
    name="Bar Ethics Opinion on AI",
    description="The state bar issues an ethics opinion on AI use — competence (Rule 1.1), confidentiality (1.6), and supervision (5.3) obligations for AI-assisted work. Heightens the stakes on privilege, citation-checking, and attorney oversight.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.08,
    duration_sprints=2,
    cooldown_sprints=5,
    matter_volume_multiplier=1.0,
    budget_multiplier=1.0,
    stress_multiplier=1.2,
    regulation_multiplier=2.5,
    affected_departments=["litigation", "knowledge_mgmt", "executive"],
)


# === INTERNAL EVENTS ===

KEY_PERSON_DEPARTURE = EnvironmentalEvent(
    name="Key Person Departure",
    description="A critical non-partner role (senior associate, KM partner, IT lead) leaves. One random agent is replaced with a different profile. The tacit knowledge they held walks out the door.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.06,
    duration_sprints=1,
    cooldown_sprints=2,
    matter_volume_multiplier=1.0,
    budget_multiplier=1.0,
    stress_multiplier=1.2,
    affected_departments=["litigation", "knowledge_mgmt", "it_innovation"],
)

IT_SYSTEM_OUTAGE = EnvironmentalEvent(
    name="IT System Outage (Major)",
    description="The document management system, e-discovery platform, or practice-management system experiences a significant outage. All IT changes frozen; matters slow.",
    severity=EventSeverity.HIGH,
    probability_per_sprint=0.04,
    duration_sprints=1,
    cooldown_sprints=3,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.95,
    stress_multiplier=1.5,
    it_freeze=True,
    transformation_pause=True,
    affected_departments=["it_innovation", "litigation", "legal_ops"],
)

BUDGET_SHIFT = EnvironmentalEvent(
    name="Budget Shift (±20%)",
    description="Quarterly reforecast shifts the transformation budget by ±20%.",
    severity=EventSeverity.LOW,
    probability_per_sprint=0.12,
    duration_sprints=1,
    cooldown_sprints=1,
    matter_volume_multiplier=1.0,
    budget_multiplier=None,          # determined by draw: 0.8 or 1.2
    stress_multiplier=1.05,
    affected_departments=["it_innovation", "executive", "legal_ops"],
)

NEGATIVE_PRESS_EVENT = EnvironmentalEvent(
    name="Malpractice / Ethics Violation Public",
    description="A missed conflict, a privilege waiver, or an AI hallucination in a filed brief becomes public. Reputation damage, potential malpractice exposure, and regulator/bar attention.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.03,
    duration_sprints=2,
    cooldown_sprints=8,
    matter_volume_multiplier=1.0,
    budget_multiplier=1.0,
    stress_multiplier=1.3,
    regulation_multiplier=1.5,
    affected_departments=["litigation", "executive", "legal_ops"],
)


# === TECHNOLOGY / VENDOR EVENTS ===

NEW_TECH_AVAILABLE = EnvironmentalEvent(
    name="New Legal AI Capability Available",
    description="A major model or vendor release creates a step-change — reliable AI drafting, agentic e-discovery, or citation-guaranteed research. Genuinely expands what's possible.",
    severity=EventSeverity.MODERATE,
    probability_per_sprint=0.06,
    duration_sprints=1,
    cooldown_sprints=3,
    matter_volume_multiplier=1.0,
    budget_multiplier=1.0,
    stress_multiplier=1.0,
    urgency_spike=True,
    affected_departments=["it_innovation", "litigation", "executive"],
)

LEGACY_SYSTEM_EOL = EnvironmentalEvent(
    name="Legacy System End-of-Life",
    description="A critical vendor (document management, practice management, or time/billing) announces version sunset with a hard deadline. Migration consumes IT bandwidth; every department fights for priority.",
    severity=EventSeverity.HIGH,
    probability_per_sprint=0.06,
    duration_sprints=4,
    cooldown_sprints=12,
    matter_volume_multiplier=1.0,
    budget_multiplier=0.80,
    stress_multiplier=1.5,
    it_freeze=True,
    affected_departments=["it_innovation", "litigation", "legal_ops"],
)


# === ALL EVENTS (for sampling) ===

ALL_EVENTS = [
    # Economic
    RECESSION,
    CLIENT_RATE_PRESSURE,
    INTEREST_RATE_CHANGE,
    # Competitive / client
    COMPETITOR_LEGAL_AI_LAUNCH,
    LATERAL_PARTNER_POACHING,
    CLIENT_MANDATE_AFAS,
    ASSOCIATE_MARKET_TIGHTENING,
    # Regulatory / ethics
    COURT_RULE_CHANGE,
    ETHICS_OPINION_AI,
    # Internal
    KEY_PERSON_DEPARTURE,
    IT_SYSTEM_OUTAGE,
    BUDGET_SHIFT,
    NEGATIVE_PRESS_EVENT,
    # Technology / vendor
    NEW_TECH_AVAILABLE,
    LEGACY_SYSTEM_EOL,
]


@dataclass
class EnvironmentalState:
    """Current state of the simulation environment."""
    sprint: int
    market_phase: MarketPhase
    active_events: list[tuple[EnvironmentalEvent, int]]  # (event, sprints_remaining)
    event_history: list[dict]  # {sprint, event_name, severity, effects}

    @property
    def transformation_paused(self) -> bool:
        return any(e.transformation_pause for e, _ in self.active_events)

    @property
    def it_frozen(self) -> bool:
        return any(e.it_freeze for e, _ in self.active_events)

    @property
    def urgency_elevated(self) -> bool:
        return any(e.urgency_spike for e, _ in self.active_events)

    # Derived factors are PRODUCTS over concurrently-active events, clamped to a
    # defensible range (R4 — an unlucky stack of events shouldn't produce implausible values).
    @property
    def matter_volume_factor(self) -> float:
        factor = 1.0
        for event, _ in self.active_events:
            factor *= event.matter_volume_multiplier
        return min(factor, 3.0)

    @property
    def budget_factor(self) -> float:
        factor = 1.0
        for event, _ in self.active_events:
            factor *= event.budget_multiplier
        return max(0.5, min(factor, 1.5))

    @property
    def stress_factor(self) -> float:
        factor = 1.0
        for event, _ in self.active_events:
            factor *= event.stress_multiplier
        return min(factor, 3.0)

    @property
    def regulation_factor(self) -> float:
        factor = 1.0
        for event, _ in self.active_events:
            factor *= event.regulation_multiplier
        return min(factor, 3.0)

    def summary(self) -> str:
        lines = [
            f"Sprint {self.sprint} | Market: {self.market_phase.value}",
            f"  Matter volume: {self.matter_volume_factor:.1f}x | Budget: {self.budget_factor:.2f}x",
            f"  Stress: {self.stress_factor:.1f}x | Regulation: {self.regulation_factor:.1f}x",
            f"  Transformation paused: {self.transformation_paused} | IT frozen: {self.it_frozen}",
            f"  Active events: {len(self.active_events)}",
        ]
        for event, remaining in self.active_events:
            lines.append(f"    - {event.name} ({event.severity.value}, {remaining} sprints remaining)")
        return "\n".join(lines)


class WorldEngine:
    """
    Generates environmental conditions for the simulation.
    Events are drawn ONCE per sprint and applied identically to both tracks.
    """

    def __init__(self, seed: int = 42):
        self.rng = Random(seed)
        self.state: Optional[EnvironmentalState] = None
        self._event_cooldowns: dict[str, int] = {}

    def initialize(self) -> EnvironmentalState:
        """Set up initial state. Start in a demand market (typical mid-cycle)."""
        self.state = EnvironmentalState(
            sprint=0,
            market_phase=MarketPhase.DEMAND,
            active_events=[],
            event_history=[],
        )
        return self.state

    def advance_sprint(self) -> EnvironmentalState:
        """Advance one sprint: tick down events/cooldowns, check market transition,
        draw new events, apply the major-event concurrency cap. Returns new state."""
        if self.state is None:
            raise ValueError("WorldEngine not initialized. Call initialize() first.")

        current = self.state

        # 1. Tick down active events
        updated_active = []
        for event, remaining in current.active_events:
            if remaining > 1:
                updated_active.append((event, remaining - 1))

        # 2. Tick down cooldowns
        for name in list(self._event_cooldowns.keys()):
            self._event_cooldowns[name] -= 1
            if self._event_cooldowns[name] <= 0:
                del self._event_cooldowns[name]

        # 3. Market cycle transition
        new_phase = current.market_phase
        if current.market_phase == MarketPhase.DEMAND:
            if self.rng.random() < DEMAND_TO_CONTRACTION_TRANSITION_PROB:
                new_phase = MarketPhase.TRANSITIONING
        elif current.market_phase == MarketPhase.TRANSITIONING:
            new_phase = MarketPhase.CONTRACTION
        elif current.market_phase == MarketPhase.CONTRACTION:
            if self.rng.random() < CONTRACTION_TO_DEMAND_TRANSITION_PROB:
                new_phase = MarketPhase.TRANSITIONING

        # 4. Draw random events
        new_events = []
        sprint_num = current.sprint + 1

        for event in ALL_EVENTS:
            if event.name in self._event_cooldowns:
                continue
            if any(e.name == event.name for e, _ in updated_active):
                continue

            if self.rng.random() < event.probability_per_sprint:
                # BUDGET_SHIFT direction determined by a separate draw
                if event.name == "Budget Shift (±20%)":
                    direction = "positive" if self.rng.random() < 0.5 else "negative"
                    event_copy = EnvironmentalEvent(
                        **{**event.__dict__,
                           "description": event.description.replace("±20%", f"{'+20%' if direction == 'positive' else '-20%'}"),
                           "budget_multiplier": 1.2 if direction == 'positive' else 0.8}
                    )
                    new_events.append(event_copy)
                else:
                    new_events.append(event)

                if event.cooldown_sprints > 0:
                    self._event_cooldowns[event.name] = event.cooldown_sprints

        # Cap concurrent MAJOR events (HIGH/EXTREME) at 2 (R4).
        MAX_MAJOR_CONCURRENT = 2
        major = {EventSeverity.HIGH, EventSeverity.EXTREME}
        carried_major = sum(1 for e, _ in updated_active if e.severity in major)
        kept, drawn_major = [], carried_major
        for e in new_events:
            if e.severity in major:
                if drawn_major >= MAX_MAJOR_CONCURRENT:
                    if e.cooldown_sprints > 0:
                        self._event_cooldowns.pop(e.name, None)
                    continue
                drawn_major += 1
            kept.append(e)
        all_active = updated_active + [(e, e.duration_sprints) for e in kept]

        # 5. Update state
        event_log = []
        for event, _ in all_active:
            event_log.append({
                "sprint": sprint_num,
                "event_name": event.name,
                "severity": event.severity.value,
                "effects": {
                    "matter_volume_multiplier": event.matter_volume_multiplier,
                    "budget_multiplier": event.budget_multiplier,
                    "stress_multiplier": event.stress_multiplier,
                    "regulation_multiplier": event.regulation_multiplier,
                },
            })

        self.state = EnvironmentalState(
            sprint=sprint_num,
            market_phase=new_phase,
            active_events=all_active,
            event_history=current.event_history + event_log,
        )
        return self.state

    def get_effective_parameters(self) -> dict:
        """Collapse the EnvironmentalState into the flat params dict the
        orchestrator and tracks consume (factors + active-event names + flags)."""
        if self.state is None:
            raise ValueError("WorldEngine not initialized. Call initialize() first.")
        s = self.state
        return {
            "matter_volume_factor": s.matter_volume_factor,
            "budget_factor": s.budget_factor,
            "stress_factor": s.stress_factor,
            "regulation_factor": s.regulation_factor,
            "transformation_paused": s.transformation_paused,
            "it_frozen": s.it_frozen,
            "urgency_elevated": s.urgency_elevated,
            "active_event_names": [e.name for e, _ in s.active_events],
        }
