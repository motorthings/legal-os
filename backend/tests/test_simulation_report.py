"""Rendering tests for the simulation report.

The report's job is to be understood, so these tests assert on what a reader sees: that
each phase is labeled, that the numbers are attributed to the phase that produced them,
that internal identifiers never reach the prose, and that a report with nothing to say
about something says nothing rather than apologizing.

Fixtures are built on disk (meta.json + metrics.csv) exactly as the orchestrator exports
them, so `build_report` is exercised through its real entry point.

Run: cd backend && /opt/homebrew/bin/python3 -m pytest tests/test_simulation_report.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.report import build_report


# --- fixtures ---------------------------------------------------------------------

SPRINTS = 4
# Metric values per sprint. PPP declines, redline rework is high — the shape of a firm
# leaking value at the seams, which is what the baseline narrative is written against.
SERIES = {
    "ppp": [2_560_000, 2_450_000, 2_380_000, 2_310_000],
    "matter_profit_margin": [27.9, 27.1, 26.4, 25.9],
    "realization_rate": [77.9, 77.5, 77.2, 78.1],
    "redline_rework_rate": [80.0, 70.0, 85.0, 80.0],
    "exception_rate": [55.0, 52.9, 60.0, 54.3],
    "handoff_failure_rate": [9.4, 9.5, 8.8, 9.0],
    "associate_attrition": [21.5, 21.4, 22.6, 23.5],
    "partner_ai_trust": [3.8, 3.8, 3.9, 3.9],
    "associate_ai_trust": [6.2, 6.1, 6.0, 5.8],
    "ai_assisted_matter_pct": [0.0, 10.0, 10.0, 20.0],
    "wip_aging": [76.6, 76.6, 76.5, 76.5],
    "collection_cycle": [105.0, 104.4, 106.0, 104.8],
}


def _write_run(tmp_path: Path, *, stated_ppp: float = 3_000_000) -> Path:
    # exist_ok: a test taking both the baseline and searched fixtures shares one tmp_path.
    run_dir = tmp_path / "run_test"
    run_dir.mkdir(exist_ok=True)
    (run_dir / "meta.json").write_text(json.dumps({
        "run_id": "run_test", "seed": 42, "firm_name": "Testwell LLP",
        "sprints": SPRINTS, "matters_per_sprint": 10, "provider": "mock",
        "levers_pulled": {k: False for k in
                          ("pricing", "leverage", "comp", "seams", "latency")},
        "firm_signature": {
            "pricing_posture": "hourly", "leverage_ratio": 3.5,
            "origination_concentration": 0.4, "practice_mix_transactional": 0.35,
            "client_concentration": 0.3, "partner_power_mix": 0.5,
            "tacit_work_share": 0.5, "comp_model": "modified",
            "client_afa_pressure": 0.3, "partner_retirement_horizon": 10.0,
            "baseline_ppp": stated_ppp, "baseline_rpl": 1_200_000,
            "baseline_realization": 85.0, "baseline_margin": 30.0, "tech_maturity": 0.4,
            "culture": {"partner_ai_usage": 0.69, "attrition_intensity": 0.19,
                        "escalation_design": 0.5},
        },
    }))
    rows = ["metric_id,sprint,value"]
    for mid, vals in SERIES.items():
        for i, v in enumerate(vals, start=1):
            rows.append(f"{mid},{i},{v}")
    (run_dir / "metrics.csv").write_text("\n".join(rows) + "\n")
    return run_dir


SENSITIVITY = {"bands": {
    "pricing": {
        "coefficient": "margin_ai_afa_gain", "coefficient_name": "AFA margin conversion",
        "source": "[ASSUMPTION] how much of each AI-assisted point converts to margin",
        "calibration_question": "On flat-fee matters, when AI cuts the hours, how much do you keep?",
        "band_low": 90_000, "band_high": 240_000,
    },
    "seams": {
        "coefficient": "margin_redline_penalty", "coefficient_name": "Redline-rework margin cost",
        "source": "[ASSUMPTION] margin lost per percent-point of partner-rewrite rate",
        "calibration_question": "When a partner rewrites a draft, what does that cost the matter?",
        "band_low": 40_000, "band_high": 120_000,
    },
}}

RUN_BLOCK = {"baseline_scenarios": 20, "sensitivity_seeds": 3, "sensitivity_sims": 72}

OPTIMIZE = {
    "objective": "ppp", "objective_label": "PPP", "weights": {"ppp": 1.0}, "guardrails": [],
    "round_seeds": 8, "mc_seeds": 20, "sims_run": 196,
    "baseline_ppp": 2_400_000,
    "main_effects": {
        "pricing": {"delta_ppp": 180_000, "delta_margin": 3.1},
        "seams": {"delta_ppp": 120_000, "delta_margin": 2.2},
        "comp": {"delta_ppp": -40_000, "delta_margin": -0.8},
        "leverage": {"delta_ppp": 15_000, "delta_margin": 0.3},
        "latency": {"delta_ppp": 5_000, "delta_margin": 0.1},
    },
    "interactions": {
        "pricingxseams": {"both": 360_000, "additive": 300_000, "synergy": 60_000},
        "comp_x_pricing": {"delta": 45_000},
    },
    "best_combo": ["comp", "pricing", "seams"],
    "best_ppp": 2_780_000, "best_delta": 380_000, "spread": 60_000, "ci95": 28_000,
    "story": "Pull comp, pricing, seams.",
}


@pytest.fixture
def baseline_report(tmp_path):
    """A run with no lever search — Phase 1 and Phase 3 only."""
    return build_report(_write_run(tmp_path),
                        {"run": RUN_BLOCK, "sensitivity": SENSITIVITY})


@pytest.fixture
def searched_report(tmp_path):
    """A run whose lever search completed — all three phases."""
    return build_report(_write_run(tmp_path),
                        {"run": RUN_BLOCK, "optimize": OPTIMIZE, "sensitivity": SENSITIVITY})


# --- what the reader must be able to find -----------------------------------------

def test_opens_by_explaining_the_model(baseline_report):
    """Before any number, the report says what was simulated and at what scale."""
    assert "## What this is" in baseline_report
    assert "4 quarters" in baseline_report                 # scale, in quarters not sprints
    assert "10 matters per quarter" in baseline_report
    assert "20 independent scenarios" in baseline_report
    assert "not a forecast" in baseline_report.lower()
    # A mock run must say so — a reader who thinks real AI made these calls is misled.
    assert "stand-in" in baseline_report


def test_every_input_says_what_it_drives(baseline_report):
    """An input the reader can't connect to an outcome is a question answered for nothing."""
    section = baseline_report.split("## 1.")[1].split("## 2.")[0]
    # One "Drives:" clause per input bullet, not a token few.
    assert section.count("*Drives:*") >= 7
    assert "the sign on every hour AI saves" in section     # pricing_posture
    assert "who can veto the change" in section             # origination_concentration


