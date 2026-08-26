"""Tests for the "when to make each change" feature: the engine's phasing gates, the timing
search, and the report section that renders it.

The phasing model lets a lever start at a chosen quarter instead of quarter 1, holding the firm
at its pre-change state until then. Timing is judged on CUMULATIVE (mean-across-quarters) profit,
not the endpoint — the endpoint is, correctly, almost silent about timing, so the search ranks on
the cumulative measure, which can separate "act now" from "act later."

Run: cd backend && /opt/homebrew/bin/python3 -m pytest tests/test_simulation_timing.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.optimize import run_timing_search, set_base_firm
from simulation.src.orchestrator import Orchestrator, SimulationConfig, FirmSignature
from simulation.src.models.elasticities import default_profile
from simulation.report import build_report


def _cfg(phasing, comp=0.9, latency=1, sprints=8, matters=20):
    # Mirror how build_overrides sets the lever TARGET on the signature (afa_native for the
    # pricing lever) while capturing the firm's pre-change posture (hourly) for the phasing gate.
    sig = FirmSignature(pricing_posture="afa_native", leverage_ratio=5.0)
    return SimulationConfig(
        sprints=sprints, matters_per_sprint=matters, seed=42, llm_provider="mock",
        output_dir="results/_timing_test", firm_signature=sig,
        elasticities=default_profile(),
        comp_lever_strength=comp, decision_latency_sprints=latency, codify_seams=True,
        lever_start_sprints=phasing, pre_lever_pricing="hourly", pre_lever_leverage=3.5,
    )


# --- engine phasing gates --------------------------------------------------------------

def test_lever_active_gates_on_start_quarter():
    """A phased lever is off before its start quarter, on from it; an unphased lever is always on."""
    o = Orchestrator(_cfg({"comp": 5}))
    o.initialize()
    assert not o._lever_active("comp", 2)
    assert o._lever_active("comp", 5)
    o2 = Orchestrator(_cfg({}))                 # no phasing -> everything from quarter 1
    o2.initialize()
    assert o2._lever_active("comp", 1)


def test_phased_comp_holds_adoption_at_the_floor_before_activation():
    """Before the comp lever activates there is no adoption incentive, so adoption rides the
    partner-usage floor; an unphased comp lever (target strength from Q1) raises it immediately."""
    o = Orchestrator(_cfg({"comp": 5}))
    o.initialize()
    o_unphased = Orchestrator(_cfg({}))
    o_unphased.initialize()
    # Before activation: phased comp=0 -> ceiling is the 69% usage floor; unphased comp=0.9 -> higher.
    assert o._adoption_rate(2) < o_unphased._adoption_rate(2)
    # From the start quarter the target strength applies, so the phased firm catches up.
    assert o._adoption_rate(5) >= o._adoption_rate(2)


def test_phasing_changes_the_path_not_just_the_endpoint():
    """A phased pricing lever (delayed flat fees) must reduce cumulative profit vs pricing from Q1,
    even when the endpoint is the same — that is the timing signal the report renders."""
    import contextlib, io, asyncio, statistics
    def cum(phasing):
        o = Orchestrator(_cfg(phasing))
        o.initialize()
        with contextlib.redirect_stdout(io.StringIO()):
            r = asyncio.run(o.run())
        ppp = [snap.value for snap in r.company.metric_history["ppp"].values]
        return statistics.mean(ppp), ppp[-1]
    early_cum, early_end = cum({"pricing": 1, "comp": 1})
    late_cum, late_end = cum({"pricing": 6, "comp": 1})
    # Endpoints may converge (the engine is endpoint-silent on timing)…
    assert abs(early_end - late_end) < early_end * 0.5
    # …but the cumulative path is worse when the pricing change is delayed.
    assert late_cum < early_cum


# --- timing search ---------------------------------------------------------------------

def test_timing_search_returns_none_for_empty_combo():
    set_base_firm(None, None)
    assert run_timing_search([], seeds=[42], sprints=8, matters=20,
                             weights={"ppp": 1.0}, guardrails=[]) is None


def test_timing_search_returns_per_lever_start_and_noise():
    set_base_firm(None, None)
    t = run_timing_search(["pricing", "seams"], seeds=[42, 43, 44], sprints=8, matters=20,
                          weights={"ppp": 1.0}, guardrails=[])
    assert t is not None
    for lv in ("pricing", "seams"):
        d = t["levers"][lv]
        assert "start" in d and "cost_of_waiting" in d
        assert isinstance(d["within_noise"], bool)
    # Pricing (the foundation) is never worth delaying on the cumulative measure — waiting to the
    # last candidate loses money, a signal that clears the model's own spread.
    assert t["levers"]["pricing"]["cost_of_waiting"] > 0
    assert t["levers"]["pricing"]["within_noise"] is False


def test_timing_search_honors_objective_weights():
    """The search runs under the same weights the lever search used (here a blend)."""
    set_base_firm(None, None)
    t = run_timing_search(["pricing"], seeds=[42, 43], sprints=8, matters=20,
                          weights={"ppp": 0.6, "retention": 0.4}, guardrails=[])
    assert t is not None and t["objective"] == "priority blend"


# --- report section --------------------------------------------------------------------

def _timing_report(tmp_path):
    run_dir = tmp_path / "run_t"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(
        '{"run_id":"run_t","seed":42,"firm_name":"Testwell LLP","sprints":16,'
        '"matters_per_sprint":10,"provider":"mock","firm_signature":{"pricing_posture":"hourly",'
        '"leverage_ratio":3.5,"origination_concentration":0.4,"practice_mix_transactional":0.35,'
        '"client_concentration":0.3,"partner_power_mix":0.5,"tacit_work_share":0.5,'
        '"comp_model":"modified","client_afa_pressure":0.3,"partner_retirement_horizon":10.0,'
        '"baseline_ppp":3000000,"baseline_rpl":1200000,"baseline_realization":85.0,'
        '"baseline_margin":30.0,"tech_maturity":0.4,"culture":{"partner_ai_usage":0.69,'
        '"attrition_intensity":0.19,"escalation_design":0.5}}}')
    (run_dir / "metrics.csv").write_text(
        "metric_id,sprint,value\nppp,1,2500000\nppp,16,2600000\n")
    opt = {
        "objective": "ppp", "objective_label": "PPP", "weights": {"ppp": 1.0}, "guardrails": [],
        "baseline_ppp": 2400000,
        "main_effects": {
            "pricing": {"delta_ppp": 180000, "delta_margin": 3.1},
            "seams": {"delta_ppp": 120000, "delta_margin": 2.2},
            "comp": {"delta_ppp": -40000, "delta_margin": -0.8},
            "leverage": {"delta_ppp": 15000, "delta_margin": 0.3},
            "latency": {"delta_ppp": 5000, "delta_margin": 0.1},
        },
        "interactions": {"comp_x_pricing": {"delta": 45000}},
        "best_combo": ["comp", "pricing", "seams"],
        "best_ppp": 2780000, "best_delta": 380000, "spread": 60000, "ci95": 28000,
        "timing": {
            "objective": "PPP", "horizon_sprints": 16, "candidates": [1, 2, 3, 4, 5, 7],
            "spread_ppp": 18700, "gain": 40000, "all_q1_ppp": 3057454, "schedule_ppp": 3097499,
            "levers": {
                "pricing": {"start": 1, "cost_of_waiting": 305272, "within_noise": False},
                "seams": {"start": 3, "cost_of_waiting": 82307, "within_noise": False},
                "comp": {"start": 1, "cost_of_waiting": 16046, "within_noise": True},
            },
        },
    }
    return build_report(run_dir, {"optimize": opt, "stage": "lever_optimization"})


def test_report_renders_when_to_make_each_change(tmp_path):
    report = _timing_report(tmp_path)
    assert "**When to make each change.**" in report
    section = report.split("When to make each change.**")[1].split("Where each change stands.**")[0]
    # Coarse, grounded phrases — never a bare internal key.
    assert "Move to flat fees" in section and "now" in section
    assert "range, not a sharp call" in section                      # comp is within noise
    assert "not dates" in section
    for token in ("cost_of_waiting", "within_noise", "spread_ppp", "candidates",
                  "horizon_sprints", "all_q1", "best_start_score"):
        assert token not in section, f"internal token leaked to reader: {token!r}"


def test_report_omits_timing_when_search_found_nothing(tmp_path):
    """No timing search -> no section (nothing invented)."""
    run_dir = tmp_path / "run_nt"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text('{"run_id":"run_nt","firm_name":"T","sprints":16,'
        '"provider":"mock","firm_signature":{"pricing_posture":"hourly","leverage_ratio":3.5}}')
    (run_dir / "metrics.csv").write_text("metric_id,sprint,value\nppp,1,2500000\nppp,16,2600000\n")
    opt = {"objective": "ppp", "best_combo": ["pricing"], "best_ppp": 2600000,
           "baseline_ppp": 2500000, "spread": 60000}
    report = build_report(run_dir, {"optimize": opt, "stage": "lever_optimization"})
    assert "When to make each change." not in report
