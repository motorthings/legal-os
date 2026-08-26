"""Tests for the 90-second decision one-pager.

The one-pager is a separate artifact from the full report: the move in order, the one
dependency that gates it, the one assumption to verify, and a falsifiable prediction with a
check-in. It renders from the SAME meta/experiments the full report uses (no metrics), so it
regenerates from stored render_inputs with no re-run. It must never print an internal key or a
sharp quarter call that the search didn't back.

Run: cd backend && /opt/homebrew/bin/python3 -m pytest tests/test_simulation_onepager.py -v
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.report import render_decision_onepager, load_meta
from simulation import optimize
from simulation.run_config import build_sim_config, build_firm, build_elasticities
from app.services.simulation import reportgen


# --- fixture ---------------------------------------------------------------------------

META = {
    "run_id": "run_t", "seed": 42, "firm_name": "Testwell LLP", "sprints": 16,
    "matters_per_sprint": 10, "provider": "mock",
    "firm_signature": {"pricing_posture": "hourly", "leverage_ratio": 3.5,
                       "baseline_ppp": 3_000_000, "baseline_rpl": 1_200_000},
}

OPTIMIZE = {
    "objective": "ppp", "objective_label": "PPP", "weights": {"ppp": 1.0}, "guardrails": [],
    "baseline_ppp": 2_400_000,
    "main_effects": {
        "pricing": {"delta_ppp": 180_000, "delta_margin": 3.1},
        "seams": {"delta_ppp": 120_000, "delta_margin": 2.2},
        "comp": {"delta_ppp": -40_000, "delta_margin": -0.8},
        "leverage": {"delta_ppp": 15_000, "delta_margin": 0.3},
        "latency": {"delta_ppp": 5_000, "delta_margin": 0.1},
    },
    "interactions": {"comp_x_pricing": {"delta": 45_000}},
    "best_combo": ["comp", "pricing", "seams"],
    "best_ppp": 2_780_000, "best_delta": 380_000, "spread": 60_000, "ci95": 28_000,
    "timing": {
        "objective": "PPP", "horizon_sprints": 16, "candidates": [1, 2, 3, 4, 5, 7],
        "spread_ppp": 18_700, "gain": 40_000, "all_q1_ppp": 3_057_454, "schedule_ppp": 3_097_499,
        "levers": {
            "pricing": {"start": 1, "cost_of_waiting": 305_272, "within_noise": False},
            "seams": {"start": 3, "cost_of_waiting": 82_307, "within_noise": False},
            "comp": {"start": 1, "cost_of_waiting": 16_046, "within_noise": True},
        },
    },
}

SENSITIVITY = {"bands": {
    "pricing": {
        "coefficient": "margin_ai_afa_gain", "coefficient_name": "AFA margin conversion",
        "calibration_question": "On flat-fee matters, when AI cuts the hours, how much do you keep?",
        "band_low": 90_000, "band_high": 240_000,
    },
    "seams": {
        "coefficient": "margin_redline_penalty", "coefficient_name": "Redline-rework margin cost",
        "calibration_question": "When a partner rewrites a draft, what does that cost the matter?",
        "band_low": 40_000, "band_high": 120_000,
    },
}}


def _onepager(optimize_override=None, sensitivity=SENSITIVITY, meta=META):
    opt = {**OPTIMIZE, **(optimize_override or {})}
    return render_decision_onepager(meta, {"optimize": opt, "sensitivity": sensitivity})


# --- the decision page, plain and complete -------------------------------------------

def test_onepager_leads_with_the_move_in_order():
    page = _onepager()
    assert "The move, in order" in page
    for name in ("Move to flat fees", "Write down the know-how at your hand-offs",
                 "Pay partners to use AI"):
        assert name in page
    # Order follows the plan, not alphabetical: pricing before comp.
    assert page.index("Move to flat fees") < page.index("Pay partners to use AI")


def test_onepager_names_the_dependency_and_when():
    page = _onepager()
    assert "The one thing the plan depends on." in page
    assert "only pays once you're on flat fees" in page
    assert "**When.**" in page
    assert "now" in page                      # pricing, act now
    assert "range, not a sharp call" in page  # comp is within noise


def test_onepager_names_the_one_thing_to_verify():
    page = _onepager()
    assert "The one thing to verify" in page
    assert "On flat-fee matters, when AI cuts the hours" in page   # the calibration question
    assert "$90,000 to $240,000" in page                            # the widest band


def test_onepager_commits_to_a_falsifiable_prediction():
    page = _onepager()
    assert "What we're predicting" in page
    assert "$2,780,000" in page                 # the headline PPP
    assert "$2,400,000" in page                 # "left as is" baseline
    assert "testable claim" in page             # the check-in
    assert "finding, not a failure" in page


def test_onepager_honesty_footer_and_no_jargon():
    page = _onepager()
    assert "What this does not claim." in page
    assert "not your P&L numbers" in page
    for token in ("best_combo", "best_ppp", "cost_of_waiting", "within_noise", "spread_ppp",
                  "band_low", "interactions", "calibration_question", "candidates", "main_effects"):
        assert token not in page, f"internal key leaked to reader: {token!r}"


def test_onepager_negative_band_is_honest_not_a_positive_range():
    """A lever measured alone can sweep negative (comp under hourly). The one-pager must not
    sign-strip a [-$247k, 0] band into a misleading positive '$247,000 to $0'."""
    sens = {"bands": {"comp": {"coefficient_name": "Comp to adoption",
                               "calibration_question": "If you tied comp to AI use, how much would adoption move?",
                               "band_low": -247_000, "band_high": 0}}}
    page = _onepager(sensitivity=sens)
    assert "up to roughly" in page
    assert "which direction depends on your answer" in page
    assert "$247,000 to $0" not in page


def test_onepager_empty_combo_is_honest_not_air():
    page = _onepager({"best_combo": [], "best_ppp": None})
    assert "none reliably beat standing still" in page
    assert "finding, not a failure" in page


def test_onepager_no_dependency_when_comp_not_in_plan():
    """If the plan doesn't pair comp with pricing, no dependency is invented."""
    page = _onepager({"best_combo": ["pricing", "seams"], "interactions": {"comp_x_pricing": {"delta": 0}}})
    assert "The one thing the plan depends on." not in page


