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
