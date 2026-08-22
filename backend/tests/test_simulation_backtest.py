"""Tests for the back-test / validation loop: prediction recording, outcome ingest, and the
divergence math (error, % error, band-coverage). The divergence computation is pure, so it's
tested without a database; the db/route wiring is covered by imports + the integration suite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.simulation.db import _divergence_rows, replay_hash
from app.services.simulation.reportgen import _build_meta
from simulation.run_config import build_sim_config


def _row(pred=100.0, lo=80.0, hi=120.0, actual=None):
    return {"id": "p1", "run_id": "r1", "metric": "ppp", "predicted_value": pred,
            "band_low": lo, "band_high": hi, "horizon_sprints": 16, "config_hash": "h1",
            "predicted_at": None, "actual_value": actual, "source": "manual",
            "recorded_at": None}


def test_outcome_inside_band_is_covered():
    d = _divergence_rows([_row(actual=105)])[0]
    assert d["in_band"] is True
    assert d["error"] == 5
    assert d["pct_error"] == 5.0


def test_outcome_outside_band_is_flagged():
    d = _divergence_rows([_row(actual=200)])[0]
    assert d["in_band"] is False
    assert d["error"] == 100
    assert d["pct_error"] == 100.0


def test_no_outcome_yet_is_not_counted_as_wrong():
    d = _divergence_rows([_row(actual=None)])[0]
    assert d["error"] is None and d["pct_error"] is None
    assert d["in_band"] is False  # nothing to validate yet — not a miss


def test_no_band_means_no_coverage_claim():
    d = _divergence_rows([_row(lo=None, hi=None, actual=105)])[0]
    assert d["in_band"] is False  # no band => cannot claim coverage


def test_replay_hash_is_stable_and_distinguishing():
    cfg = {"run": {"model": "mock"}, "elasticities": {}}
    assert replay_hash(cfg, "mock", 20) == replay_hash(cfg, "mock", 20)
    assert replay_hash(cfg, "mock", 20) != replay_hash(cfg, "mock", 21)
    assert replay_hash(cfg, "mock", 20) != replay_hash(cfg, "deepseek", 20)


def test_build_meta_reconstructs_firm_context_from_config():
    """A deploy/restart can wipe the run disk and leave meta.json gone; the report must be
    able to rebuild firm name, horizon, and signature from the persisted config snapshot."""
    import tempfile
    rc = {"run": {"sprints": 12, "matters_per_sprint": 30, "model": "mock"},
          "firm": {"pricing_posture": "hourly", "leverage_ratio": 3.5, "baseline_ppp": 3_000_000}}
    cfg = build_sim_config(rc, provider="mock", output_dir=str(tempfile.mkdtemp()))
    meta = _build_meta(rc, cfg, {"mode": "deterministic", "count": 0})
    assert meta["sprints"] == 12
    assert "Aldrich" in meta["firm_name"]
    assert meta["provider"] == "mock"
    assert (meta.get("firm_signature") or {}).get("baseline_ppp") == 3_000_000