# --- regeneration from stored render_inputs (no metrics needed) ------------------------

@pytest.fixture
def e2e_inputs(tmp_path):
    """A minimal run dir + config so reportgen.generate_report runs (sensitivity stubbed)."""
    run = tmp_path / "primary"; run.mkdir(parents=True)
    (run / "meta.json").write_text(json.dumps(META))
    (run / "metrics.csv").write_text("metric_id,sprint,value\nppp,1,2400000\nppp,16,2600000\n")
    rc = {"name": "t", "firm": {}, "objective": {"weights": {"ppp": 1.0}}}
    optimize.set_base_firm(build_firm({}), build_elasticities(rc))
    cfg = build_sim_config(rc, provider="mock", output_dir=str(tmp_path))
    mc = {"ppp": [2_600_000] * 3, "matter_profit_margin": [30.0] * 3, "rpl": [1_200_000] * 3,
          "realization_rate": [85.0] * 3, "associate_attrition": [20.0] * 3}
    opt = {**OPTIMIZE, **{"timing": OPTIMIZE["timing"]}}
    return run, rc, cfg, mc, opt


def test_reportgen_returns_onepager_and_it_regenerates_from_render_inputs(e2e_inputs, monkeypatch):
    """generate_report returns (markdown, render_inputs, onepager); re-rendering the onepager
    from the stored render_inputs (meta + experiments only) reproduces it byte-for-byte."""
    run, rc, cfg, mc, opt = e2e_inputs
    # Fast: stub the sensitivity sweep (not the subject under test here).
    async def _no_sens(*a, **k):
        return {}
    monkeypatch.setattr(reportgen, "_sensitivity_bands", _no_sens)

    async def run_it():
        return await reportgen.generate_report(
            "runX", run, rc, cfg, mc, optimize_result=opt, stage="lever_optimization")
    markdown, render_inputs, onepager = asyncio.run(run_it())

    assert onepager and "The move, in order" in onepager
    # Regenerate purely from what was stored — no re-run, no metrics.
    regen = render_decision_onepager(render_inputs["meta"], render_inputs["experiments"])
    assert regen == onepager
    # The full report still renders (unchanged path), just a different artifact.
    assert "## The bottom line" in markdown
