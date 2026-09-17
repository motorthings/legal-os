"""Tests for the re-curation nudge.

The bugs these pin down, found 2026-09-17:

  1. wrong corpus  — the nudge read the frozen data.json while the re-curation skill wrote
                     the live corpus, so acting on it changed nothing it measured. A loop by
                     construction: same nudge every week, forever.
  2. wrong fix     — it prescribed case-law discovery for thinness that case-law discovery
                     provably cannot fix. Nine T1 orders moved neither line off 2/5 lanes.

Runs with pytest or standalone: `python radar/tests/test_stale_report.py`.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import stale_report


def _line(**kw):
    base = {"id": "x", "stale_days": 10, "lanes_populated": 5, "reviewed_days": None,
            "lanes": {"capability": 3, "ruling": 9, "adoption": 2, "enable": 1, "software": 1}}
    base.update(kw)
    return base


def test_current_line_is_not_flagged():
    needs, why, fix = stale_report.diagnose(_line())
    assert not needs and why == "" and fix == ""


def test_stale_line_routes_to_case_law():
    needs, why, fix = stale_report.diagnose(_line(stale_days=400))
    assert needs and "stale 400d" in why
    assert "case-law discovery" in fix


def test_thin_on_ruling_routes_to_case_law():
    """An empty ruling lane IS a case-law problem — that is the lane Descrybe fills."""
    f = _line(lanes_populated=2,
              lanes={"capability": 3, "ruling": 0, "adoption": 2, "enable": 1, "software": 0})
    needs, why, fix = stale_report.diagnose(f)
    assert needs
    assert "case-law discovery" in fix


def test_thin_on_adoption_routes_to_market_discovery():
    """The regression. A populated ruling lane plus empty market lanes is not a legal-research
    problem, and telling someone to run a case search at it wastes a pass."""
    f = _line(lanes_populated=2,
              lanes={"capability": 0, "ruling": 40, "adoption": 0, "enable": 2, "software": 0})
    needs, why, fix = stale_report.diagnose(f)
    assert needs and "2/5 lanes" in why
    assert "market discovery" in fix
    assert "case search will not move it" in fix
    assert "adoption" in fix and "software" in fix


def test_recently_reviewed_line_is_not_flagged():
    """A line a human checked within 30 days is dormant, not neglected."""
    needs, _, _ = stale_report.diagnose(_line(stale_days=400, reviewed_days=5))
    assert not needs


def test_stale_reviewed_long_ago_is_flagged_again():
    needs, _, _ = stale_report.diagnose(_line(stale_days=400, reviewed_days=200))
    assert needs


def test_reads_the_live_landscape_not_the_frozen_one():
    """The corpus fix. The nudge must measure what curation can actually change."""
    import live
    live_json = RADAR.parent / "docs" / "radar" / "live.json"
    frozen = RADAR.parent / "docs" / "radar" / "data.json"
    if live_json.exists():
        assert stale_report.landscape_path() == live_json
        assert stale_report.landscape_path() != frozen


def test_the_real_landscape_reports_no_loop():
    """Every flagged line must name a fix that could plausibly clear it."""
    import json
    data = json.loads(stale_report.landscape_path().read_text())
    for line in stale_report.needy_lines(data):
        assert "—" in line, f"flagged without a routing hint: {line}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all stale-report tests passed")
