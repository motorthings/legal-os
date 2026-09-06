"""Fault-Line Radar — taxonomy and source-authority model.

The radar tracks *fault lines*: the places where an AI capability stresses an
existing legal duty. Rulings land on fault lines. We forecast the fault line,
not the ruling.

Governance note (see repo CLAUDE.md pillars):
- Deterministic: scores are pure functions of the evidence set + these weights.
- Explainable: every score cites the specific evidence and weight that moved it.
- Evidence over eloquence: authority is weighted by tier, not by volume.
"""

# --- Source authority tiers -------------------------------------------------
# Not all legal writing earns the same sway. Weight by authority, not loudness.
SOURCE_TIERS = {
    "T1": {"label": "Binding / primary", "weight": 1.00,
           "desc": "Court rulings, sanctions orders, statutes, regulations, rule amendments."},
    "T2": {"label": "Regulatory guidance", "weight": 0.80,
           "desc": "ABA / state bar ethics opinions, judicial standing orders."},
    "T3": {"label": "Empirical / institutional", "weight": 0.60,
           "desc": "Peer-reviewed research, trackers, insurer/market actions with data."},
    "T4": {"label": "Professional commentary", "weight": 0.35,
           "desc": "Firm client alerts, bar magazines, established legal press."},
    "T5": {"label": "Vendor / marketing / opinion", "weight": 0.008,
           "desc": "Vendor blogs, SEO content, hot takes. ~1/100 of an ABA opinion. Narrative signal only."},
}

# Scoring knobs (all explicit so score replay is deterministic).
CONFLICT_DISCOUNT = 0.4     # multiply weight if source sells what it comments on
EMPIRICAL_BOOST = 1.25      # multiply weight if item carries hard data
CORROBORATION_STEP = 0.15   # added per distinct higher-or-equal tier corroborating
HALF_LIFE_DAYS = 180        # momentum decay half-life (standing T1/T2 evidence exempt)
STANDING_TIERS = {"T1", "T2"}   # never decays out of the evidence base
# NOTE: source-reliability (a source earning weight above its tier floor by a proven
# track record) is a BACKLOG item, not v1. v1 weights are tier-flat.

# --- Three orders of prediction ---------------------------------------------
# The engine forecasts a CASCADE. Each order depends on the one before it, so we
# track calibration at each level separately AND conditionally:
#   L1  Capability / behavior  — AI can now do X in legal work (agentic autonomy,
#       error rates). This is what CREATES a fault line. (capability lane, backlog #3)
#   L2  The ruling reacts      — a court/bar/statute moves on that behavior. (the
#       ruling-pressure meter, shipped.)
#   L3  The market adopts       — the control becomes table stakes, court or no court.
#       (the control-adoption meter, below. This is where Harbor lives.)
# Getting L1 right is necessary but not sufficient: an L3 call is only meaningful if
# the L2 it rests on held. Calibration reports hit-rate per order and L3-given-L2.
ORDERS = {
    1: {"name": "Capability", "q": "Can AI now do the thing that creates the fault line?"},
    2: {"name": "Ruling",     "q": "Will a court, bar, or statute move on it?"},
    3: {"name": "Adoption",   "q": "Is the control becoming table stakes?"},
}

# --- Third-order layer: control-adoption pressure ---------------------------
# Third-order evidence is a DIFFERENT object than a ruling, so it is weighted by how
# binding it is ON THE MARKET, not on a court. An insurer changing a renewal form
# gates money and moves everyone; a pundit's "future of the firm" essay moves nobody.
# Feed items carrying a `market` class are the adoption evidence; everything else is
# second-order only. Kept in a separate, clearly-labeled lane so inference never
# masquerades as a ruling (same discipline as the capability lane, backlog #3).
MARKET_WEIGHTS = {
    "insurer": 1.00,          # carriers price the risk — the real market regulator
    "procurement": 0.85,      # client/RFP attestation requirements
    "deployment": 0.70,       # Big Law / MSP adoption data (a control going live at scale)
    "cert": 0.60,             # certification / benchmark standards emerging
    "process_mandate": 0.55,  # a rule or opinion mandating a *process* control, not just a duty
    "commentary": 0.20,       # trade press noting the trend
    "pundit": 0.02,           # speculation. narrative signal only.
}

