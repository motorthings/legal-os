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
    """The optimization stage — adds the recommendation, not yet the scenario confirmation."""
    return build_report(_write_run(tmp_path),
                        {"run": RUN_BLOCK, "optimize": OPTIMIZE, "sensitivity": SENSITIVITY,
                         "stage": "lever_optimization"})


@pytest.fixture
def scenario_report(tmp_path):
    """The final stage — the full story, including what the simulation showed."""
    return build_report(_write_run(tmp_path),
                        {"run": RUN_BLOCK, "optimize": OPTIMIZE, "sensitivity": SENSITIVITY,
                         "stage": "scenario_simulation", "prior": {"best_delta": 380_000}})



# --- the report is one story a partner can read top to bottom -----------------------

def test_bottom_line_leads_with_the_answer(searched_report, baseline_report):
    """A partner who reads only the first paragraph should get the decision (searched) or
    the situation (baseline)."""
    assert "## The bottom line" in searched_report
    assert "The move:" in searched_report and "in that order" in searched_report
    # Baseline has no recommendation to lead with — it points at the decision instead.
    assert "The move:" not in baseline_report
    assert "five changes" in baseline_report.lower()


def test_your_firm_is_recognizable_and_reconciled(searched_report):
    """The 'Your firm' section names the firm's traits and reconciles stated vs simulated PPP."""
    section = searched_report.split("## Your firm")[1].split("## Where")[0]
    assert "billing by the hour" in section
    assert "One number to reconcile" in section
    assert "$440,000" in section                          # the gap, stated plainly


def test_heading_unchanged_shows_the_slide(searched_report):
    section = searched_report.split("## Where it's heading")[1].split("## The changes")[0]
    assert "profit per partner moves from" in section
    assert "%)" in section                                # the percentage move


def test_changes_on_the_table_lists_five_plain_options(searched_report):
    section = searched_report.split("## The changes on the table")[1].split("## The recommendation")[0]
    for name in ("Flat-fee pricing", "Codified hand-offs", "AI-adoption pay", "Faster action", "Flatter pyramid"):
        assert name in section


def test_recommendation_gives_order_standing_and_method(searched_report):
    section = searched_report.split("## The recommendation")[1].split("## What the simulation")[0]
    assert "Why that order." in section
    assert "Flat fees first" in section
    # comp's sign flip, stated once, in plain terms
    assert "flips with how you bill" in section
    assert "How we got there." in section
    assert "What this doesn't include." in section


def test_scenario_section_says_what_the_sim_did_and_showed(scenario_report):
    section = scenario_report.split("## What the simulation did")[1].split("## How to read")[0]
    assert "fresh scenarios" in section
    assert "whichever way the year breaks" in section or "provisional" in section


def test_baseline_stops_before_the_recommendation(baseline_report):
    """No search, no recommendation section and no scenario section — inventing one is worse."""
    assert "## The recommendation" not in baseline_report
    assert "## What the simulation did" not in baseline_report
    assert "## The changes on the table" in baseline_report   # the options still stand


# --- executive lens: plain language, no machinery -----------------------------------

def test_no_variable_names_jargon_or_math_reaches_the_reader(searched_report):
    forbidden = [
        "pricing_posture", "leverage_ratio", "origination_concentration", "baseline_ppp",
        "Δ PPP", "Δ margin", "coefficient", "[SURVEY]", "[INFERRED]", "[ASSUMPTION]",
        "| field | value |", "1σ", "95% CI", "PPP of", "Phase 1", "Phase 2", "the band does not reach zero",
    ]
    for token in forbidden:
        assert token not in searched_report, f"leaked to the reader: {token!r}"


def test_firm_appendix_reads_in_plain_language(searched_report):
    section = searched_report.split("Your firm, on the record")[1]
    assert "How you bill:" in section
    assert "billing by the hour" in section
    assert "Associates per partner:" in section


def test_calibration_question_is_surfaced(searched_report):
    """One answerable question beats 'calibrate the model' — kept in the appendix now."""
    assert "AFA margin conversion" in searched_report


# --- structure ---------------------------------------------------------------------

def _headings(report):
    return [ln for ln in report.splitlines() if ln.startswith("## ")]


def test_appendix_lettering_has_no_gaps(baseline_report, searched_report):
    for report in (baseline_report, searched_report):
        letters = [h.split("Appendix ")[1][0] for h in _headings(report) if "Appendix " in h]
        assert letters == list("ABCDEFGH"[:len(letters)])


def test_headings_are_separated_from_their_prose(searched_report):
    lines = searched_report.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("#"):
            assert lines[i + 1].strip() == "", f"no blank line after heading: {line!r}"


def test_no_apology_for_missing_data(tmp_path):
    """A run with no metric history says so plainly, never '_Insufficient data_'."""
    import json
    run_dir = tmp_path / "empty"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(json.dumps({
        "run_id": "empty", "firm_name": "Testwell LLP", "sprints": 4, "matters_per_sprint": 10,
        "firm_signature": {"pricing_posture": "hourly", "leverage_ratio": 3.5},
    }))
    report = build_report(run_dir, {"optimize": OPTIMIZE})
    assert "Insufficient data" not in report
