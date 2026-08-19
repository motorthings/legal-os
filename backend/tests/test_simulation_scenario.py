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


def test_baseline_stage_points_at_the_decision_not_a_recommendation(tmp_path):
    """The baseline stage stops at the changes on the table — no recommendation."""
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "sensitivity": SENSITIVITY, "stage": "baseline"})
    assert "## The changes on the table" in report
    assert "## The recommendation" not in report
    assert "The move:" not in report


def test_optimization_stage_recommends_with_plain_standings(tmp_path):
    """The optimization stage adds the recommendation, each change's standing in plain terms."""
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": OPTIMIZE, "sensitivity": SENSITIVITY,
                           "stage": "lever_optimization"})
    section = report.split("## The recommendation")[1].split("## How to read")[0]
    assert "Move to flat fees" in section
    assert "adds about $180,000" in section          # pricing standing, rounded + plain
    assert "flips with how you bill" in section       # comp's sequencing, once
    assert "## What the simulation did" not in report  # scenario section not yet


def test_negative_alone_but_kept_lever_reads_as_kept_not_denied(tmp_path):
    """A lever negative on its own but in the plan must not read as a flat 'left out'."""
    opt = {**OPTIMIZE,
           "best_combo": ["latency", "pricing", "seams"],
           "main_effects": {**OPTIMIZE["main_effects"],
                            "latency": {"delta_ppp": -30_000, "delta_margin": -0.5}}}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY,
                           "stage": "lever_optimization"})
    section = report.split("## The recommendation")[1]
    assert "earns its place once the others are in" in section
    assert "doesn't earn a place here" not in section.split("Act on results faster")[1][:200]


def test_scenario_stage_says_whether_it_held(tmp_path):
    """The scenario stage adds what the simulation did and whether the plan held up."""
    overlay = {"best_ppp": 2_900_000, "best_delta": 500_000, "spread": 42_000, "ci95": 19_000,
               "mc_seeds": 40}
    opt = {**OPTIMIZE, **overlay}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY,
                           "stage": "scenario_simulation", "prior": {"best_delta": 380_000}})
    section = report.split("## What the simulation did")[1]
    assert "40 fresh scenarios" in section
    assert "whichever way the year breaks" in section       # confirmed wording
    assert "optimization had estimated" in section           # compares to prior


def test_overlay_moves_the_numbers_in_the_recommendation(tmp_path):
    """A scenario re-run reuses the story but shows the refreshed figures."""
    overlay = {"best_ppp": 2_900_000, "best_delta": 500_000, "best_objective": 2_900_000,
               "best_delta_objective": 500_000, "spread": 42_000, "ci95": 19_000, "mc_seeds": 40}
    opt = {**OPTIMIZE, **overlay}
    report = build_report(_write_run(tmp_path),
                          {"run": RUN_BLOCK, "optimize": opt, "sensitivity": SENSITIVITY,
                           "stage": "scenario_simulation", "prior": {"best_delta": 380_000}})
    assert "## The recommendation" in report
    assert "$2,900,000" in report                            # refreshed best PPP reached the prose
