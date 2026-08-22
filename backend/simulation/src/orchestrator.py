"""
Simulation orchestrator — the top-level loop for a single, parameterized firm.

Runs ONE firm through `sprints` quarterly sprints. The firm is described by a
`FirmSignature` (pricing posture, leverage ratio, origination concentration, …);
the levers are its config knobs, and the outcome is the firm's own P&L (PPP,
realization, margin, leverage, attrition).

Each sprint:
1. Advance the environment (events).
2. Generate a matter batch.
3. Process the batch through the litigation workflow (AI-assisted per adoption).
4. Apply trust cascade + attrition contagion.
5. Collect metrics (with the levers applied — pricing → margin, etc.).
6. Log.
"""

import copy
import os
import asyncio
import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable

from .models.company import CompanyState, create_company
from .models.matters import (
    Matter, MatterComplexity, MatterStatus,
    WORKFLOW_STEP_MAP, route_matter,
)
from .models.events import WorldEngine
from .models.legal_tools import get_tool
from .models.metrics import MetricSnapshot, MetricHistory, METRICS
from .models.elasticities import ElasticityProfile, default_profile
from .engine.agents import AgentStates, AgentDecision, AgentRuntime
from .engine.dynamics import (
    process_attrition, AttritionState,
    propagate_trust_cascade,
    TrustState,
)
from .engine.state import SprintLog, SimulationRun, StateSerializer
from .utils.trace import TraceLog

MAX_MATTER_STEPS = 50
FIRM_TRACK = "firm"   # single firm — the "track" label is a logging convention only


# === DETERMINISTIC AI SEAM FRICTION ===

def _ai_failure(matter_id: str, step_name: str, error_rate: float, sprint: int,
                env_params: Optional[dict] = None, context_complete: bool = False) -> bool:
    """Deterministic AI auto-processing failure (pure function of state, no RNG)."""
    if error_rate <= 0:
        return False
    digest = hashlib.md5(f"{matter_id}:{step_name}:{sprint}".encode()).hexdigest()
    roll = int(digest[:8], 16) / (16 ** 8)
    effective = error_rate
    if env_params:
        volume = env_params.get("matter_volume_factor", 1.0)
        effective *= 1.0 + 0.5 * max(0.0, volume - 1.0)
    if context_complete:
        effective *= 0.7
    effective = max(0.01, min(0.95, effective))
    return roll < effective


# Purely procedural steps — filing on standardized court rails, payment collection,
# and file closure. They carry the lowest seam risk in the workflow and exercise
# none of the AI-adoption / trust / redline dynamics the sim measures, so paying for
# a full LLM reasoning call on each is waste. Processed deterministically instead:
# ~20% fewer LLM calls, identical experimental signal.
ADMIN_STEPS = {"filing", "collection", "closed"}


def _scripted_admin_decision(matter_id: str, step, sprint: int) -> AgentDecision:
    """Deterministically clear a procedural admin step — no LLM call. Attributed to the
    ai_pipeline sentinel so it's excluded from agent-decision + LLM-call accounting, and
    marked used_ai=False so it never inflates AI-adoption metrics."""
    return AgentDecision(
        matter_id=matter_id,
        step_name=step.name,
        agent_role_id="ai_pipeline",
        agent_name="Admin Pipeline",
        track=FIRM_TRACK,
        decision="approve",
        reasoning=f"Procedural step {step.name} processed on standardized rails.",
        used_ai=False,
        ai_was_correct=None,
        ai_confidence=None,
        processing_time_sprints=0.02,
    )


def _ai_auto_decision(matter_id: str, step, sprint: int, agent_name: str,
                      ai_confidence: float, success_reasoning: str,
                      env_params: Optional[dict] = None) -> AgentDecision:
    """Auto-process an AI-capable step: succeed, or fail at the seam into a translation incident."""
    if _ai_failure(matter_id, step.name, step.ai_error_rate, sprint,
                   env_params=env_params,
                   context_complete=getattr(step, "context_complete", False)):
        return AgentDecision(
            matter_id=matter_id,
            step_name=step.name,
            agent_role_id="ai_pipeline",
            agent_name=agent_name,
            track=FIRM_TRACK,
            decision="escalate",
            reasoning=f"AI processed {step.name} but its output lost meaning at the handoff",
            used_ai=True,
            ai_was_correct=False,
            ai_confidence=0.5,
            translation_incident=True,
            exception_raised=True,
            processing_time_sprints=0.3,
        )
    return AgentDecision(
        matter_id=matter_id,
        step_name=step.name,
        agent_role_id="ai_pipeline",
        agent_name=agent_name,
        track=FIRM_TRACK,
        decision="accept_ai",
        reasoning=success_reasoning,
        used_ai=True,
        ai_was_correct=True,
        ai_confidence=ai_confidence,
        processing_time_sprints=0.05,
    )


# === THE FIRM'S CONTEXT SIGNATURE ===

@dataclass
class CultureProfile:
    """The firm's collective norms, captured through OBSERVABLE proxies — not abstract
    scales. Each field is an answerable question about what the firm does, and maps to a
    grounded mechanism. (Abstract 'how innovative are you' scales are un-defensible.)"""
    partner_ai_usage: float = 0.69    # % of partners who've personally used a legal AI tool [SURVEY: 69%]
    attrition_intensity: float = 0.19 # associate churn / up-or-out intensity [SURVEY: NALP 19%]
    escalation_design: float = 0.5    # 0=ad-hoc "whoever shouts loudest", 1=designed escalation path [ASSUMPTION]


