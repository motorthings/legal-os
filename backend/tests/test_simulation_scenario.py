"""Stage 3 — Scenario Simulation.

The Monte Carlo re-run against a determined lever set. Two things must hold:
  - run_scenario_mc measures the FIXED combo (no search) and returns a refreshed band,
  - overlaying that band onto the optimization's stored dict keeps the recommendation
    narrative intact while only the numbers move — which is the whole point of being able
    to re-run the dice on the same lever set again and again.

Run: cd backend && /opt/homebrew/bin/python3 -m pytest tests/test_simulation_scenario.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.optimize import run_scenario_mc
from simulation.report import build_report

from tests.test_simulation_report import _write_run, RUN_BLOCK, SENSITIVITY, OPTIMIZE


def test_scenario_mc_measures_the_fixed_combo():
    """No search: the combo comes in fixed and comes back unchanged, with a real band."""
    rc = {"firm": {}, "objective": {}}
    out = run_scenario_mc(rc, ["seams", "pricing"], sprints=4, matters=8, mc_seeds=4)
    assert out["best_combo"] == ["pricing", "seams"]     # sorted, unchanged
    assert out["mc_seeds"] == 4
    assert out["spread"] >= 0.0
    assert out["ci95"] >= 0.0
    # It ran only the MC — two lever passes + two baseline passes over 4 seeds.
    assert out["sims_run"] > 0


def test_scenario_mc_is_deterministic():
    """Same inputs, same band — the reproducibility a comparison engine needs."""
    rc = {"firm": {}, "objective": {}}
    kw = dict(sprints=4, matters=8, mc_seeds=4)
    a = run_scenario_mc(rc, ["pricing"], **kw)
    b = run_scenario_mc(rc, ["pricing"], **kw)
    assert a == b


def test_baseline_summary_establishes_no_recommendation(tmp_path):
    """The baseline's At-a-glance says where you land and makes no recommendation."""
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "sensitivity": SENSITIVITY, "stage": "baseline"})
    assert "## At a glance — Baseline" in report
    assert "no recommendation" in report.lower()


def test_optimization_summary_confirms_and_denies_levers(tmp_path):
    """The lever search's At-a-glance gives a per-lever confirmed/denied verdict."""
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": OPTIMIZE, "sensitivity": SENSITIVITY,
                           "stage": "lever_optimization"})
    assert "## At a glance — Lever Optimization" in report
    assert "Recommendation: pull comp, pricing, seams" in report
    assert "Pricing confirmed" in report          # positive lever
    # Comp is negative alone but flips positive after pricing — the sequencing verdict.
    assert "Comp — it depends on sequence" in report


def test_negative_alone_but_kept_lever_is_not_called_denied(tmp_path):
    """A lever that scores negative on its own but is kept in the recommendation must not
    read as a flat 'denied' — that contradicts its place in the plan."""
    opt = {**OPTIMIZE,
           "best_combo": ["latency", "pricing", "seams"],
           "main_effects": {**OPTIMIZE["main_effects"],
                            "latency": {"delta_ppp": -30_000, "delta_margin": -0.5}}}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY,
                           "stage": "lever_optimization"})
    summary = report.split("## What this is")[0]
    assert "Latency denied" not in summary
    assert "negative alone, kept in the mix" in summary


def test_scenario_summary_gives_a_hold_up_verdict(tmp_path):
    """The scenario's At-a-glance says whether the lever set held up, and compares to prior."""
    overlay = {"best_ppp": 2_900_000, "best_delta": 500_000, "spread": 42_000, "ci95": 19_000,
               "mc_seeds": 40}
    opt = {**OPTIMIZE, **overlay}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY,
                           "stage": "scenario_simulation",
                           "prior": {"best_delta": 380_000}})
    assert "## At a glance — Scenario Simulation" in report
    assert "Verdict:" in report
    assert "40 fresh scenarios" in report
    # delta 500k exceeds band 19k → confirmed.
    assert "Confirmed" in report
    # Compares against the optimization's prior estimate.
    assert "optimization estimated" in report


def test_overlay_keeps_narrative_moves_the_band(tmp_path):
    """A scenario report reuses the optimization's story but shows the refreshed numbers."""
    overlay = {
        "best_combo": ["comp", "pricing", "seams"],
        "best_objective": 2_900_000, "best_delta_objective": 500_000,
        "best_ppp": 2_900_000, "best_delta": 500_000,
        "spread": 42_000, "ci95": 19_000, "mc_seeds": 40, "sims_run": 80,
    }
    opt = {**OPTIMIZE, **overlay}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY})
    # Narrative intact: still a searched report recommending the same levers.
    assert "## 4. What the lever search added" in report
    assert "Pull comp, pricing, seams" in report
    # Refreshed band reached the prose (the overlaid PPP delta, formatted).
    assert "$2,900,000" in report
