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
#       error rates). This is what CREATES a fault line. (capability lane, below.)
#   L2  The ruling reacts      — a court/bar/statute moves on that behavior. (the
#       ruling-pressure meter, shipped.)
#   L3  The market adopts       — the control becomes table stakes, court or no court.
#       (the control-adoption meter, below. This is where Harbor lives.)
# Getting L1 right is necessary but not sufficient: an L2 call is only meaningful if
# the capability it reacts to actually arrived, and an L3 call is only meaningful if
# the L2 it rests on held. Calibration reports hit-rate per order plus the two
# conditionals: P(L2 called | L1 called) and P(L3 called | L2 called).
ORDERS = {
    1: {"name": "Capability", "q": "Can AI now do the thing that creates the fault line?"},
    2: {"name": "Ruling",     "q": "Will a court, bar, or statute move on it?"},
    3: {"name": "Adoption",   "q": "Is the control becoming table stakes?"},
}

# --- First-order layer: capability pressure ---------------------------------
# L1 evidence is a DIFFERENT object than a ruling or a market signal: it is a claim
# that AI can now DO the thing that stresses a duty. It is weighted by how HARD the
# demonstration is — a reproducible benchmark with published error rates outranks a
# vendor's "our agent can do discovery now" a hundredfold. The whole lane is held
# deliberately LOW (see CAP_DIVISOR in score.py) and clearly labeled "capability
# forming," so a capability that has arrived never reads as a ruling that has landed.
# Speculation (`hype`) is narrative signal only. Items carrying a `capability` class
# are the L1 evidence; everything else is second/third-order only.
#
# Capability, once demonstrated, does not un-happen — so L1 evidence does NOT decay
# (a proven capability persists, unlike ruling momentum). Kept in its own labeled
# lane so inference never masquerades as a ruling (same discipline as the L3 lane).
CAPABILITY_WEIGHTS = {
    "benchmark":  1.00,   # a reproducible benchmark / measured error-rate study
    "study":      0.80,   # peer-reviewed capability research (no public leaderboard)
    "deployment": 0.50,   # capability demonstrated at production scale (usage data)
    "model_access": 0.45, # a frontier-model unlock (context, agentic SDK, tool-use) that
                          # legal tooling builds on — the substrate, not a legal demonstration
    "release":    0.35,   # a model/agent release claiming the capability
    "demo":       0.12,   # demo / anecdote — a capability shown once, not measured
    "hype":       0.02,   # speculation. narrative signal only.
}