@dataclass
class FirmSignature:
    """
    The dimensions that determine which lever is highest-leverage for THIS firm.

    These are the inputs — set directly, no org-data import. Each maps onto the
    firm's structural posture and, in turn, which levers move its P&L.

    Tier 1 (change the answer) — work composition, comp model, client pressure,
    partner demographics. Tier 2 (ground + refine) — actual financials, tech maturity.
    """
    # --- structural posture (the original six) ---
    pricing_posture: str = "hourly"          # "hourly" | "partial_afa" | "afa_native"
    leverage_ratio: float = 3.5              # associate:partner ratio (pyramid steepness)
    origination_concentration: float = 0.4   # 0=distributed book, 1=one dominant rainmaker
    practice_mix_transactional: float = 0.35 # 0=all litigation, 1=all transactional
    client_concentration: float = 0.3        # 0=many clients, 1=one whale
    partner_power_mix: float = 0.5           # 0=cooperative, 1=rainmaker veto strong

    # --- Tier 1: work, comp, clients, people ---
    tacit_work_share: float = 0.5            # 0=all routine/codifiable, 1=all bet-the-company tacit (drives matter mix)
    comp_model: str = "modified"             # "lockstep" | "modified" | "eat_what_you_kill" (drives comp lever ceiling)
    client_afa_pressure: float = 0.3         # 0=no client demands AFA, 1=clients will leave without it
    partner_retirement_horizon: float = 10.0 # avg years to retirement (low = resistance is temporary)

    # --- Tier 2: ground the numbers + tech maturity ---
    baseline_ppp: float = 3_000_000          # [SURVEY] mid-AmLaw-100; override with the firm's real PPP
    baseline_rpl: float = 1_200_000          # [SURVEY]
    baseline_realization: float = 85.0       # [SURVEY]
    baseline_margin: float = 30.0            # [INFERRED]
    tech_maturity: float = 0.4               # 0=no KM/data infra, 1=fully codified (fewer gappy seams)

    # --- Culture (the collective-norms facet — distinct from individual psychology) ---
    culture: CultureProfile = field(default_factory=CultureProfile)

    def apply_to(self, company: CompanyState):
        """Map the signature onto the company's structural posture."""
        company.pricing_model = {
            "hourly": "hourly", "partial_afa": "hourly", "afa_native": "fixed_fee",
        }[self.pricing_posture]
        company.leverage_target = self.leverage_ratio
        # client concentration -> pass-vs-absorb pressure (a whale can force savings through)
        company.absorb_vs_pass = "pass" if self.client_concentration > 0.6 else "absorb"


@dataclass
class SimulationConfig:
    """Configuration for a single-firm run."""
    run_id: str = field(default_factory=lambda: datetime.now().strftime("run_%Y%m%d_%H%M%S"))
    sprints: int = 16
    matters_per_sprint: int = 50
    output_dir: str = "results"
    seed: int = 42

    # The firm
    firm_name: str = "Aldrich & Vale LLP"       # shown in the report; comes from the config
    firm_signature: Optional[FirmSignature] = None

    # Levers (the intervention set — each a knob the sim sweeps)
    comp_lever_strength: float = 0.3            # comp lever: pay partners for AI (0-1) -> adoption
    decision_latency_sprints: int = 2           # latency lever: observe->act speed -> adoption ramp
    seam_gap_profile: Optional[str] = None      # CONTEXT: which seams start gappy (tacit/codifiable/mixed)
    codify_seams: bool = False                  # seams lever (intervention): invest to codify tacit seams over the run
    # Transfer-function coefficients (how strongly levers move the numbers). Defaults
    # reproduce the prior hardcoded literals exactly; vary for sensitivity bands or set
    # from firm calibration. See src/models/elasticities.py.
    elasticities: Optional["ElasticityProfile"] = None
    legal_tool: str = "mock"
    no_ai: bool = False
    max_cost: Optional[float] = None            # real-LLM spend cap ($): stop early if exceeded

    # LLM
    llm_provider: str = "mock"
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_concurrency: int = field(
        default_factory=lambda: int(os.environ.get("LLM_CONCURRENCY", "16"))
    )


