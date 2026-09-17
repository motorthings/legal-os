"""Fixture tests for the leverage layer.

This layer replaced `EXPECTED_ADOPTION = 7.0`, which could not be calibrated: it reached only
two lines, moved at most two verdicts across its whole range, and thresholded a meter resting
on three items across eleven lines. The replacement asks a countable question instead — does a
named actor who can withhold something require the control — so these tests pin the properties
that question needs.

Runs with pytest or standalone: `python radar/tests/test_leverage.py`.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import leverage
import fault_lines as K


def test_every_leverage_row_resolves():
    """A row naming evidence that is not in the corpus must fail, not silently drop."""
    for r in leverage.rows():
        assert r["title"], r


def test_requirement_and_exclusion_are_separated():
    """A reviewed-and-rejected row is kept and counted as a finding, not deleted."""
    reqs = leverage.requirements()
    excl = leverage.excluded()
    assert all(r.get("requirement") and r.get("actor") for r in reqs)
    assert all(not (r.get("requirement") and r.get("actor")) for r in excl)
    # the fees pricing-trend row is the documented rejection
    assert any(r["fault_line"] == "fees" for r in excl)


def test_the_record_has_exactly_one_leverage_requirement():
    """The honest state of the market evidence, asserted so it cannot drift unnoticed.

    If this grows, the market really moved. Update deliberately rather than loosening it.
    """
    reqs = leverage.requirements()
    assert len(reqs) == 1, f"leverage requirements changed: {[(r['actor'], r['fault_line']) for r in reqs]}"
    assert reqs[0]["actor"] == "CNA"
    assert reqs[0]["fault_line"] == "insurance"
    assert reqs[0]["withheld"] == "coverage"


def test_actors_are_deduplicated_per_line():
    """Two CNA items are ONE actor. Counting items made `insurance` look like it had two
    independent signals when it had one carrier saying two things."""
    facts = leverage.facts()
    assert facts["actors_by_line"]["insurance"] == ["CNA"]
    assert len(facts["by_fault_line"]["insurance"]) == 1


def test_every_requirement_uses_a_leverage_class():
    """A requirement from a class that withholds nothing is a category error."""
    for r in leverage.requirements():
        assert r["actor_class"] in K.LEVERAGE_CLASSES, r


def test_actor_match_is_case_insensitive_substring():
    assert leverage.actor_match("CNA", ("CNA",))
    assert leverage.actor_match("CNA Financial", ("cna",))
    assert leverage.actor_match("cna", ("CNA Financial",))
    assert not leverage.actor_match("CNA", ("Chubb",))
    assert not leverage.actor_match("CNA", ())
    assert not leverage.actor_match(None, ("CNA",))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all leverage tests passed")