# The control each fault line maps to: the operating-model move that neutralizes it.
# (Short label; the long form lives in each fault line's `build_now`.)
CONTROLS = {
    "insurance":          "Governance as an insurable artifact",
    "disclosure":         "Verification-by-default with an audit trail",
    "verification":       "Documented verification + trace logs",
    "agentic":            "Human-decides gates + scope-limiting",
    "confidentiality":    "Data-flow mapping + vendor attestation",
    "benchmark":          "Tool-certification benchmark (NERVE)",
    "competence":         "Firm-wide training + governance program",
    "fees":               "Value-delivered measurement",
    "vendor_liability":   "Tool-provenance documentation",
    "judicial_analytics": "Guardrailed strategy sim (no actor prediction)",
    "convergence":        "One operating model, to the strictest standard",
}

# Adoption seed (0-10): how far the market has already moved toward the control being
# table stakes, before this run's evidence. The evidence then moves it, same as pressure.
ADOPTION_SEEDS = {
    "insurance": 7.5, "disclosure": 7.0, "verification": 6.5, "convergence": 7.0,
    "confidentiality": 6.0, "benchmark": 5.5, "competence": 5.5, "agentic": 5.0,
    "fees": 3.0, "judicial_analytics": 3.0, "vendor_liability": 2.5,
}

# Lead time to stand a control up, derived from the fault line's horizon.
# "now" = you needed this yesterday; the intersection with high pressure is the alarm.
LEAD_BY_HORIZON = {
    "near (0-12mo)": "now", "near": "now", "near-mid": "~2 quarters",
    "mid (1-3yr)": "~1 year", "mid": "~1 year", "mid-far": "~1-2 years",
    "far (3yr+)": "later",
}

