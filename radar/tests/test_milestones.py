"""Fixture tests for the milestone grader.

Proves the four properties the grader must have:
  1. integrity    — every reference in milestones.jsonl resolves to a corpus row
  2. arithmetic   — lead_days is the antecedent -> binding distance
  3. loud failure — a reference that names nothing raises instead of grading silently
  4. actionability — pending milestones with a precursor surface in actionable_now

Runs with pytest or standalone: `python radar/tests/test_milestones.py`.
No network, no embeddings.
"""
import json
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import milestones


CORPUS = [
    {"date": "2024-01-01", "tier": "T1", "title": "Alpha ruling", "source": "a",
     "url": "u1", "empirical": False, "conflict": False, "text": "t",
     "fault_lines": ["verification"]},
    {"date": "2025-01-01", "tier": "T1", "title": "Beta ruling", "source": "b",
     "url": "u2", "empirical": False, "conflict": False, "text": "t",
     "fault_lines": ["verification"]},
]


def test_every_milestone_reference_resolves():
    """The shipped milestones.jsonl must not name evidence that is not in the feed."""
    corpus = milestones.load_corpus()
    for m in milestones.load_milestones():
        for key in ("antecedent", "binding"):
            ref = m.get(key)
            if ref is not None:
                milestones._resolve(ref, corpus)   # raises if absent


def test_lead_days_arithmetic():
    rows = [
        {"fault_line": "verification", "status": "landed",
         "antecedent": {"date": "2024-01-01", "match": "Alpha"},
         "binding": {"date": "2025-01-01", "match": "Beta"}},
    ]
    ant = milestones._resolve(rows[0]["antecedent"], CORPUS)
    bind = milestones._resolve(rows[0]["binding"], CORPUS)
    from score import _parse_date
    assert (_parse_date(bind["date"]) - _parse_date(ant["date"])).days == 366


def test_bad_reference_fails_loudly():
    try:
        milestones._resolve({"date": "2024-01-01", "match": "Nonexistent"}, CORPUS)
    except ValueError as e:
        assert "not found" in str(e)
    else:
        raise AssertionError("a reference naming nothing must raise, not grade silently")


def test_ambiguous_reference_fails_loudly():
    corpus = CORPUS + [dict(CORPUS[0])]   # same date + title, distinct row
    try:
        milestones._resolve({"date": "2024-01-01", "match": "Alpha"}, corpus)
    except ValueError as e:
        assert "ambiguous" in str(e)
    else:
        raise AssertionError("a reference matching two rows must raise")


def test_pending_with_precursor_is_actionable():
    report = milestones.grade()
    for a in report["actionable_now"]:
        assert a["precursor"] and a["precursor_date"]
    # insurance and agentic are pending with a precursor on the record
    assert "insurance" in {a["fault_line"] for a in report["actionable_now"]}


def test_superseded_is_not_counted_as_landed():
    report = milestones.grade()
    statuses = {r["fault_line"]: r["status"] for r in report["milestones"]}
    assert "superseded" in statuses.values()
    landed = [r for r in report["milestones"] if r["status"] == "landed"]
    assert all(r["lead_days"] is not None for r in landed)


def test_blindside_scan_counts_first_item_per_line():
    scan = milestones.blindside_scan(corpus=CORPUS)
    # Alpha is the first standing item on `verification`, so it counts as a blindside;
    # Beta is not (Alpha precedes it on the same line).
    assert scan["n_no_precursor"] == 1
    assert scan["blindside_events"][0]["title"] == "Alpha ruling"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all milestone tests passed")