def test_reconciles_stated_and_simulated_baseline(searched_report):
    """The stated PPP and the model's starting PPP differ for a real reason. Unexplained,
    the pair reads as an arithmetic error."""
    assert "One number to reconcile" in searched_report
    assert "$3,000,000" in searched_report                  # what the firm reported
    assert "$2,560,000" in searched_report                  # where the model starts
    assert "$440,000" in searched_report                    # the gap, stated explicitly
    assert "rewriting 80.0% of drafts" in searched_report   # and attributed to a cause


def test_reconciliation_suppressed_when_baselines_agree(tmp_path):
    """No gap, no paragraph. Explaining a difference that isn't there invents a problem."""
    run_dir = _write_run(tmp_path, stated_ppp=2_560_000)
    report = build_report(run_dir, {"run": RUN_BLOCK})
    assert "One number to reconcile" not in report


def test_phases_are_named_and_counted(searched_report):
    """The reader can size the evidence behind the recommendation."""
    section = searched_report.split("## 2.")[1].split("## 3.")[0]
    assert "Phase 1 — the baseline" in section
    assert "Phase 2 — the lever search" in section
    assert "Phase 3" in section
    assert "196 simulations" in section                     # the search's real size
    assert "8 scenarios each" in section                    # round seeds
    assert "20 fresh scenarios" in section                  # the confirming Monte Carlo