class Orchestrator:
    """Top-level simulation controller for a single firm."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.sim: Optional[SimulationRun] = None
        self.trace = TraceLog()
        # Optional per-sprint progress hook, fired after each sprint's metrics are committed.
        # Signature: on_progress(sprint: int, latest_metrics: dict). Default None = no-op,
        # so the CLI and tests behave exactly as before.
        self.on_progress: Optional[Callable[[int, dict], None]] = None

        from .engine.llm_client import create_llm_client
        self.llm = create_llm_client(
            provider=config.llm_provider,
            model=config.llm_model,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            temperature=config.llm_temperature,
            seed=config.seed,
        )

    def initialize(self):
        self.sim = SimulationRun(run_id=self.config.run_id, sprints_total=self.config.sprints)
        self.sim.world = WorldEngine(seed=self.config.seed)

        # Apply the firm signature.
        if self.config.firm_signature is not None:
            self.config.firm_signature.apply_to(self.sim.company)

        self.sim.initialize()

        import random
        random.seed(self.config.seed)

        self._apply_seam_gap_profile()
        self._apply_tool_profile()

    # --- profile application ---

    def _apply_seam_gap_profile(self):
        profile = self.config.seam_gap_profile or "tacit"
        TACIT = {
            "partner_review": ["associate_draft", "research_memo", "prior_redlines", "client_position"],
            "settlement_negotiation": ["matter_history", "client_authority", "counterparty_position", "prior_settlement_patterns"],
            "matter_staffing": ["matter_complexity", "associate_availability", "client_expectation", "leverage_target"],
            "billing": ["time_entries", "client_guidelines", "prior_write_off_history", "matter_budget"],
        }
        CODIFIABLE = {
            "legal_research": ["matter_issues", "jurisdiction", "prior_precedent"],
            "document_review": ["document_corpus", "relevance_protocol", "privilege_protocol"],
            "drafting": ["research_memo", "matter_facts", "prior_precedent", "client_position"],
            "filing": ["final_document", "court_deadline", "service_requirements"],
        }
        if profile == "tacit":
            gappy = TACIT
        elif profile == "codifiable":
            gappy = CODIFIABLE
        else:
            gappy = {**{k: TACIT[k] for k in ("partner_review", "settlement_negotiation")},
                     **{k: CODIFIABLE[k] for k in ("legal_research", "drafting")}}

        wf = self.sim.company.workflow_state
        for s in wf.values():
            s.context_complete = True
            s.handoff_context = []
        # tech_maturity (Tier 2): a firm that has already invested in KM/precedent has
        # codified some tacit seams, so fewer start gappy.
        sig = self.config.firm_signature or FirmSignature()
        keep = int(round(len(gappy) * (1.0 - sig.tech_maturity)))
        for name in list(gappy.keys())[:keep]:
            step = wf.get(name)
            if step is None:
                continue
            step.context_complete = False
            step.handoff_context = list(gappy[name])

    _STEP_TO_OPERATION = {
        "legal_research": "find_cases",
        "citation_check": "verify_quote",
        "drafting": "draft",
        "document_review": "doc_review",
    }

    def _apply_tool_profile(self):
        tool = get_tool(self.config.legal_tool)
        wf = self.sim.company.workflow_state
        for step_name, op_name in self._STEP_TO_OPERATION.items():
            step = wf.get(step_name)
            if step is None:
                continue
            op = tool.op(op_name)
            if op.supports:
                step.ai_capable = True
                step.ai_error_rate = op.accuracy
                step.tacit_residual = op.tacit_residual
            else:
                step.ai_capable = False
                step.ai_error_rate = 1.0
        if self.config.no_ai:
            for step in wf.values():
                step.ai_capable = False
                step.ai_error_rate = 1.0

    # --- run loop ---

    def _adoption_rate(self, sprint: int) -> float:
        """The firm's AI adoption rate this sprint. Ramps toward a ceiling set by the
        comp lever (partners adopt when compensated); the comp model and latency levers
        modulate how effective and how fast."""
        sig = self.config.firm_signature or FirmSignature()
        comp = self.config.comp_lever_strength
        # comp model: lockstep = collective action (comp bites harder); eat-what-you-kill =
        # individual books (partners resist, comp is blunted); modified in between.
        comp_mult = {"lockstep": 1.2, "modified": 1.0, "eat_what_you_kill": 0.8}[sig.comp_model]
        # rainmaker resistance: a concentrated origination book + strong partner veto blunt the
        # comp lever — a firm-wide "pay for AI" change can't move a partner who owns the clients.
        # Centered at the archetype (origination 0.4, power 0.5) so the default firm is unchanged;
        # only deviations bite. [INFERRED from intake mechanisms]
        rainmaker_resistance = max(0.2, min(1.3, 1.0 - 0.5 * (
            (sig.origination_concentration - 0.4) + (sig.partner_power_mix - 0.5))))
        # culture (observable proxy): partners already personally using AI (69% [SURVEY]) set
        # the adoption floor; the comp lever can raise it further (up to ~95%), net of resistance.
        el = self.config.elasticities or default_profile()
        ceiling = min(0.95, max(sig.culture.partner_ai_usage,
                                0.30 + el.get("adoption_comp_gain") * comp * comp_mult * rainmaker_resistance))
        latency = self.config.decision_latency_sprints
        ramp = max(1, 3 + 4 * latency)                     # sprints to reach the ceiling
        return ceiling * min(1.0, sprint / ramp)

    @staticmethod
    def _adopt_roll(matter_id: str, sprint: int) -> float:
        """Deterministic [0,1) roll for whether a matter uses AI this sprint."""
        digest = hashlib.md5(f"adopt:{matter_id}:{sprint}".encode()).hexdigest()
        return int(digest[:8], 16) / (16 ** 8)

    def _codify_seams(self, sprint: int):
        """The seams lever (INTERVENTION): the firm invests in codifying its tacit seams —
        building the precedent library, standardizing the handoffs — so one gappy seam is
        completed every few sprints. Distinct from `seam_gap_profile`, which is the CONTEXT
        (which seams start gappy). Completing a seam (context_complete=True) removes its
        translation debt, at the cost of the codification investment (applied in _collect_metrics)."""
        if sprint % 3 != 0:
            return
        wf = self.sim.company.workflow_state
        gappy = [s for s in wf.values() if not s.context_complete]
        if not gappy:
            return
        target = max(gappy, key=lambda s: s.seam_risk)  # codify the worst handoff first
        target.context_complete = True
        target.handoff_context = list(target.inputs_required)
        self.trace.firm_action(sprint, "codify_seam", {"seam": target.name})

    async def run(self) -> SimulationRun:
        if self.sim is None:
            raise ValueError("Not initialized.")
        semaphore = asyncio.Semaphore(self.config.llm_concurrency)
        import time as _time
        _started = _time.time()

        for sprint in range(1, self.config.sprints + 1):
            self.sim.advance()
            self.sim.world.advance_sprint()
            env_params = self.sim.world.get_effective_parameters()
            self.sim.env_history.append(dict(env_params))

            # Trace the environmental state: market phase + any active shocks.
            world_state = self.sim.world.state
            self.trace.env_event(sprint, world_state.market_phase.value,
                                 {"stress_factor": env_params.get("stress_factor", 1.0),
                                  "matter_volume_factor": env_params.get("matter_volume_factor", 1.0),
                                  "active_events": [e.name for e, _ in world_state.active_events]})

            adoption_rate = self._adoption_rate(sprint)
            # seams lever (intervention): progressively codify gappy tacit seams.
            if self.config.codify_seams:
                self._codify_seams(sprint)
            batch = self._generate_matter_batch(sprint)
            log = await self._process_matter_batch(
                self.sim.company, self.sim.agent_states, batch, sprint, env_params, semaphore,
                adoption_rate,
            )

            # trust cascade + attrition
            ts = self.sim.agent_states.to_trust_state()
            trust_before = dict(ts.confidence)
            propagate_trust_cascade(self.sim.company, ts)
            self.sim.agent_states.update_from_trust_state(ts)
            for rid, after in ts.confidence.items():
                before = trust_before.get(rid, 0.5)
                if abs(after - before) >= 0.01:
                    self.trace.agent_trust_shift(sprint, rid, before, after, "trust_cascade")
            import random as _random
            rng = _random.Random(self.config.seed + sprint)
            departures = process_attrition(
                self.sim.company, self.sim.attrition, sprint, rng,
                retirement_horizon=(self.config.firm_signature or FirmSignature()).partner_retirement_horizon,
            )
            for dep in departures:
                self.sim.agent_states.states[dep.role_id].active = False
                self.trace.agent_departed(sprint, dep.role_id, dep.reason)

            self._collect_metrics(self.sim.company, log, sprint)
            self.sim.sprint_logs.append(log)

            # Per-sprint progress hook (the runner streams this live). Fires after the
            # sprint's metrics are committed, so the callback sees the finalized state.
            if self.on_progress is not None:
                self.on_progress(sprint, self._latest_metric_snapshot())

            # Live status snapshot for the dashboard (one small JSON, rewritten each sprint).
            self._write_live_status(sprint, _started)

            # Cost cap (real-LLM runs): stop early once estimated spend exceeds the budget.
            if self.config.max_cost is not None:
                spent = getattr(getattr(self.llm, "usage", None), "cost_estimate", 0.0)
                if spent >= self.config.max_cost:
                    print(f"[cost cap] stopping after sprint {sprint}: "
                          f"est. ${spent:.2f} >= cap ${self.config.max_cost:.2f}", flush=True)
                    break

        self.sim.completed = True
        # Mark the live status complete.
        import json as _json
        status_path = Path(self.config.output_dir) / "latest_run.json"
        if status_path.exists():
            data = _json.loads(status_path.read_text())
            data["complete"] = True
            status_path.write_text(_json.dumps(data))
        return self.sim

    def _latest_metric_snapshot(self) -> dict:
        """The latest value of every metric recorded so far — the per-sprint live view."""
        latest = {}
        for metric_id, history in self.sim.company.metric_history.items():
            if history and history.values:
                latest[metric_id] = history.values[-1].value
        return latest

    def _write_live_status(self, sprint: int, started: float):
        """Write results/latest_run.json — the dashboard reads this to show live progress."""
        import time as _time
        decisions = sum(len(l.decisions) for l in self.sim.sprint_logs)
        matters = sum(len(l.matters_completed) for l in self.sim.sprint_logs)
        latest = self._latest_metric_snapshot()
        key = {k: round(latest[k], 2) for k in
               ("ppp", "matter_profit_margin", "realization_rate", "ai_assisted_matter_pct",
                "redline_rework_rate", "associate_attrition")
               if k in latest}
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        import json as _json
        usage = getattr(self.llm, "usage", None)
        (Path(self.config.output_dir) / "latest_run.json").write_text(_json.dumps({
            "run_id": self.sim.run_id,
            "total_sprints": self.config.sprints,
            "current_sprint": sprint,
            "matters_per_sprint": self.config.matters_per_sprint,
            "decisions_so_far": decisions,
            "matters_completed": matters,
            "provider": self.config.llm_provider,
            "llm_model": getattr(self.llm, "model", None) or self.config.llm_model,
            "legal_tool": self.config.legal_tool,
            "complete": False,
            "elapsed_s": round(_time.time() - started, 1),
            # Live LLM spend (real-provider runs; zero on the mock). tokens_in is the
            # TOTAL prompt tokens; cache_hit_tokens is the discounted (cached) portion of
            # it, so uncached = tokens_in - cache_hit_tokens. rate_card carries the exact
            # per-million rates used, so the dashboard can show the arithmetic and you can
            # reconcile against the real DeepSeek invoice line-by-line.
            "api_calls": getattr(usage, "api_calls", 0),
            "tokens_in": getattr(usage, "input_tokens", 0),
            "tokens_out": getattr(usage, "output_tokens", 0),
            "cache_hit_tokens": getattr(usage, "cache_read_tokens", 0),
            "cost_estimate": round(getattr(usage, "cost_estimate", 0.0), 4),
            "rate_card": self._rate_card(),
            "metrics": key,
        }))

    def _rate_card(self) -> Optional[dict]:
        """Per-million-token rates actually used for the cost estimate — single source of
        truth from the pricing table, surfaced so the dashboard can show the math."""
        if self.config.llm_provider == "mock":
            return None
        try:
            from .engine.llm_client import _openai_pricing
            model = getattr(self.llm, "model", "") or self.config.llm_model or ""
            in_miss, out, in_hit = _openai_pricing(model)
            return {
                "model": model,
                "in_miss_per_m": round(in_miss * 1_000_000, 4),
                "in_hit_per_m": round(in_hit * 1_000_000, 4),
                "out_per_m": round(out * 1_000_000, 4),
            }
        except Exception:
            return None

    # --- matter generation ---

    def _generate_matter_batch(self, sprint: int) -> list[Matter]:
        import random
        rng = random.Random(self.config.seed + sprint)
        # tacit_work_share shifts the mix toward partner-judgment work (complex /
        # high-stakes), which is what drives the tacit-seam debt the levers must fix.
        sig = self.config.firm_signature or FirmSignature()
        t = max(0.0, min(1.0, sig.tacit_work_share))
        routine_cut = 0.45 - 0.35 * t          # 0.45 -> 0.10
        complex_cut = routine_cut + (0.35 - 0.05 * t)   # +standard band
        hs_cut = 1.0 - (0.05 + 0.10 * t)        # high-stakes band 0.05 -> 0.15
        matters = []
        for _ in range(self.config.matters_per_sprint):
            roll = rng.random()
            if roll < routine_cut:
                complexity, amount = MatterComplexity.ROUTINE, rng.uniform(50_000, 500_000)
            elif roll < complex_cut:
                complexity, amount = MatterComplexity.STANDARD, rng.uniform(200_000, 5_000_000)
            elif roll < hs_cut:
                complexity, amount = MatterComplexity.COMPLEX, rng.uniform(2_000_000, 50_000_000)
            else:
                complexity, amount = MatterComplexity.HIGH_STAKES, rng.uniform(20_000_000, 500_000_000)
            matters.append(Matter(
                id=f"m{sprint}_{len(matters)}",
                matter_type=rng.choice(["motion_to_dismiss", "discovery", "settlement", "trial"]),
                complexity=complexity,
                amount_in_dispute=amount,
                jurisdiction=rng.choice(["SDNY", "D. Del.", "N.D. Cal.", "E.D. Tex.", "N.D. Ill.", "S.D. Fla."]),
                client_name=rng.choice(["Acme Corp", "Beta Holdings", "Gamma Industries", "Delta Partners", "Epsilon Group"]),
                involves_privilege=(complexity in (MatterComplexity.COMPLEX, MatterComplexity.HIGH_STAKES)) or rng.random() < 0.4,
                has_prior_precedent=rng.random() < 0.5,
                opposing_counsel_known=rng.random() < 0.7,
            ))
        return matters

    # --- matter processing ---

    async def _process_matter_batch(self, company, agent_states, matters, sprint, env_params, semaphore, adoption_rate):
        log = SprintLog(sprint=sprint, events=env_params.get("active_event_names", []))
        runtime = AgentRuntime(track=FIRM_TRACK, states=agent_states)
        trust_snapshot = {rid: s.ai_confidence for rid, s in agent_states.states.items()}

        async def process_one(matter):
            decisions = []
            # Adoption gate: this matter uses AI only if the firm has adopted it this
            # sprint (deterministic roll vs the adoption rate — comp/latency levers).
            uses_ai = self._adopt_roll(matter.id, sprint) < adoption_rate
            if not matter.pipeline:
                matter.pipeline = route_matter(matter.complexity)
            current = matter.current_step
            step_count = 0
            request_info_count = 0
            while current and current != "closed":
                step_count += 1
                if step_count > MAX_MATTER_STEPS:
                    matter.status = MatterStatus.ESCALATED
                    break
                step = company.workflow_state.get(current)
                if step is None:
                    break
                role = company.get_role(step.role_responsible)
                if role is None:
                    current = step.handoff_to[0] if step.handoff_to else "closed"
                    continue
                agent_state = agent_states.get(role.id)
                if agent_state and not agent_state.active:
                    current = step.handoff_to[0] if step.handoff_to else "closed"
                    continue
                # Procedural admin steps: process deterministically, no LLM call.
                if step.name in ADMIN_STEPS:
                    decision = _scripted_admin_decision(matter.id, step, sprint)
                    decisions.append(decision)
                    matter.handoffs += 1
                    current = step.handoff_to[0] if step.handoff_to else "closed"
                    matter.current_step = current
                    continue
                if uses_ai and matter.pipeline == "codifiable" and step.ai_capable and step.exception_path:
                    decision = _ai_auto_decision(matter.id, step, sprint, "AI Pipeline", 0.90,
                                                 f"AI auto-processed {step.name}", env_params=env_params)
                    decisions.append(decision)
                    matter.ai_touched = True
                    if agent_state is not None:
                        if decision.translation_incident:
                            agent_state.negative_ai_experiences += 1
                            agent_state.translation_incidents += 1
                        else:
                            agent_state.positive_ai_experiences += 1
                    current = step.exception_path if decision.decision == "escalate" else (step.handoff_to[0] if step.handoff_to else "closed")
                    continue
                decision = await runtime.process_matter_step(
                    role=role, matter=matter, step=step, previous_decisions=matter.decisions,
                    env_params=env_params, llm_call=self.llm, semaphore=semaphore, trust_snapshot=trust_snapshot,
                )
                decisions.append(decision)
                if decision.used_ai and uses_ai:
                    matter.ai_touched = True
                if decision.decision == "escalate":
                    current = step.exception_path if step.exception_path and step.exception_path in company.workflow_state else (step.handoff_to[0] if step.handoff_to else "closed")
                elif decision.decision == "request_info":
                    current = step.handoff_to[0] if step.handoff_to else "closed"
                elif decision.next_step and decision.next_step in company.workflow_state:
                    current = decision.next_step
                else:
                    current = step.handoff_to[0] if step.handoff_to else "closed"
                matter.current_step = current
                matter.handoffs += 1
                if decision.decision == "request_info":
                    request_info_count += 1
                    if request_info_count <= 2:
                        matter.handoffs += 1
            matter.completed_at_sprint = sprint
            if current == "closed":
                matter.status = MatterStatus.CLOSED
            elif matter.status != MatterStatus.ESCALATED:
                matter.status = MatterStatus.INCOMPLETE
            return decisions

        decision_lists = await asyncio.gather(*(process_one(m) for m in matters))
        for matter, decisions in zip(matters, decision_lists):
            for d in decisions:
                log.decisions.append(d)
                if d.agent_role_id != "ai_pipeline":
                    self.trace.agent_decision(sprint, d)
                    self.trace.llm_call(sprint, d, self.config.llm_provider,
                                        getattr(self.llm, "model", None) or self.config.llm_model or self.config.llm_provider)
            log.matters_completed.append(matter)
        for role_id, state in agent_states.states.items():
            log.agent_state_summaries[role_id] = state.summary()
        return log

    # --- metrics ---

    def _collect_metrics(self, company: CompanyState, log: SprintLog, sprint: int):
        decisions = log.decisions
        matters = log.matters_completed
        total_decisions = len(decisions)
        partner_roles = {"managing_partner", "rainmaker_partner", "service_partner",
                         "practice_group_leader", "km_partner", "billing_partner"}
        associate_roles = {"senior_associate", "mid_associate", "junior_associate"}

        translation_incidents = sum(1 for d in decisions if d.translation_incident)
        exceptions = sum(1 for d in decisions if d.exception_raised)

        company.record_metric("translation_debt_index", sprint, (translation_incidents / max(total_decisions, 1)) * 100)
        company.record_metric("exception_rate", sprint, (exceptions / max(total_decisions, 1)) * 100)
        # Handoff failure = share of the actual step-to-step HAND-OFFS that broke (a translation
        # incident), not "matters with any incident" — the latter saturates at 100% because nearly
        # every 15-step matter accumulates at least one, so it can't discriminate. Denominator is
        # the total hand-offs across all matters this sprint.
        handoffs_total = sum(m.handoffs for m in matters)
        company.record_metric("handoff_failure_rate", sprint,
                              (translation_incidents / max(handoffs_total, 1)) * 100)

        partner_review_decisions = [d for d in decisions if d.step_name == "partner_review"]
        # Redline rework = the partner actually had to REWRITE the work (overrode the AI, or the
        # hand-off garbled meaning). `escalate`/`request_info` are normal routing, not rewrites —
        # counting them pegged this at 100%.
        redline_rework = sum(1 for d in partner_review_decisions
                             if d.translation_incident or d.decision == "override_ai")
        redline_pct = (redline_rework / max(len(partner_review_decisions), 1)) * 100 if partner_review_decisions else 0
        company.record_metric("redline_rework_rate", sprint, redline_pct)

        if matters:
            avg_handoffs = sum(m.handoffs for m in matters) / max(len(matters), 1)
            avg_proc_time = sum(d.processing_time_sprints for d in decisions) / max(len(decisions), 1)
            company.record_metric("matter_cycle_time", sprint, avg_handoffs + avg_proc_time * 10)

        exc_rate_pct = (exceptions / max(total_decisions, 1)) * 100
        debt_pct = (translation_incidents / max(total_decisions, 1)) * 100
        ai_assisted = sum(1 for m in matters if m.ai_touched)
        ai_pct = (ai_assisted / max(len(matters), 1)) * 100

        # Firm's own financial baselines (Tier 2) — the archetype defaults unless overridden.
        sig = self.config.firm_signature or FirmSignature()
        base_realization = sig.baseline_realization
        base_margin = sig.baseline_margin
        base_ppp = sig.baseline_ppp
        base_rpl = sig.baseline_rpl

        # escalation_design (culture): a designed escalation path catches exceptions early and
        # resolves them, so fewer become financial problems [ASSUMPTION].
        exc_rate_pct = max(0.0, exc_rate_pct - sig.culture.escalation_design * 10.0)

        el = self.config.elasticities or default_profile()
        realization = base_realization - exc_rate_pct * el.get("realization_exception_penalty") - debt_pct * 0.3
        if company.absorb_vs_pass == "pass":
            realization -= 6.0
        # client AFA pressure: stay hourly while clients demand AFA -> realization leaks.
        if company.pricing_model == "hourly":
            realization -= sig.client_afa_pressure * el.get("realization_afa_leak")
        # Floor at 55% — a firm under maximum debt + rate pressure genuinely collects ~55%.
        # (Was 64, which sat above the raw value and masked the Tier-1 inputs.)
        realization = max(55.0, realization)

        # practice mix: transactional work is already effectively fixed-fee, so it cushions the
        # hourly AI penalty (fewer billable hours to lose) and slightly amplifies the AFA benefit.
        # Centered at the archetype (0.35) so the default firm's margin is unchanged. [SURVEY]
        ptx = max(0.0, min(1.0, sig.practice_mix_transactional))
        margin = base_margin - redline_pct * el.get("margin_redline_penalty") - exc_rate_pct * el.get("margin_exception_penalty")
        if company.pricing_model == "fixed_fee":
            margin += ai_pct * el.get("margin_ai_afa_gain") * (1.0 + 0.3 * (ptx - 0.35))
        elif company.pricing_model == "hourly":
            margin -= ai_pct * el.get("margin_ai_hourly_drag") * (1.0 - 0.6 * (ptx - 0.35))
        # codification investment: the seams lever costs KM staff + precedent-library build [ASSUMPTION].
        if self.config.codify_seams:
            margin -= 1.0
        margin = max(5.0, margin)

        # Leverage lever: a steeper pyramid (higher leverage_target) means MORE juniors per
        # partner, so AI's hour-compression cuts utilization harder. Scale the AI cut by the
        # leverage ratio relative to the archetype baseline (~3.5).
        leverage = getattr(company, "leverage_target", 3.5)
        utilization_cut = ai_pct * el.get("utilization_ai_cut") * (leverage / 3.5)
        util_baseline = METRICS["utilization"].baseline
        utilization = max(0.0, util_baseline - utilization_cut)
        company.record_metric("utilization", sprint, utilization)

        # PPP scales with collection (realization), profitability (margin), AND how much of
        # the pyramid stays billable (utilization) — the three channels a lever can move.
        # Routing utilization into PPP is what lets the LEVERAGE lever reach the headline:
        # a steeper pyramid amplifies AI's hour-compression, so more leverage = more billable
        # hours lost per partner. RPL (revenue per lawyer) scales with collection × utilization.
        realization_factor = realization / base_realization
        margin_factor = margin / base_margin
        utilization_factor = utilization / util_baseline
        ppp = base_ppp * realization_factor * margin_factor * utilization_factor
        rpl = base_rpl * realization_factor * utilization_factor
        company.record_metric("realization_rate", sprint, realization)
        company.record_metric("matter_profit_margin", sprint, margin)
        company.record_metric("ppp", sprint, ppp)
        company.record_metric("rpl", sprint, rpl)

        # Adoption (the comp lever's domain) — the fraction of matters AI touched.
        company.record_metric("ai_assisted_matter_pct", sprint, ai_pct)
        # Associate attrition responds to how the transformation is landing, not just to fixed
        # inputs. Baseline is the firm's observed churn [NALP 19% SURVEY]; a leverage term (more
        # juniors in the up-or-out tournament) plus two dynamic pressures: low associate AI trust
        # (they lose faith in the new way of working) and a heavy exception load (frustrating,
        # error-prone work drives people out). Was a static formula of two constants — inert.
        assoc_conf = [s.ai_confidence for rid, s in self.sim.agent_states.states.items()
                      if rid in associate_roles]
        assoc_trust = sum(assoc_conf) / len(assoc_conf) if assoc_conf else 0.5
        attrition = (sig.culture.attrition_intensity * 100
                     + (leverage - 3.5) * 2.0
                     + max(0.0, 0.5 - assoc_trust) * el.get("attrition_trust_sensitivity")
                     + exc_rate_pct * 0.05)
        company.record_metric("associate_attrition", sprint, attrition)
        company.record_metric("collection_cycle", sprint, 90 + exc_rate_pct * 0.3)
        company.record_metric("wip_aging", sprint, 75 + debt_pct * 0.15)

        confidence = {rid: s.ai_confidence for rid, s in self.sim.agent_states.states.items()}
        partner_vals = [v for rid, v in confidence.items() if rid in partner_roles]
        associate_vals = [v for rid, v in confidence.items() if rid in associate_roles]
        if partner_vals:
            company.record_metric("partner_ai_trust", sprint, (sum(partner_vals) / len(partner_vals)) * 10)
        if associate_vals:
            company.record_metric("associate_ai_trust", sprint, (sum(associate_vals) / len(associate_vals)) * 10)

        trust_vals = list(confidence.values())
        if len(trust_vals) > 1:
            mean_t = sum(trust_vals) / len(trust_vals)
            company.record_metric("trust_polarization", sprint,
                (sum((v - mean_t) ** 2 for v in trust_vals) / len(trust_vals)) ** 0.5 * 10)

        # First-pass accuracy = share of individual STEPS done right the first time (no incident,
        # no exception), not "matters that were perfectly clean end-to-end" — the latter pegs at 0%
        # because almost no 15-step matter is flawless, so it can't discriminate.
        clean_steps = sum(1 for d in decisions if not (d.translation_incident or d.exception_raised))
        company.record_metric("first_pass_accuracy", sprint, (clean_steps / max(total_decisions, 1)) * 100)

        log.metric_snapshots = []
        for metric_id in METRICS:
            history = company.metric_history.get(metric_id)
            if history and history.values:
                log.metric_snapshots.append(history.values[-1])

        # Trace a compact sprint-end snapshot for the audit trail.
        snap = {metric_id: history.values[-1].value
                for metric_id, history in company.metric_history.items()
                if history and history.values}
        self.trace.metric_snapshot(sprint, snap)

    # --- export ---

    def export_results(self, run: SimulationRun = None):
        run = run or self.sim
        if run is None:
            return
        output_dir = Path(self.config.output_dir) / run.run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        sig = self.config.firm_signature or FirmSignature()
        # Which levers this run actually pulled as an INTERVENTION (vs the firm's own state) —
        # so the report can say plainly "here's what we changed." A firm's structural posture
        # (e.g. a firm whose leverage IS 4.0, or that already bills AFA) is not a lever pull.
        # The leverage lever is pulled to 5.0 by the optimizer; the pricing lever to afa_native.
        levers_pulled = {
            "pricing": sig.pricing_posture == "afa_native",
            "leverage": sig.leverage_ratio >= 5.0,
            "comp": self.config.comp_lever_strength >= 0.6,
            "seams": bool(self.config.codify_seams),
            "latency": self.config.decision_latency_sprints <= 1,
        }
        with open(output_dir / "meta.json", "w") as f:
            json.dump({
                "run_id": run.run_id, "seed": self.config.seed,
                "firm_name": self.config.firm_name,
                "sprints": self.config.sprints, "matters_per_sprint": self.config.matters_per_sprint,
                "provider": self.config.llm_provider, "legal_tool": self.config.legal_tool,
                "llm_model": getattr(self.llm, "model", None) or self.config.llm_model,
                # Provider-derived model variance so even an offline (CLI) report discloses it.
                # Mock is deterministic — the band is the model's own spread, not the world's.
                # The web runner's measured sweep (reportgen) overrides this via experiments.
                "model_variance": ({"mode": "deterministic", "count": 0}
                                   if self.config.llm_provider == "mock" else None),
                # Which transfer-function coefficients the FIRM set (vs archetype defaults).
                # The report stamps every number "firm-calibrated" or "archetype default" from
                # this, so a firm that never calibrated is labeled a generic reference scenario.
                "calibrated_elasticities": sorted(
                    (self.config.elasticities or default_profile()).calibrated),
                "levers_pulled": levers_pulled,
                "lever_settings": {
                    "pricing_posture": sig.pricing_posture,
                    "leverage_ratio": sig.leverage_ratio,
                    "comp_lever_strength": self.config.comp_lever_strength,
                    "codify_seams": bool(self.config.codify_seams),
                    "decision_latency_sprints": self.config.decision_latency_sprints,
                },
                "usage": getattr(self.llm, "usage", None).summary() if getattr(self.llm, "usage", None) else None,
                "firm_signature": asdict(self.config.firm_signature) if self.config.firm_signature else None,
            }, f, indent=2)

        StateSerializer.save(run, output_dir / "state.json")
        StateSerializer.export_metrics_csv(run, output_dir / "metrics.csv")
        StateSerializer.export_decisions_jsonl(run, output_dir / "decisions.jsonl")
        trace_path = self.trace.export(output_dir / "trace.jsonl")
        with open(output_dir / "summary.txt", "w") as f:
            f.write(run.summary())

        # Auto-generate the human-readable markdown report into the run folder, so every
        # run is self-documenting — no separate `python3 report.py` step. Pure
        # post-processing of the files just written (no API calls). Wrapped so a report
        # failure can never lose the raw data that already landed.
        try:
            import sys as _sys
            _root = str(Path(__file__).resolve().parents[2])
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            from report import build_report, load_experiments
            exp_path = Path(self.config.output_dir) / "experiments.json"
            experiments = load_experiments(exp_path if exp_path.exists() else None)
            (output_dir / "report.md").write_text(build_report(output_dir, experiments))
            print(f"Report → {output_dir / 'report.md'}")
        except Exception as e:
            print(f"(report.md generation skipped: {e})")

        print(f"Results exported to: {output_dir}")
        return output_dir
