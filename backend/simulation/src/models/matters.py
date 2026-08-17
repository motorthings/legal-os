"""
Matter workflow definitions for the legal simulation.

Models a commercial-litigation matter from intake to collection.
Grounded in the standard AmLaw matter lifecycle, the 2026 GenAI legal-tech
stack (Westlaw/Lexis AI research, e-discovery TAR, drafting assistants like
Harvey/CoCounsel), and the ethics/privilege constraints that govern it.

The workflow is designed to surface the seams — handoff points
where translation debt accumulates, informal control points operate, and
bottlenecks migrate. In law, tacit knowledge is *concentrated* (partners,
paralegals, KM) rather than distributed across a frontline, so the seams are
fewer but deeper than insurance.

Two pipeline tracks exist, mirroring the insurance split but for a different
reason — not AI-vs-human routing, but *which seam carries the tacit judgment*:
- CODIFIABLE SLICES: legal research, e-discovery relevance coding, template
  drafting — where AI is genuinely strong and the seam is standardizable.
- TACIT SLICES: partner review (redlines), settlement negotiation, trial prep —
  where the partner's judgment IS the product and AI automates the 80% that
  was never the value.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

from .workflows import WorkflowStep


class MatterComplexity(str, Enum):
    ROUTINE = "routine"          # form pleadings, low dollar, no privilege edge
    STANDARD = "standard"        # typical commercial matter, motion practice, some discovery
    COMPLEX = "complex"          # multi-party, privilege-heavy, expert testimony
    HIGH_STAKES = "high_stakes"  # bet-the-company, bet-the-practice, trial-bound


class MatterStatus(str, Enum):
    INTAKE_RECEIVED = "intake_received"
    CONFLICTS_CLEARED = "conflicts_cleared"
    ENGAGED = "engaged"
    STAFFED = "staffed"
    RESEARCHED = "researched"
    DOCUMENTS_REVIEWED = "documents_reviewed"
    DRAFTED = "drafted"
    PARTNER_REVIEWED = "partner_reviewed"
    FILED = "filed"
    NEGOTIATING = "negotiating"
    TRIAL_READY = "trial_ready"
    BILLED = "billed"
    COLLECTED = "collected"
    CLOSED = "closed"
    DISPUTED = "disputed"        # exception path
    ESCALATED = "escalated"      # exception path — partner rescue required
    INCOMPLETE = "incomplete"    # ran out of workflow steps without closing
    WITHDRAWN = "withdrawn"      # client pulled the matter


@dataclass
class Matter:
    """A single matter instance moving through the litigation workflow.

    Carries the processing-state contract (status, current_step, decisions,
    exceptions_raised, translation_incidents, ai_* flags) so the engine's agent
    runtime binds to it unchanged. The domain fields are legal.
    """
    id: str
    matter_type: str          # "motion_to_dismiss", "discovery", "settlement", "trial"
    complexity: MatterComplexity
    amount_in_dispute: float  # dollars at stake
    jurisdiction: str         # "SDNY", "D. Del.", "N.D. Cal.", etc.

    # Matter details
    client_name: str
    involves_privilege: bool  # privilege review = the tacit, high-stakes edge
    has_prior_precedent: bool
    opposing_counsel_known: bool
    has_documents: bool = True  # e-discovery corpus present

    # Processing state (engine contract)
    status: MatterStatus = MatterStatus.INTAKE_RECEIVED
    current_step: str = "intake"
    assigned_associate: Optional[str] = None   # role_id
    assigned_partner: Optional[str] = None     # role_id
    pipeline: Optional[str] = None             # "codifiable" | "tacit" — set at staffing

    # Workflow metrics
    started_at_sprint: int = 0
    completed_at_sprint: Optional[int] = None
    time_at_each_step: dict[str, int] = field(default_factory=dict)  # step → sprints
    exceptions_raised: int = 0
    handoffs: int = 0
    translation_incidents: int = 0      # handoff failures, reconciliation, ambiguity repair
    redline_rework: int = 0             # NEW — times the partner substantially rewrote an AI draft

    # Decisions made
    decisions: list[dict] = field(default_factory=list)  # [{step, agent, decision, reasoning}]

    # AI involvement
    ai_touched: bool = False
    ai_decision_overridden: bool = False
    human_review_triggered: bool = False


# === THE COMMERCIAL LITIGATION WORKFLOW ===
# 14 substantive steps + the closed terminal = 15 total, grounded in the standard
# AmLaw matter lifecycle + the 2026 GenAI
# legal-tech stack. Each step is scored for seam_risk (translation-debt
# likelihood at the handoff) and seam_tacitness (0=codifiable via a
# schema/template/precedent-database, 1=lives in an expert's head).
#
# The codifiability thesis: a-priori standardization nails low-tacitness seams;
# observed-failure redesign is required for high-tacitness ones.
# seam_tacitness has a None sentinel (see workflows.WorkflowStep.__post_init__) —
# every step MUST be scored or construction fails loudly.

LITIGATION_WORKFLOW = [
    # === STEP 0: INTAKE ===
    WorkflowStep(
        name="intake",
        description="Client/partner reports the matter. Information collected: parties, forum, amount in dispute, deadlines, basic facts. The intake form asks what the firm's template asks, not what the matter actually needs downstream.",
        role_responsible="junior_associate",
        inputs_required=["client_name", "matter_description"],
        decision_type="classify",
        ai_capable=True,       # AI intake summarization already exists (Clio/Harvey)
        ai_confidence_required=0.85,
        typical_duration_sprints=0.1,
        handoff_to=["conflicts_check"],
        seam_risk=0.5,         # MODERATE: intake collects the form's fields, not the
                               # matter's actual needs — deadlines, opposing counsel,
                               # privilege exposure arrive late.
        seam_tacitness=0.30,   # LOW: intake is a form/schema; the gap is form DESIGN,
                               # which is codifiable. → B territory.
    ),

    # === STEP 1: CONFLICTS CHECK ===
    WorkflowStep(
        name="conflicts_check",
        description="Screen the matter for conflicts against existing representations. The database holds what's been *recorded*; the senior partner's memory holds the lateral relationships and historical adverse positions the database never captured.",
        role_responsible="conflicts_analyst",
        inputs_required=["client_name", "adverse_parties", "matter_description"],
        decision_type="verify",
        ai_capable=True,       # AI conflicts screening is emerging, but incomplete
        ai_confidence_required=0.90,
        typical_duration_sprints=0.15,
        handoff_to=["engagement_letter"],
        exception_path="escaped_to_partner",  # conflicts found → partner judgment
        seam_risk=0.7,         # HIGH: a missed conflict is an ethics violation and a
                               # disqualification — high consequence, not high frequency.
        seam_tacitness=0.55,   # MIXED: the conflicts DATABASE is codifiable, but the
                               # memory of past representations and lateral relationships
                               # is tacit. → contested.
    ),

    # === STEP 2: ENGAGEMENT LETTER ===
    WorkflowStep(
        name="engagement_letter",
        description="Draft and execute the engagement letter — scope, fee arrangement, staffing, matter management terms. Governed by firm templates and client billing guidelines.",
        role_responsible="junior_associate",
        inputs_required=["conflicts_clearance", "client_name", "scope", "fee_arrangement"],
        decision_type="approve",
        ai_capable=True,       # template-based; AI generation is reliable
        ai_confidence_required=0.90,
        typical_duration_sprints=0.1,
        handoff_to=["matter_staffing"],
        seam_risk=0.4,         # MODERATE: template-driven, but scope/fee terms carry
                               # client-negotiation nuance.
        seam_tacitness=0.25,   # LOW: engagement letters are heavily templated and
                               # governed by client guidelines. → B territory.
    ),

    # === STEP 3: MATTER STAFFING ===
    WorkflowStep(
        name="matter_staffing",
        description="Assign the associate/partner team. Leverage target, skill match, and client expectation all matter. A wrong staffing call over- or under-leverages the matter and destroys the economics.",
        role_responsible="practice_group_leader",
        inputs_required=["matter_complexity", "associate_availability", "leverage_target", "client_expectation"],
        decision_type="assess",
        ai_capable=False,      # staffing is a judgment call about people, not data
        ai_confidence_required=1.0,
        typical_duration_sprints=0.2,
        handoff_to=["legal_research", "document_review"],  # splits by matter type
        seam_risk=0.6,         # HIGH: staffing drives the leverage ratio — the firm's
                               # profit engine. Mis-staffing compounds downstream.
        seam_tacitness=0.50,   # MIXED: availability/utilization is codifiable data, but
                               # "who's ready for this client" is judgment. → contested.
    ),

    # === STEP 4: LEGAL RESEARCH ===
    WorkflowStep(
        name="legal_research",
        description="Research the controlling authority — statute, case law, local rules. This is where GenAI is strongest: Westlaw/Lexis AI reliably surfaces and summarizes precedent.",
        role_responsible="mid_associate",
        inputs_required=["matter_issues", "jurisdiction", "prior_precedent"],
        decision_type="assess",
        ai_capable=True,       # the canonical AI-win — research is codifiable
        ai_confidence_required=0.80,
        typical_duration_sprints=0.2,
        handoff_to=["drafting"],
        seam_risk=0.5,         # MODERATE: the classic hallucination risk — AI cites a
                               # case that doesn't exist, or misses binding vs persuasive.
        seam_tacitness=0.20,   # LOW: legal research is precisely the codifiable domain —
                               # statutes, citations, shepardization. → B territory.
    ),

    # === STEP 5: DOCUMENT REVIEW (e-discovery) ===
    WorkflowStep(
        name="document_review",
        description="Review the document corpus for relevance and privilege. TAR (technology-assisted review) handles relevance coding; privilege calls remain human because they carry ethics risk.",
        role_responsible="junior_associate",
        inputs_required=["document_corpus", "relevance_protocol", "privilege_protocol"],
        decision_type="classify",
        ai_capable=True,       # TAR is mature and codifiable for relevance
        ai_confidence_required=0.85,
        typical_duration_sprints=0.4,
        handoff_to=["drafting"],
        exception_path="privilege_review_escalation",
        seam_risk=0.6,         # HIGH: a privilege miss is an ethics violation and waiver
                               # — same high-consequence, low-frequency shape as conflicts.
        seam_tacitness=0.35,   # LOW-MODERATE: relevance coding is a codifiable protocol,
                               # but privilege is a judgment call under Rule 502(d).
                               # → B-leaning.
    ),

    # === STEP 6: DRAFTING ===
    WorkflowStep(
        name="drafting",
        description="Associate drafts the motion/memo/discovery response, assisted by AI. The draft is 80% right — template structure, boilerplate, research integration. The 20% that constitutes judgment is what the partner's redlines will add.",
        role_responsible="mid_associate",
        inputs_required=["research_memo", "matter_facts", "prior_precedent", "client_position"],
        decision_type="assess",
        ai_capable=True,       # drafting assistants (Harvey/CoCounsel) are the flagship use case
        ai_confidence_required=0.80,
        typical_duration_sprints=0.3,
        handoff_to=["associate_review"],
        seam_risk=0.5,         # MODERATE: the drafting seam is where translation debt
                               # between the associate's draft and the partner's judgment
                               # first appears.
        seam_tacitness=0.40,   # LOW-MODERATE: template + precedent drafting is codifiable;
                               # the tacit bit is argument shape and client-risk framing.
                               # → B-leaning.
    ),

    # === STEP 6b: SENIOR-ASSOCIATE REVIEW (first-pass supervision) ===
    # The senior associate supervises the mid/junior draft before it reaches the
    # partner — the first redline pass, the "is this partner-ready" gate that BigLaw
    # leverage runs on. Modeled explicitly so the senior_associate agent actually
    # touches matters (was inert: staffed, trust/stress tracked, zero decisions).
    WorkflowStep(
        name="associate_review",
        description="The senior associate reviews the draft before it reaches the partner — the first redline pass and the 'partner-ready?' gate. Catches the obvious misses so partner time is spent on judgment, not cleanup. A supervisory seam: where the leverage model's quality control actually lives.",
        role_responsible="senior_associate",
        inputs_required=["associate_draft", "research_memo", "matter_facts", "client_position"],
        decision_type="approve",
        ai_capable=False,      # supervisory judgment — "is this partner-ready" is tacit
        ai_confidence_required=1.0,
        typical_duration_sprints=0.2,
        handoff_to=["partner_review"],
        exception_path="escalated_to_partner",
        seam_risk=0.6,         # HIGH: the supervisory seam — a weak first-pass review
                               # pushes cleanup onto the partner, inflating exception load.
        seam_tacitness=0.60,   # MIXED-HIGH: some of the review is checklist (cites, format),
                               # but "partner-ready" judgment is tacit. → contested.
    ),

    # === STEP 7: PARTNER REVIEW (redlines) ===
    WorkflowStep(
        name="partner_review",
        description="The partner reviews and redlines the associate's (or AI's) draft. This is where the partner's judgment lives — the carve-outs, the argument strategy, the client-risk calculus that no template captures. The redlines ARE the product.",
        role_responsible="service_partner",
        inputs_required=["associate_draft", "research_memo", "prior_redlines", "client_position"],
        decision_type="approve",
        ai_capable=False,      # the single most human-judgment step in the workflow
        ai_confidence_required=1.0,
        typical_duration_sprints=0.3,
        handoff_to=["citation_check"],
        exception_path="escalated_to_rainmaker",
        seam_risk=0.8,         # CRITICAL: the highest-tacitness seam. The partner re-reads
                               # every AI draft line-by-line because their billable value is
                               # in the redlines. The bottleneck does NOT migrate past here.
        seam_tacitness=0.85,   # HIGHEST: the partner's judgment is irreducibly tacit — no
                               # template or precedent database captures the carve-outs.
                               # The canonical "high-risk AND tacit" case. → A territory.
    ),

    # === STEP 7b: CITATION CHECK (malpractice gate) ===
    # §7.9 — added as the "verify every cite/quote before filing" step. A real
    # malpractice check: shepardize the authority, confirm each quote is verbatim,
    # flag any hallucinated case or misquoted language. Where this step's tacitness
    # lands depends on the active tool — Descrybe makes it codifiable (B territory),
    # a drafting-only tool leaves it tacit (A territory). The static seam_tacitness
    # below assumes a verification-capable tool; the tool profile (§7.9) re-drives
    # ai_error_rate per tool.
    WorkflowStep(
        name="citation_check",
        description="Verify every citation and quote before filing — shepardize the authority, confirm each quote is verbatim, flag any hallucinated case or misquoted language. A malpractice gate; the tool's verification capability determines how much is codifiable.",
        role_responsible="mid_associate",
        inputs_required=["final_draft", "citation_list", "quote_list", "active_tool"],
        decision_type="verify",
        ai_capable=True,       # citation verification is the canonical AI-win (Descrybe's core)
        ai_confidence_required=0.95,   # high bar — a missed hallucination is malpractice
        typical_duration_sprints=0.2,
        handoff_to=["filing"],
        exception_path="escalated_to_partner",
        seam_risk=0.6,         # HIGH: a missed hallucinated citation is a malpractice/ethics
                               # exposure (Rule 11 / candor to the tribunal).
        seam_tacitness=0.30,   # LOW-MODERATE with a verification-capable tool: quote/treatment
                               # checks are codifiable. Rises toward tacit with a drafting-only
                               # tool (see §7.9). → B territory for Descrybe, contested otherwise.
    ),

    # === STEP 8: FILING ===
    WorkflowStep(
        name="filing",
        description="File the reviewed document with the court or serve on opposing counsel. Deadline-driven, procedural, administrative.",
        role_responsible="paralegal",
        inputs_required=["final_document", "court_deadline", "service_requirements"],
        decision_type="classify",
        ai_capable=True,       # filing runs on standardized procedural rails
        ai_confidence_required=0.95,
        typical_duration_sprints=0.05,
        handoff_to=["settlement_negotiation"],
        seam_risk=0.3,         # LOW: procedural/administrative.
        seam_tacitness=0.15,   # LOW: filing deadlines and service rules are codifiable
                               # (court rules, PACER/CM-ECF). → B territory.
    ),

    # === STEP 9: SETTLEMENT NEGOTIATION ===
    WorkflowStep(
        name="settlement_negotiation",
        description="Negotiate resolution with opposing counsel or the counterparty. Leverage, timing, relationship, and the client's true risk tolerance — all tacit, all held by the partner.",
        role_responsible="rainmaker_partner",
        inputs_required=["matter_history", "client_authority", "counterparty_position", "prior_settlement_patterns"],
        decision_type="negotiate",
        ai_capable=False,      # negotiation is relationship + leverage — irreducible
        ai_confidence_required=1.0,
        typical_duration_sprints=0.5,
        handoff_to=["trial_prep"],
        exception_path="escalated_to_rainmaker",
        seam_risk=0.7,         # HIGH: the settlement seam is where client authority meets
                               # counterparty position — pure judgment.
        seam_tacitness=0.85,   # HIGHEST: leverage, timing, and client-relationship are
                               # irreducibly tacit. → A territory.
    ),

    # === STEP 10: TRIAL PREP ===
    WorkflowStep(
        name="trial_prep",
        description="Prepare for trial — witness prep, exhibit lists, motion in limine, jury themes. High-stakes, judgment-heavy, deadline-compressed.",
        role_responsible="service_partner",
        inputs_required=["case_evidence", "witness_list", "opposing_theory", "client_goals"],
        decision_type="assess",
        ai_capable=False,      # trial strategy is senior-partner judgment
        ai_confidence_required=1.0,
        typical_duration_sprints=0.6,
        handoff_to=["billing"],
        seam_risk=0.6,         # HIGH: trial prep compresses everything — deadlines, stress,
                               # judgment — into a short horizon.
        seam_tacitness=0.80,   # HIGH: jury themes, witness credibility, evidentiary
                               # strategy are senior judgment. → A territory.
    ),

    # === STEP 11: BILLING ===
    WorkflowStep(
        name="billing",
        description="Capture time and issue the invoice. Time capture is mechanical, but the write-off decision — which client tolerates what — is the billing partner's tacit knowledge. Realization is negotiated, not computed.",
        role_responsible="billing_partner",
        inputs_required=["time_entries", "client_guidelines", "prior_write_off_history", "matter_budget"],
        decision_type="approve",
        ai_capable=True,       # AI time capture (narrative generation) is emerging
        ai_confidence_required=0.85,
        typical_duration_sprints=0.2,
        handoff_to=["collection"],
        seam_risk=0.6,         # HIGH: the AI time-capture output produces hours the client
                               # won't pay; the write-off decision reconciles them.
        seam_tacitness=0.45,   # MIXED: time capture + client guidelines are codifiable;
                               # the write-off/realization judgment is tacit. → contested.
    ),

    # === STEP 12: COLLECTION ===
    WorkflowStep(
        name="collection",
        description="Collect payment, close the matter. Collection is downstream of everything — if realization failed, collection shows the damage weeks later.",
        role_responsible="billing_partner",
        inputs_required=["final_invoice", "payment_received", "matter_id"],
        decision_type="pay",
        ai_capable=True,       # collection runs on standardized payment rails
        ai_confidence_required=0.95,
        typical_duration_sprints=0.15,
        handoff_to=["closed"],
        seam_risk=0.5,         # MODERATE: downstream lagging indicator of realization.
        seam_tacitness=0.30,   # LOW: collection is administrative/checklist. → B territory.
    ),

    # === STEP 13: CLOSED ===
    WorkflowStep(
        name="closed",
        description="Matter closed. File archived, client satisfaction surveyed, matter knowledge harvested into the KM system (or not — see INFORMAL_CONTROLS).",
        role_responsible="paralegal",
        inputs_required=["collection_confirmation", "matter_outcome"],
        decision_type="classify",
        ai_capable=True,
        ai_confidence_required=1.0,
        typical_duration_sprints=0.0,
        handoff_to=[],
        seam_risk=0.0,
        seam_tacitness=0.10,   # LOW: file closure is administrative/checklist. → n/a.
    ),
]

# Build step lookup
WORKFLOW_STEP_MAP: dict[str, WorkflowStep] = {step.name: step for step in LITIGATION_WORKFLOW}

# AI auto-processing error rates at the AI-capable steps. Single-to-low-double
# digits, grounded in the 2026 reality that a well-shipped legal-AI step isn't
# wrong 50%+ of the time — the failures are concentrated at the *seams*, not the
# steps themselves. [ASSUMPTION — calibrate during baseline run.]
AI_ERROR_RATES = {
    "legal_research": 0.10,    # hallucinated citations / missed binding authority
    "document_review": 0.08,   # missed privilege / relevance calls
    "drafting": 0.12,          # AI draft misses the client-risk framing the partner adds
    "citation_check": 0.10,    # missed hallucinated citation / misquoted language (baseline;
                               # overridden per-tool by the §7.9 tool profile)
    "billing": 0.15,           # AI time capture produces hours the client won't pay
}
for _name, _rate in AI_ERROR_RATES.items():
    if _name in WORKFLOW_STEP_MAP:
        WORKFLOW_STEP_MAP[_name].ai_error_rate = _rate

# Seam gaps — the handoffs that start "gappy" in both tracks (context_complete=False).
# Each names a step a *human agent* processes that receives an incomplete handoff,
# plus the fields a complete handoff should carry. The four gappy seams are exactly
# the four where tacit knowledge concentrates in a firm.
SEAM_GAPS = {
    "partner_review":         ["associate_draft", "research_memo", "prior_redlines", "client_position"],
    "settlement_negotiation": ["matter_history", "client_authority", "counterparty_position", "prior_settlement_patterns"],
    "matter_staffing":        ["matter_complexity", "associate_availability", "client_expectation", "leverage_target"],
    "billing":                ["time_entries", "client_guidelines", "prior_write_off_history", "matter_budget"],
}
for _name, _fields in SEAM_GAPS.items():
    if _name in WORKFLOW_STEP_MAP:
        WORKFLOW_STEP_MAP[_name].context_complete = False
        WORKFLOW_STEP_MAP[_name].handoff_context = _fields

# Workflow registry
WORKFLOW_REGISTRY = {
    "commercial_litigation": {
        "workflow": LITIGATION_WORKFLOW,
        "start_step": "intake",
        "description": "Commercial litigation from intake to collection",
    },
}

# Pipeline routing — the legal analog of route_to_pipeline. Unlike insurance's
# AI-vs-human split (which routed on complexity), the legal split is about which
# *seams* carry the tacit judgment. v1 routes all matters through the full
# workflow; the codifiable/tacit distinction lives in seam_tacitness, not a fork.
def route_matter(complexity: MatterComplexity) -> str:
    """All matters flow through the full lifecycle; complexity tunes staffing.

    COMPLEX and HIGH_STAKES matters are partner-heavy: they exercise the tacit seams
    (partner_review, settlement) that AI cannot codify. ROUTINE/STANDARD are leverage-heavy:
    AI does more of the work. (Was HIGH_STAKES-only, which routed ~90% of matters down the
    AI path and starved the tacit-seam mechanism — redline_rework_rate read 0.)"""
    if complexity in (MatterComplexity.COMPLEX, MatterComplexity.HIGH_STAKES):
        return "tacit"       # partner-heavy staffing, tacit seams exercised
    return "codifiable"      # leverage-heavy staffing, AI does more of the work


# Seam identification — where are the handoffs between different roles?
def get_seams() -> list[dict]:
    seams = []
    for step in LITIGATION_WORKFLOW:
        for next_step_name in step.handoff_to:
            if next_step_name in WORKFLOW_STEP_MAP:
                next_step = WORKFLOW_STEP_MAP[next_step_name]
                if step.role_responsible != next_step.role_responsible:
                    seams.append({
                        "from_step": step.name,
                        "to_step": next_step_name,
                        "from_role": step.role_responsible,
                        "to_role": next_step.role_responsible,
                        "seam_risk": step.seam_risk,
                        "description": f"Handoff from {step.role_responsible} ({step.name}) to {next_step.role_responsible} ({next_step_name})",
                    })
    return seams


# Known informal control points (the "Diana situations" of law).
# These are NOT in the formal workflow but ARE how work actually gets done.
# Each is the tacit-knowledge seam that AI exposes and the codify_seams lever fixes.
INFORMAL_CONTROLS = [
    {
        "description": "The partner's redlines ARE the value — the associate's draft is 80% right, the partner's carve-outs and argument strategy are the 20% that constitutes judgment. AI automates the 80% and misses the 20%.",
        "trigger": "AI drafting produces a clean template draft; the partner still rewrites the argument-shape and client-risk framing",
        "effect": "redline_rework_rate stays high even as drafting time falls; the AI's output looks 'done' but isn't",
        "discoverable": True,
    },
    {
        "description": "The paralegal holds the clause library and the 'we always carve this out in Delaware' exceptions in her head — no template contains them.",
        "trigger": "AI drafting pulls the standard clause; the paralegal's jurisdiction-specific exception is absent",
        "effect": "filed documents miss the carve-out; rework at the filing/partner-review seam",
        "discoverable": True,
    },
    {
        "description": "The conflicts check is actually the senior partner's memory of past representations and lateral relationships — the database is incomplete.",
        "trigger": "AI conflicts screening runs only against the recorded database",
        "effect": "a missed conflict surfaces late as a disqualification or ethics fire-drill",
        "discoverable": True,
    },
    {
        "description": "Realization is negotiated, not computed — the billing partner knows which clients tolerate a write-off and which don't.",
        "trigger": "AI time capture produces hours at face value; the write-off decision is absent",
        "effect": "billed hours rise but realization rate falls; the collection cycle lengthens",
        "discoverable": True,
    },
    {
        "description": "Associates bill AI-saved hours as if they worked them (gaming utilization), OR don't bill AI time at all — the double-bind that makes the leverage model structurally hostile to AI.",
        "trigger": "AI does the research/drafting; the associate's utilization target is unchanged",
        "effect": "either utilization is gamed (invisible waste) or realization drops (visible loss)",
        "discoverable": True,
    },
]