# --- The fault lines --------------------------------------------------------
# `signals` are lowercase substrings used to match incoming items deterministically.
# `pressure_seed` (0-10) and `horizon`/`layer` come from the analyst thesis and are
# the baseline the evidence then moves.
FAULT_LINES = [
    {
        "id": "insurance",
        "title": "Insurance becomes the real regulator",
        "model_rules": ["1.1", "5.1", "5.3"],
        "pressure_seed": 8.5,
        "horizon": "near (0-12mo)",
        "layer": "3b — operating model",
        "vector": "Carriers price AI risk faster than bars write rules.",
        "tech_driver": "Uninsurable == unusable. Governance becomes a coverage condition.",
        "build_now": "The governance program as an insurable artifact: model inventory, "
                     "approval process, oversight documentation, measurement.",
        "signals": ["insurance", "insurer", "malpractice carrier", "underwrit", "premium",
                    "coverage", "cna", "axa", "endorsement", "uninsurable"],
    },
    {
        "id": "disclosure",
        "title": "Disclosure & certification standardize",
        "model_rules": ["3.3", "Rule 11"],
        "pressure_seed": 8.0,
        "horizon": "near (0-12mo)",
        "layer": "3a — reactive",
        "vector": "Mata was reactive; 300+ judges now require prospective disclosure.",
        "tech_driver": "Patchwork of standing orders collapses into a uniform certification.",
        "build_now": "Verification-by-default with an auditable trail, so certification is a byproduct.",
        "signals": ["disclosure", "standing order", "certif", "rule 11", "frcp", "disclose ai",
                    "attestation"],
    },
    {
        "id": "verification",
        "title": "'A human reviewed it' stops being enough",
        "model_rules": ["5.1", "5.3"],
        "pressure_seed": 7.5,
        "horizon": "near-mid",
        "layer": "3b — operating model",
        "vector": "Attestation gives way to a documented verification process.",
        "tech_driver": "Multi-step agentic work no single human fully traces.",
        "build_now": "Logging, trace analysis, evaluation records as the compliance artifact.",
        "signals": ["verification", "human review", "human-in-the-loop", "audit trail",
                    "trace", "reasonable inquiry", "verify citation"],
    },
    {
        "id": "agentic",
        "title": "Agentic autonomy reopens supervision & UPL",
        "model_rules": ["5.1", "5.3", "5.5"],
        "pressure_seed": 6.5,
        "horizon": "mid (1-3yr)",
        "layer": "3b — operating model",
        "vector": "Agents that act, not just draft, break 'review the output'.",
        "tech_driver": "Autonomous multi-step agents; AI AGENT Act; UPL-by-proxy scholarship.",
        "build_now": "Human-decides gates and scope-limiting by design.",
        "signals": ["agentic", "autonomous agent", "ai agent act", "unauthorized practice",
                    "upl", "scope-limited", "revocable", "multi-agent"],
    },
    {
        "id": "confidentiality",
        "title": "Confidentiality hardens into data governance",
        "model_rules": ["1.6", "1.7", "1.9"],
        "pressure_seed": 7.0,
        "horizon": "near (0-12mo)",
        "layer": "3b — operating model",
        "vector": "Self-learning tools and cross-matter contamination stress 1.6.",
        "tech_driver": "No-training clauses become an ethical default; vendor attestations required.",
        "build_now": "Data-flow mapping and vendor attestation at tool onboarding.",
        "signals": ["confidential", "data governance", "no-training", "training data",
                    "ethical wall", "cross-matter", "client data", "privacy"],
    },
    {
        "id": "benchmark",
        "title": "A tool-certification / benchmark standard emerges",
        "model_rules": ["1.1"],
        "pressure_seed": 6.0,
        "horizon": "mid (1-3yr)",
        "layer": "3b — operating model",
        "vector": "Public error rates make tool choice a competence exercise.",
        "tech_driver": "'Lex-TruthfulQA'-style minimum-competence benchmarks proposed.",
        "build_now": "You already built one: NERVE. A benchmark is a compliance instrument.",
        "signals": ["benchmark", "error rate", "hallucination rate", "stanford", "certif",
                    "minimum competence", "lex-truthful", "nerve", "evaluation standard"],
    },
    {
        "id": "competence",
        "title": "Competence becomes an affirmative governance duty",
        "model_rules": ["1.1"],
        "pressure_seed": 6.0,
        "horizon": "mid (1-3yr)",
        "layer": "3a — reactive",
        "vector": "Duty shifts from 'understand the tool' to 'have a program'.",
        "tech_driver": "Mandatory AI CLE spreading; firm-level governance capability expected.",
        "build_now": "Training and enablement at scale (iTrain bet; AI Build Lab proof).",
        "signals": ["competence", "cle", "training", "continuing legal education", "duty of technology",
                    "technological competence", "governance program"],
    },
    {
        "id": "fees",
        "title": "The billable hour cracks under AI",
        "model_rules": ["1.5"],
        "pressure_seed": 4.5,
        "horizon": "mid-far",
        "layer": "second-order (business model)",
        "vector": "AI collapses billable time; fee reasonableness under strain.",
        "tech_driver": "Fee-transparency rules; shift toward value-based billing.",
        "build_now": "Measure value delivered, not hours saved.",
        "signals": ["billable hour", "reasonable fee", "fee transparency", "value-based billing",
                    "alternative fee", "billing"],
    },
    {
        "id": "vendor_liability",
        "title": "Liability shifts partway to vendors",
        "model_rules": ["—"],
        "pressure_seed": 3.5,
        "horizon": "far (3yr+)",
        "layer": "first-order (who bears risk)",
        "vector": "Lawyer bears all risk today; tort law has no home for agent harm.",
        "tech_driver": "Pressure toward disclosure mandates and certification standards on vendors.",
        "build_now": "Track for a shift; document tool provenance now.",
        "signals": ["vendor liability", "product liability", "tort", "shift liability",
                    "vendor accountability", "who is liable"],
    },
    {
        "id": "judicial_analytics",
        "title": "Judicial / litigation analytics gets regulated",
        "model_rules": ["3.5", "8.4", "—"],
        "pressure_seed": 5.0,
        "horizon": "mid (1-3yr)",
        "layer": "first-order (new duty)",
        "vector": "Predicting a named judge's rulings shifts from analytics to profiling.",
        "tech_driver": "Judge/jury/opposing-counsel persona simulation and Monte Carlo "
                       "strategy engines make specific-actor prediction cheap.",
        "build_now": "Strategy stress-testing with human-reviewed, explicitly-uncertain "
                     "priors; never sell 'predict the judge'. Persona models are "
                     "low-confidence parameters, never determinative. (France already "
                     "criminalized judicial profiling; US direction is toward rules.)",
        "signals": ["judicial analytics", "judge analytics", "judicial profiling",
                    "litigation analytics", "predict the judge", "jury simulation",
                    "outcome prediction", "monte carlo", "article 33"],
    },
    {
        "id": "convergence",
        "title": "Regulatory convergence forces one operating model",
        "model_rules": ["1.1", "1.6"],
        "pressure_seed": 7.5,
        "horizon": "near (0-12mo)",
        "layer": "3b — operating model",
        "vector": "Patchwork itself is the pressure: EU + Colorado + 35 bars + 300 judges.",
        "tech_driver": "Firms adopt one framework calibrated to the strictest standard.",
        "build_now": "The unifying operating model. This is the whole thesis.",
        "signals": ["eu ai act", "colorado ai act", "patchwork", "conformity assessment",
                    "risk management system", "convergence", "state bar", "multi-jurisdiction"],
    },
]


def fault_line_by_id(fid):
    for fl in FAULT_LINES:
        if fl["id"] == fid:
            return fl
    return None
