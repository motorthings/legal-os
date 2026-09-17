"""Fixture tests for the live/advisory fork.

The whole point of the fork is that refreshing the advisory corpus cannot move the
experiment's fingerprint. That is a property worth testing rather than asserting, so
test_freeze_survives_live_build hashes the frozen inputs around a live build.

Properties:
  1. superset      — the live corpus is the curated feed plus live additions
  2. no live rows  — a corpus with no live files is byte-identical to the curated one
  3. guard         — writing a frozen input is refused, not merely discouraged
  4. freeze holds  — build_live() leaves every frozen input unchanged

Runs with pytest or standalone: `python radar/tests/test_live.py`.
"""
import hashlib
import json
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import live


def _hash(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def test_live_corpus_is_superset_of_curated():
    from score import load_corpus
    base = load_corpus()
    both = live.live_corpus()
    assert len(both) >= len(base)
    # every curated row survives into the live corpus
    titles = {i["title"] for i in both}
    assert {i["title"] for i in base} <= titles


def test_no_live_files_means_curated_only():
    """Before the first live addition the advisory runs on the curated feed alone."""
    keep = (live.LIVE_FEED_PATH, live.LIVE_HARVESTED_PATH)
    try:
        live.LIVE_FEED_PATH = Path("/nonexistent/feed_live.jsonl")
        live.LIVE_HARVESTED_PATH = Path("/nonexistent/harvested_live.jsonl")
        assert live.load_live() == []
        f = live.freshness()
        assert f["n_live"] == 0 and f["newest_live_evidence"] is None
    finally:
        live.LIVE_FEED_PATH, live.LIVE_HARVESTED_PATH = keep


def test_guard_refuses_frozen_inputs():
    frozen = RADAR / "sources" / "feed.jsonl"
    try:
        live._guard([frozen])
    except RuntimeError as e:
        assert "refusing to write a frozen input" in str(e)
    else:
        raise AssertionError("the guard must refuse a frozen input")


def test_freeze_survives_live_build(tmp_path=None):
    """A live build must not move any frozen input."""
    import tempfile
    before = {p: _hash(p) for p in live.FROZEN_INPUTS}
    with tempfile.TemporaryDirectory() as d:
        live.DOCS_JSON = Path(d) / "live.json"
        live.FRONTEND_JSON = Path(d) / "frontend" / "live.json"
        data = live.build_live()
        assert live.DOCS_JSON.exists()
        assert data["n_items"] >= 1
    after = {p: _hash(p) for p in live.FROZEN_INPUTS}
    assert before == after, f"a frozen input changed: {before} -> {after}"


def test_advisory_reads_live_landscape_when_present():
    import advisory
    live.DOCS_JSON = RADAR.parent / "docs" / "radar" / "live.json"
    advisory.LIVE_JSON = live.DOCS_JSON
    if live.DOCS_JSON.exists():
        assert advisory.landscape_path().name == "live.json"
    # and the frozen landscape is still reachable explicitly
    assert advisory.landscape_path(prefer_live=False).name == "data.json"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all live tests passed")