def test_trajectories_are_attributed_to_phase_one(searched_report):
    """The single most confusing thing in the old report: charts from the baseline run
    sitting under a recommendation from a different set of simulations."""
    assert "none of Phase 2 appears in the trajectory charts" in searched_report
    trajectories = searched_report.split("Quarter-by-quarter trajectories")[1]
    assert "baseline only" in trajectories


def test_baseline_run_omits_the_recommendation(baseline_report):
    """No search, no verdict. Inventing one is worse than not having it."""
    assert "## 4. What the lever search added" not in baseline_report
    assert "Lever-by-lever results" not in baseline_report
    assert "**Not run.**" in baseline_report
    assert "The next step is to run the lever search" in baseline_report


def test_searched_run_reports_the_interaction_findings(searched_report):
    """The findings a one-lever-at-a-time comparison structurally cannot produce — this is
    what the search is for."""
    section = searched_report.split("## 4.")[1].split("## 5.")[0]
    assert "changes sign depending on how you bill" in section
    assert "-$40,000" in section and "+$45,000" in section   # both sides of the flip
    assert "compound each other" in section
    assert "+$60,000" in section                             # the synergy, quantified


def test_recommendation_states_order_and_confidence(searched_report):
    section = searched_report.split("## 5.")[1]
    assert "Pull comp, pricing, seams" in section
    assert "+$380,000" in section
    assert "$28,000" in section                              # the CI half-width
    assert "The order is part of the recommendation" in section
    assert "does not include" in section                     # implementation cost caveat


def test_surfaces_the_calibration_question_that_would_sharpen_it(searched_report):
    """'Calibrate the model' is not actionable. One answerable question is."""
    assert "AFA margin conversion" in searched_report
    assert "On flat-fee matters, when AI cuts the hours, how much do you keep?" in searched_report


# --- claims the report must not overstate -------------------------------------------
#
# Each of these was a real bug, found by running the report against live optimizer output
# rather than a hand-written fixture. A noisy few-seed search produces exact zeros, trivial
# interactions, and bands wider than the effect — and the prose asserted findings anyway.

def _searched(tmp_path, **optimize_overrides) -> str:
    opt = {**OPTIMIZE, **optimize_overrides}
    return build_report(_write_run(tmp_path),
                        {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY})


def test_a_zero_effect_is_not_reported_as_a_sign(tmp_path):
    """'+$0' reads as a gain that rounded away. The lever did nothing; say that."""
    report = _searched(tmp_path, interactions={
        "pricingxseams": {"both": 360_000, "additive": 300_000, "synergy": 60_000},
        "comp_x_pricing": {"delta": 0.0},
    })
    assert "+$0" not in report
    assert "no measurable difference" in report
    assert "It stays negative" not in report      # zero is not negative


def test_a_trivial_interaction_is_not_called_an_interaction(tmp_path):
    """A 2% gap across a handful of scenarios is a rounding artifact. Calling it 'more than
    the sum of its parts' is the overclaim this report exists to avoid."""
    report = _searched(tmp_path, interactions={
        "pricingxseams": {"both": 576_000, "additive": 565_000, "synergy": 11_000},
        "comp_x_pricing": {"delta": 45_000},
    })
    assert "too small to read as interaction" in report
    assert "compound each other" not in report
    assert "you get less than half" not in report


def test_a_band_wider_than_the_effect_is_flagged_not_asserted(tmp_path):
    """Whether the confidence band clears zero is a fact to check, not a line to print."""
    wide = _searched(tmp_path, best_delta=100_000, ci95=170_000)
    assert "wide enough to touch zero" in wide
    assert "rather than a lucky draw" not in wide

    narrow = _searched(tmp_path, best_delta=568_000, ci95=28_000)
    assert "doesn't reach zero" in narrow
    assert "wide enough to touch zero" not in narrow


