"""Lane-isolation tests: an item feeds ONE primary lane, not several.

G5 isolated the ruling meter in 2026-09-14 — a T3 market action must never lift the ruling
grade. The symmetric bug was never fixed: a ruling was lifting the ADOPTION grade, reading
the same evidence twice. Measured on the real feed before the fix, 10 ruling-eligible items
were scoring in both lanes across 6 lines (`verification`, `disclosure`, `confidentiality`,
`competence`, `convergence`, `benchmark`). `pressure` and `adoption` were correlated by
construction, which is why `required = pressure OR adoption` barely discriminated (10 of 11
lines flagged).

Careful with the count: `fl["evidence"]` is provenance and holds 18 items that also appear
in adoption, but the T3/T4/T5 ones never moved the ruling grade. Counting provenance instead
of scoring overstates the defect by nearly double. The number that matters is 10.

The rule now: a rule-derived class (`process_mandate`) that is ruling-eligible belongs to the
ruling lane. An item that is NOT ruling-eligible keeps its adoption weight, because adoption
is the only lane that can count it and dropping it would lose evidence rather than
de-duplicate it.

Runs with pytest or standalone: `python radar/tests/test_lane_isolation.py`.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

from score import _market_weight, load_corpus                      # noqa: E402
import fault_lines as K                                            # noqa: E402


def _item(cls, tier, **kw):
    base = {"date": "2026-01-01", "tier": tier, "market": cls, "title": "t"}
    base.update(kw)
    return base


def test_ruling_eligible_rule_does_not_lift_adoption():
    """A T1/T2 rule mandating a process is already in the ruling lane. Not again here."""
    for tier in ("T1", "T2"):
        w, cls = _market_weight(_item("process_mandate", tier), None)
        assert (w, cls) == (0.0, None), f"{tier} process_mandate leaked into adoption"


def test_non_ruling_rule_keeps_its_adoption_weight():
    """A T3/T4 process_mandate is not in the ruling lane, so it stays in adoption.

    Dropping it would LOSE evidence, not de-duplicate it. `agentic`'s AI AGENT Act row is
    this case on the real feed.
    """
    from datetime import date
    for tier in ("T3", "T4", "T5"):
        w, cls = _market_weight(_item("process_mandate", tier), date(2026, 6, 1))
        assert cls == "process_mandate" and w > 0, f"{tier} lost its adoption weight"


def test_leverage_classes_are_never_excluded():
    """Market actors are the adoption lane's whole purpose. They must always count."""
    for cls in K.LEVERAGE_CLASSES:
        w, got = _market_weight(_item(cls, "T1"), None)
        assert got == cls and w > 0, f"{cls} was excluded from the adoption lane"


def test_no_ruling_eligible_item_also_scores_in_adoption():
    """The regression, asserted against the real feed rather than a fixture.

    NOTE on what counts. `fl["evidence"]` is the PROVENANCE list — it holds every matched
    item, including T3/T4/T5 market and commentary rows that cannot move the ruling grade
    (see README, G5). Overlap with provenance is expected and is not a double-count. The
    real question is whether an item SCORES in both lanes, which means ruling-eligible
    (T1/T2, or an explicit `ruling` override). That was 10 items across 6 lines before the
    fix; it is 0 now.
    """
    from fault_lines import RULING_TIERS
    offenders = []
    for fl in score_lines():
        for e in fl["adoption_evidence"]:
            if e.get("ruling_eligible") or e["tier"] in RULING_TIERS:
                offenders.append((fl["id"], e["market"], e["tier"], e["title"][:40]))
    assert not offenders, f"ruling-eligible items also scoring in adoption: {offenders}"


def score_lines():
    import score
    return score.score()["fault_lines"]


def test_adoption_lane_is_now_honest_about_how_thin_it_is():
    """The finding that motivated the fix: after separation, ONE line has leverage."""
    with_leverage = [fl["id"] for fl in score_lines()
                     if set(fl.get("market_classes", [])) & K.LEVERAGE_CLASSES]
    assert "insurance" in with_leverage
    # if this grows, the market really did move — update deliberately, don't loosen the test
    assert len(with_leverage) <= 3, f"leverage appeared on {with_leverage}; re-examine"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all lane-isolation tests passed")
