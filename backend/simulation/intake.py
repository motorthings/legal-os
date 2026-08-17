"""
Firm intake — the observable questions that populate the digital twin.

Each field is an ANSWERABLE question about the firm, tagged with the MECHANISM it
maps to in the engine and its GROUNDING. Deliberately not abstract scales
("how innovative are you 1–10") — observable proxies only, so the mapping is
defensible and the coefficients carry their source.

Usage (set the settings BEFORE running a sim):
    from intake import build_firm, FIELDS, load_firm
    sig = build_firm({"pricing_posture": "afa_native", "leverage_ratio": 4.0, ...})
    sig = load_firm("fixtures/my_firm.json")
"""
import json
from pathlib import Path

from .src.orchestrator import FirmSignature, CultureProfile

# (key, label, question, type, default, mechanism, tag)
#   type: "float" | "int" | "str" (enum values documented inline)
#   tag:  [SURVEY] = published benchmark, [INFERRED] = derived, [ASSUMPTION] = modeled
FIELDS = [
    # --- structural posture ---
    ("pricing_posture", "Pricing", "How do you bill? (hourly | partial_afa | afa_native)",
     "str", "hourly", "AI Profit Paradox: hourly makes AI a net loss, AFA a net win", "[SURVEY]"),
    ("leverage_ratio", "Leverage", "What is your associate-to-partner ratio?",
     "float", 3.5, "utilization + attrition: the pyramid AI attacks", "[SURVEY]"),
    ("origination_concentration", "Origination", "What fraction of origination does your top rainmaker control?",
     "float", 0.4, "comp lever effectiveness (a concentrated book resists comp change)", "[INFERRED]"),
    ("practice_mix_transactional", "Practice mix", "What fraction of revenue is transactional?",
     "float", 0.35, "AFA-nativeness: transactional work is already fixed-fee", "[SURVEY]"),
    ("client_concentration", "Client concentration", "What fraction of revenue is your top client?",
     "float", 0.3, "pass-vs-absorb pressure (a whale can force savings through)", "[INFERRED]"),
    ("partner_power_mix", "Partner power", "Can one partner block a firm-wide change? (0=no, 1=yes)",
     "float", 0.5, "rainmaker veto strength", "[ASSUMPTION]"),

    # --- Tier 1: work, comp, clients, people ---
    ("tacit_work_share", "Work composition", "What fraction of matters are complex/bet-the-company (vs routine)?",
     "float", 0.5, "matter complexity mix -> tacit-seam debt", "[INFERRED]"),
    ("comp_model", "Comp model", "Is comp lockstep, modified, or eat_what_you_kill?",
     "str", "modified", "adoption ceiling: lockstep forces collective action", "[INFERRED]"),
    ("client_afa_pressure", "AFA pressure", "Do your clients demand AFA? (0=no pressure, 1=they'll leave)",
     "float", 0.3, "realization: staying hourly leaks as clients demand AFA", "[SURVEY]"),
    ("partner_retirement_horizon", "Retirement horizon", "Average years until your partners retire?",
     "float", 10.0, "(stored — drives attrition/lateral next)", "[INFERRED]"),

    # --- Tier 2: financials + tech ---
    ("baseline_ppp", "PPP", "Your actual profit per partner ($)?",
     "int", 3_000_000, "P&L baseline", "[SURVEY]"),
    ("baseline_rpl", "RPL", "Your actual revenue per lawyer ($)?",
     "int", 1_200_000, "P&L baseline", "[SURVEY]"),
    ("baseline_realization", "Realization", "Your actual realization rate (%)?",
     "float", 85.0, "P&L baseline", "[SURVEY]"),
    ("baseline_margin", "Margin", "Your actual matter margin (%)?",
     "float", 30.0, "P&L baseline", "[INFERRED]"),
    ("tech_maturity", "Tech maturity", "How mature is your KM/precedent/data infrastructure? (0–1)",
     "float", 0.4, "gappy-seam count (codified work has fewer tacit seams)", "[INFERRED]"),

    # --- culture (observable proxies, not abstract scales) ---
    ("partner_ai_usage", "Partner AI usage", "What fraction of partners have personally used a legal AI tool?",
     "float", 0.69, "adoption floor (69% individual use)", "[SURVEY]"),
    ("attrition_intensity", "Attrition", "What is your associate attrition rate (as a fraction)?",
     "float", 0.19, "up-or-out intensity -> baseline churn", "[SURVEY]"),
    ("escalation_design", "Escalation design", "Is there a designed escalation path, or whoever-shouts-loudest? (0–1)",
     "float", 0.5, "(stored — needs a workflow mechanism to wire)", "[ASSUMPTION]"),
]