# Capability seed (0-10): how far the capability that CREATES this fault line has
# already been demonstrated, before this run's evidence. Deliberately mostly below
# the call threshold so the meter is EVIDENCE-driven, not seed-driven — a capability
# call has to be earned by a demonstration on record. Fault lines whose driver is a
# downstream market/regulatory reaction (insurance, convergence, fees, vendor
# liability, competence) have no direct capability of their own → default low.
CAPABILITY_SEEDS = {
    "benchmark": 6.5, "disclosure": 5.5, "verification": 5.5,
    "confidentiality": 4.5, "agentic": 4.0, "judicial_analytics": 4.0,
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

# --- Advisory annotations (Part B lens; do not move the forecast meters) ------
# These two per-line facts let the advisory seam give DIFFERENT, correct advice per
# control instead of stamping one uniform answer. They describe how a firm should act,
# not what the law will do, so they sit beside the forecast but never enter its meters.
#
# `seam`   — how capturable the underlying work is by current AI. Only meaningful where AI
#            does the work (capability-/deployment-driven lines).
#            codifiable = AI can do it well now · mixed = partially · tacit = partner-judgment
#            residue, not yet capturable.
# `driver` — why the control exists for a firm:
#            capability   the fault is the AI tool doing something (benchmark, agentic, analytics)
#            deployment   the control exists because the firm USES AI (disclosure, verification,
#                         confidentiality, competence)
#            market       the control exists from market/regulatory pressure, AI use or not
#                         (insurance, convergence, fees, vendor_liability)
FAULT_ANNOTATIONS = {
    "insurance":          {"seam": "codifiable", "driver": "market"},
    "disclosure":         {"seam": "codifiable", "driver": "deployment"},
    "verification":       {"seam": "codifiable", "driver": "deployment"},
    "confidentiality":    {"seam": "codifiable", "driver": "deployment"},
    "convergence":        {"seam": "codifiable", "driver": "market"},
    "agentic":            {"seam": "mixed",      "driver": "capability"},
    "benchmark":          {"seam": "codifiable", "driver": "capability"},
    "competence":         {"seam": "codifiable", "driver": "deployment"},
    "fees":               {"seam": "tacit",      "driver": "market"},
    "judicial_analytics": {"seam": "tacit",      "driver": "capability"},
    "vendor_liability":   {"seam": "codifiable", "driver": "market"},
}

# Adoption seed (0-10): how far the market has already moved toward the control being
# table stakes, before this run's evidence. The evidence then moves it, same as pressure.
ADOPTION_SEEDS = {
    "insurance": 7.5, "disclosure": 7.0, "verification": 6.5, "convergence": 7.0,
    "confidentiality": 6.0, "benchmark": 5.5, "competence": 5.5, "agentic": 5.0,
    "fees": 3.0, "judicial_analytics": 3.0, "vendor_liability": 2.5,
}

# --- Enablement lane (E, market) — Part B (see docs/radar-design.md §9) ------
# A fourth reading per fault line: not "is the control required" (L3 adoption,
# demand) but "can a firm actually stand it up with what the market offers right
# now" (supply: a usable tool, a certification to aim at, a provider, a playbook).
# L3 and E are the demand and supply halves of the same question; L3 conflates
# them today, which is why a control can be mandatory yet undeployable (agent
# supervision rules before mature agent tooling). E is evidence-traced (T-market),
# never a backtested call, never in Part A's calibration.
ENABLE_WEIGHTS = {
    "deploy_scale": 1.00,   # operational at production scale at major firms
    "standard":     0.90,   # a concrete certification / benchmark / minimum standard to build against
    "playbook":     0.75,   # a defined process / playbook / insurer form to follow (not just a duty)
    "provider":     0.65,   # a maturing vendor/provider category to buy from
    "client_pull":  0.55,   # clients / RFPs actively requiring the tool or control
    "launch":       0.30,   # a tool / offer launched but not yet proven at scale
    "pundit":       0.02,   # narrative only
}

# Enablement seed (0-10): baseline ecosystem readiness before this run's evidence.
ENABLE_SEEDS = {
    "benchmark": 7.0, "verification": 6.5, "disclosure": 6.0, "competence": 6.0,
    "confidentiality": 5.5, "insurance": 5.0, "convergence": 4.0, "fees": 3.5,
    "agentic": 3.5, "judicial_analytics": 3.0, "vendor_liability": 3.0,
}

# --- Software-capability lane (S, vendor trajectory) — Part B §10 -------------
# The middle layer of a three-layer enablement stack:
#   L1  AI capability   — can the underlying AI do the legal thing (existing `capability`)
#   S   Software cap.   — can legal-AI software companies build/ship a tool that
#                         operationalizes it (THIS lane — the vendors)
#   E   Method          — does the playbook/standard exist to adopt it (existing `enable`)
# Each layer enables the next: model -> software -> method -> firm.
#
# S is a FORWARD momentum signal, not a stock: it tracks what vendors are enabled
# to build next (capital, M&A, model access, regulatory room), which drives the build
# trajectory ahead of the actual shipments. Because it is momentum, S DECAYS (unlike
# E, which is a persistent supply fact and does not decay). It is Part B, T-market,
# never a backtested *ruling* call — but it IS backtested against its own build
# milestones (see calibration.py software_backtest), because a forward signal that
# cannot be graded is just a vibe.
SOFTWARE_WEIGHTS = {
    "capital":        1.00,  # a funding round / valuation step that funds future build
    "acquisition":    0.85,  # M&A consolidating build capacity / incumbency
    "regulatory_room": 0.70, # a law/ruling opening or constraining what vendors may ship
    "ship":           0.55,  # a vendor shipping a major product — proof the capability is real
}

# Momentum flag: what a software-capability event tells us about the *future* trajectory.
# A momentum signal can only predict CONTINUATION (the same trajectory staying hot). A
# direction shift re-anchors the trajectory — real, but not visible from prior capital.
# An origination is first-of-kind — the lane's known blind spot. Flagging keeps the S
# meter honest: it predicts what it can, and stops pretending otherwise.
FLAG_MULTIPLIER = {"continuation": 1.0, "direction_shift": 0.4, "origination": 0.0}

# Software-capability seed (0-10): where the vendor build already is, before this
# run's evidence. Deliberately moderate so momentum evidence has to lift the meter.
SOFTWARE_SEEDS = {
    "benchmark": 5.0, "verification": 5.5, "disclosure": 5.5, "confidentiality": 5.5,
    "competence": 5.0, "convergence": 5.0, "agentic": 5.0, "insurance": 4.0,
    "fees": 3.0, "judicial_analytics": 3.0, "vendor_liability": 3.5,
}

# Build momentum is short-lived: a round two years ago doesn't signal today's build.
SOFTWARE_HALF_LIFE = 120   # days; software evidence decays (momentum), unlike E (stock)

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
        "vector": "Malpractice insurers are adding AI-governance questions to policy "
                  "renewals and pricing coverage on the answers. They move faster than "
                  "bar regulators, so insurance, not the rules, becomes the real "
                  "gatekeeper for whether a firm can use AI at all.",
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
        "vector": "Courts first punished fake AI citations after the fact (Mata v. "
                  "Avianca was the first such sanction). Now more than 300 judges require "
                  "lawyers to disclose AI use up front, and that patchwork of local orders "
                  "is converging toward a single certification standard.",
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
        "vector": "Signing a line that says 'a human reviewed it' is no longer enough. "
                  "Courts and bars increasingly expect a documented verification process: "
                  "a record of what was checked, how, and by whom.",
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
        "vector": "AI is shifting from drafting text to taking actions on its own across "
                  "multiple steps (so-called agents). 'Just review the final output' breaks "
                  "down when no single person saw every step, reopening old duties around "
                  "supervision and the unauthorized practice of law.",
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
        "vector": "AI tools that learn from what you feed them, or mix data across "
                  "matters, put client confidentiality at risk. Firms are being pushed to "
                  "map where client data goes and get written no-training guarantees from "
                  "vendors before a tool is approved.",
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
        "vector": "Independent studies now publish how often each legal AI tool gets "
                  "things wrong. Once error rates are public, choosing a tool becomes a "
                  "measurable competence decision rather than a matter of trust.",
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
        "vector": "The duty is shifting from 'understand the tool you use' to 'run a "
                  "governance program' — training, written policies, and oversight — with "
                  "mandatory AI continuing-education requirements spreading state by state.",
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
        "vector": "AI collapses the hours a task used to take, which strains the "
                  "billable-hour model and raises the question of what counts as a "
                  "'reasonable fee' when the work now takes minutes.",
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
        "vector": "Today the lawyer carries all the risk when an AI tool fails; there is "
                  "no clear legal path to hold the vendor responsible. Pressure is building, "
                  "through disclosure mandates and product-liability proposals, to shift some "
                  "of that liability onto the toolmakers.",
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
        "vector": "Tools that predict how a specific, named judge will rule cross the line "
                  "from analytics into profiling. France has already criminalized it, and US "
                  "regulation is likely to move in the same direction.",
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
        "vector": "The rules are a patchwork — the EU AI Act, Colorado, Texas, 35-plus "
                  "state bars, 300-plus judges — each slightly different. The patchwork "
                  "itself is the pressure: a firm working across jurisdictions needs one "
                  "operating model built to the strictest standard.",
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
