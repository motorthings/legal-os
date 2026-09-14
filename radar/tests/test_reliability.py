"""Tests for Layer-3 source-reliability learning — the honesty gate is the point.

Proves:
  1. dormant today   — no out-of-sample rulings => no source boosted (scoring unchanged)
  2. in-sample gated — a ruling on/before the freeze never earns a source credit
  3. earns + caps    — post-freeze presages boost a source, bounded by the cap
  4. effective cap   — the scorer never lifts an earned weight to/above primary authority

Runs with pytest or standalone: `python radar/tests/test_reliability.py`.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import reliability
import fault_lines as K


# A tiny synthetic feed: one T5 vendor source with early items on the disclosure line.
def _feed():
    return [
        {"date": "2027-01-01", "tier": "T5", "source": "ProvenVendorBlog",
         "title": "vendor foresees disclosure certification", "text": "disclosure standing order coming",
         "fault_lines": ["disclosure"]},
        {"date": "2027-01-02", "tier": "T5", "source": "ProvenVendorBlog",
         "title": "vendor foresees verification duty", "text": "verification audit trail coming",
         "fault_lines": ["verification"]},
        {"date": "2020-01-01", "tier": "T5", "source": "OldBlog",
         "title": "old take", "text": "disclosure musings", "fault_lines": ["disclosure"]},
    ]


def test_dormant_when_no_out_of_sample():
    # freeze in the far future -> nothing is out-of-sample
    mult = reliability.compute(feed=_feed(), resolutions=[
        {"date": "2027-06-01", "order": 2, "fault_line": "disclosure", "title": "ruling"}],
        frozen_at="2099-01-01")
    assert mult == {}, mult


def test_in_sample_ruling_earns_nothing():
    # ruling BEFORE the freeze is retrodiction -> excluded even though the vendor led it
    mult = reliability.compute(feed=_feed(), resolutions=[
        {"date": "2027-06-01", "order": 2, "fault_line": "disclosure", "title": "ruling"}],
        frozen_at="2027-12-31")
    assert mult == {}, mult


def test_out_of_sample_presage_earns_and_caps():
    # two post-freeze rulings the vendor's early items presaged (disclosure + verification)
    res = [
        {"date": "2027-06-01", "order": 2, "fault_line": "disclosure", "title": "d ruling"},
        {"date": "2027-06-01", "order": 2, "fault_line": "verification", "title": "v ruling"},
    ]
    mult = reliability.compute(feed=_feed(), resolutions=res, frozen_at="2026-12-31")
    assert "ProvenVendorBlog" in mult
    # 1 + PRESAGE_STEP * 2 distinct rulings, capped at RELIABILITY_CAP_MULT
    expected = min(K.RELIABILITY_CAP_MULT, 1.0 + K.PRESAGE_STEP * 2)
    assert abs(mult["ProvenVendorBlog"] - expected) < 1e-9, mult
    # OldBlog's item (2020) does not lead a 2027 ruling by a sane margin? It does lead,
    # but it's still only credited per ruling it is attributed to (disclosure) -> present.
    # The key property: multiplier is bounded.
    assert mult["ProvenVendorBlog"] <= K.RELIABILITY_CAP_MULT


def test_scorer_effective_weight_capped_below_primary():
    # Even a large earned multiplier cannot lift a source to/above primary authority.
    import score
    score._RELIABILITY = {"ProvenVendorBlog": 999.0}   # absurd earned trust
    item = {"tier": "T5", "source": "ProvenVendorBlog", "date": "2027-01-01"}
    from datetime import date
    w = score._item_weight(item, date(2027, 6, 1))
    assert w <= K.RELIABILITY_MAX_EFFECTIVE, w
    assert w < K.SOURCE_TIERS["T2"]["weight"], (w, "must stay below primary authority")
    score._RELIABILITY = None   # reset cache


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