def build_firm(intake: dict) -> FirmSignature:
    """Map a flat intake dict of observable answers -> a FirmSignature."""
    d = {k: default for k, _, _, _, default, _, _ in FIELDS}
    d.update(intake)

    culture = CultureProfile(
        partner_ai_usage=d["partner_ai_usage"],
        attrition_intensity=d["attrition_intensity"],
        escalation_design=d["escalation_design"],
    )

    return FirmSignature(
        pricing_posture=d["pricing_posture"],
        leverage_ratio=d["leverage_ratio"],
        origination_concentration=d["origination_concentration"],
        practice_mix_transactional=d["practice_mix_transactional"],
        client_concentration=d["client_concentration"],
        partner_power_mix=d["partner_power_mix"],
        tacit_work_share=d["tacit_work_share"],
        comp_model=d["comp_model"],
        client_afa_pressure=d["client_afa_pressure"],
        partner_retirement_horizon=d["partner_retirement_horizon"],
        baseline_ppp=d["baseline_ppp"],
        baseline_rpl=d["baseline_rpl"],
        baseline_realization=d["baseline_realization"],
        baseline_margin=d["baseline_margin"],
        tech_maturity=d["tech_maturity"],
        culture=culture,
    )


def firm_to_intake(sig: FirmSignature) -> dict:
    """The reverse: dump a signature back to flat intake answers (for save)."""
    return {
        "pricing_posture": sig.pricing_posture,
        "leverage_ratio": sig.leverage_ratio,
        "origination_concentration": sig.origination_concentration,
        "practice_mix_transactional": sig.practice_mix_transactional,
        "client_concentration": sig.client_concentration,
        "partner_power_mix": sig.partner_power_mix,
        "tacit_work_share": sig.tacit_work_share,
        "comp_model": sig.comp_model,
        "client_afa_pressure": sig.client_afa_pressure,
        "partner_retirement_horizon": sig.partner_retirement_horizon,
        "baseline_ppp": sig.baseline_ppp,
        "baseline_rpl": sig.baseline_rpl,
        "baseline_realization": sig.baseline_realization,
        "baseline_margin": sig.baseline_margin,
        "tech_maturity": sig.tech_maturity,
        "partner_ai_usage": sig.culture.partner_ai_usage,
        "attrition_intensity": sig.culture.attrition_intensity,
        "escalation_design": sig.culture.escalation_design,
    }


def save_firm(sig: FirmSignature, path: str | Path):
    """Write a firm's intake to JSON (the hand-fillable template)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(firm_to_intake(sig), indent=2))


def load_firm(path: str | Path) -> FirmSignature:
    """Load a firm's intake JSON -> FirmSignature."""
    return build_firm(json.loads(Path(path).read_text()))


if __name__ == "__main__":
    # Emit the default template so a firm can hand-fill it.
    save_firm(FirmSignature(), "fixtures/example_firm.json")
    print("Wrote fixtures/example_firm.json (default archetype). Fill in a firm's numbers, then:")
    print("  sig = load_firm('fixtures/example_firm.json')")
    print("  cfg = SimulationConfig(firm_signature=sig)")
    print("\nFields (", len(FIELDS), "):")
    for key, label, q, _, default, _, tag in FIELDS:
        print(f"  {key:26s} {tag:10s} default={default}  # {q}")