def test_sequencing_steps_are_numbered_contiguously(tmp_path):
    """Which steps apply depends on which levers won. A list reading 1, 2, 4 looks broken."""
    report = _searched(tmp_path, best_combo=["latency", "pricing", "seams"])
    section = report.split("The order is part of the recommendation")[1]
    steps = [int(ln.split(".")[0]) for ln in section.splitlines()
             if ln[:1].isdigit() and ". " in ln[:4]]
    assert steps == list(range(1, len(steps) + 1))
    assert len(steps) >= 3


# --- what must never reach the reader ----------------------------------------------

@pytest.mark.parametrize("ident", ["pricingxseams", "comp_x_pricing", "margin_ai_afa_gain",
                                   "margin_redline_penalty", "delta_ppp", "best_combo"])
def test_internal_identifiers_stay_out_of_the_prose(searched_report, ident):
    """Appendix D is the raw config record and is allowed to show field names; nothing
    before it should."""
    prose = searched_report.split("— The exact configuration")[0]
    assert ident not in prose


def test_no_apology_for_missing_data(tmp_path):
    """A section with nothing to say says nothing. The old graceful-miss string shipped to
    the reader as a bare confusing sentence."""
    run_dir = tmp_path / "run_empty"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(json.dumps({"firm_name": "Empty LLP", "sprints": 4,
                                                   "matters_per_sprint": 10}))
    report = build_report(run_dir, {"optimize": OPTIMIZE})
    assert "Insufficient data" not in report
    assert "_No metric history was recorded" in report      # the honest version instead


# --- structure ---------------------------------------------------------------------

def _headings(report: str) -> list[str]:
    return [ln for ln in report.splitlines() if ln.startswith("## ")]


def test_section_numbering_has_no_gaps(baseline_report, searched_report):
    """A baseline run has no section 4 to show, so 'what to do' becomes 4, not 5."""
    assert "## 4. What to do, and what it's worth" in baseline_report
    assert "## 5. What to do, and what it's worth" in searched_report
    for report in (baseline_report, searched_report):
        numbers = [int(h.split(".")[0][3:]) for h in _headings(report)
                   if h[3:4].isdigit()]
        assert numbers == list(range(1, len(numbers) + 1))


def test_appendix_lettering_has_no_gaps(baseline_report, searched_report):
    """The lever appendix only exists on a searched run; the letters must close up."""
    for report in (baseline_report, searched_report):
        letters = [h.split("Appendix ")[1][0] for h in _headings(report)
                   if "Appendix " in h]
        assert letters == list("ABCDEFGH"[:len(letters)])


def test_no_variable_names_or_math_notation_reach_the_reader(searched_report):
    """A managing partner reads this, not an engineer. No database field names, no Greek,
    no evidence tags — the machinery stays behind plain language."""
    forbidden = [
        "pricing_posture", "leverage_ratio", "origination_concentration",
        "practice_mix_transactional", "partner_power_mix", "tech_maturity",
        "partner_ai_usage", "attrition_intensity", "baseline_ppp",
        "Δ PPP", "Δ margin", "coefficient", "[SURVEY]", "[INFERRED]", "[ASSUMPTION]",
        "| field | value |", "1σ", "95% CI",
    ]
    for token in forbidden:
        assert token not in searched_report, f"leaked to the reader: {token!r}"


def test_firm_appendix_reads_in_plain_language(searched_report):
    """Appendix D is the firm on the record — human labels and plain values, not raw dials."""
    section = searched_report.split("Your firm, on the record")[1]
    assert "How you bill:" in section
    assert "billing by the hour" in section          # humanized, not "hourly"
    assert "Associates per partner:" in section


def test_headings_are_separated_from_their_prose(searched_report):
    """Markdown needs the blank line. An earlier assembly bug stripped them and glued
    headings onto the paragraph below, which broke list and table rendering."""
    lines = searched_report.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("#"):
            assert lines[i + 1].strip() == "", f"no blank line after heading: {line!r}"
