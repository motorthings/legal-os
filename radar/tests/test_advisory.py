"""Fixture tests for the GOVERN decision logic.

The bugs these lock down, all found on 2026-09-17:

  1. threshold drift   — MANDATORY_PRESSURE was a hardcoded 7.0 whose own comment called it
                         "the radar call threshold" while calibration.CALL_THRESHOLD was 8.0
  2. fused triggers    — `required = pressure OR adoption` gave `confidentiality` (13 ruling
                         items, a binding rule) and `insurance` (zero ruling items, two CNA
                         questionnaires) the same `stand-up-now`
  3. opportunity leak  — `opportune` fed GOVERN, so a line that was explicitly NOT required
                         could still get a GOVERN verdict reading "required/open"
  4. no evidence floor — `agentic` was called `stand-up-now` off a single ruling item

Runs with pytest or standalone: `python radar/tests/test_advisory.py`.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import advisory
import calibration


def _fl(**kw):
    base = {"id": "x", "title": "t", "control": "c", "horizon": "h", "lead": "l",
            "capability": 5.0, "pressure": 5.0, "adoption": 5.0, "enable": 8.0,
            "seam": "codifiable", "driver": "deployment", "market_classes": [],
            "n_ruling_evidence": 0, "n_adoption_evidence": 0}
    base.update(kw)
    return base


def _decide(fl, pricing="fixed_fee"):
    firm = advisory.FirmPosture(pricing=pricing, enablement=7.0)
    gate = advisory._base_gate(firm)
    return advisory._decide(fl, gate, gate["hourly_full_capture"], firm)


def _set_leverage(fault_line="x", actors=("CNA",)):
    """Inject a synthetic leverage layer. The gate reads `leverage.facts()` through
    `advisory._leverage_facts()`, so the memo is the seam — no need to touch the real
    history file to exercise the decision logic."""
    by_line = {}
    if actors:
        by_line[fault_line] = {a: [{"fault_line": fault_line, "actor": a, "date": "2026-01-01",
                                    "requirement": f"{a} requires it"}] for a in actors}
    advisory._LEV_CACHE["v"] = {"requirements": [], "excluded": [], "by_fault_line": by_line,
                                "actors_by_line": {k: sorted(v) for k, v in by_line.items()}}


def _clear_leverage():
    advisory._LEV_CACHE.pop("v", None)


def test_threshold_is_imported_not_restated():
    """The mandate threshold must be one number, shared with the calibration layer."""
    assert advisory.MANDATED_PRESSURE == calibration.CALL_THRESHOLD


def test_duty_beats_norm_and_they_are_not_fused():
    """A duty and a market norm are different claims with different verdicts."""
    duty = _decide(_fl(pressure=9.0, adoption=5.0, n_ruling_evidence=10))
    _set_leverage()
    try:
        norm = _decide(_fl(pressure=5.0, adoption=9.0, n_adoption_evidence=10))
    finally:
        _clear_leverage()
    assert duty["mandated"] and not duty["expected"]
    assert norm["expected"] and not norm["mandated"]
    assert duty["govern"] == "stand-up-now"
    assert norm["govern"] == "match-the-market"
    assert duty["govern"] != norm["govern"]


def test_norm_alone_never_says_stand_up_now():
    """Only a duty earns `stand-up-now`. A norm the firm can meet is `match-the-market`."""
    _set_leverage()
    try:
        r = _decide(_fl(pressure=0.0, adoption=9.5, n_adoption_evidence=9))
    finally:
        _clear_leverage()
    assert r["govern"] == "match-the-market"


def test_table_stakes_requires_a_named_actor_not_a_score():
    """Adoption magnitude alone is not table stakes.

    This is the `benchmark` case: adoption 7.2 driven by a certification standard that
    nobody withholds anything over. The numeric threshold called it a norm; the leverage
    gate does not. Note the second half: adoption 0.0 WITH a requirement is a norm, because
    the claim is who requires it, not how much market evidence accumulated.
    """
    _set_leverage(actors=())
    try:
        no_actor = _decide(_fl(pressure=0.0, adoption=9.5, n_adoption_evidence=9))
    finally:
        _clear_leverage()
    assert no_actor["expected"] is False
    assert no_actor["leverage_actors"] == []
    assert no_actor["govern"] == "no-mandate"

    _set_leverage(actors=("CNA",))
    try:
        named = _decide(_fl(pressure=0.0, adoption=0.0, n_adoption_evidence=0))
    finally:
        _clear_leverage()
    assert named["expected"] is True
    assert named["leverage_actors"] == ["CNA"]


def test_expected_adoption_no_longer_gates_anything():
    """The retired threshold must not decide verdicts at any value."""
    verdicts = []
    for t in (0.0, 5.0, 7.0, 9.0, 10.0):
        keep = advisory.EXPECTED_ADOPTION
        advisory.EXPECTED_ADOPTION = t
        _set_leverage()   # leverage present, so `expected` is reachable
        try:
            verdicts.append(_decide(_fl(pressure=0.0, adoption=1.0))["expected"])
        finally:
            _clear_leverage()
            advisory.EXPECTED_ADOPTION = keep
    assert all(verdicts), f"expected should not depend on EXPECTED_ADOPTION, got {verdicts}"


def test_a_named_actor_clears_the_confidence_floor():
    """One carrier requiring a control OF YOU is decisive in a way two market signals are not."""
    _set_leverage(actors=("CNA",))
    try:
        theirs = advisory._decide(
            _fl(pressure=0.0, adoption=8.1, n_adoption_evidence=2),
            advisory._base_gate(advisory.FirmPosture(pricing="fixed_fee", enablement=7.0,
                                                     carriers=("CNA",))),
            advisory._base_gate(advisory.FirmPosture(pricing="fixed_fee",
                                                     enablement=7.0))["hourly_full_capture"],
            advisory.FirmPosture(pricing="fixed_fee", enablement=7.0, carriers=("CNA",)))
        generic = _decide(_fl(pressure=0.0, adoption=8.1, n_adoption_evidence=2))
    finally:
        _clear_leverage()
    assert theirs["leverage_is_yours"] is True and theirs["confidence"] == "supported"
    assert generic["leverage_is_yours"] is False and generic["confidence"] == "thin"
    # the verdict itself is the same; only the strength of the claim differs
    assert theirs["govern"] == generic["govern"] == "match-the-market"


def test_leverage_classes_match_the_taxonomy():
    """The gate reads fault_lines.LEVERAGE_CLASSES, so the two cannot drift."""
    import fault_lines as K
    assert K.LEVERAGE_CLASSES == {"insurer", "procurement", "deployment"}
    # a rule-derived class is never leverage — that is the whole point of the split
    assert "process_mandate" not in K.LEVERAGE_CLASSES
    assert "process_mandate" in K.ADOPTION_EXCLUDED


def test_opportunity_does_not_reach_govern():
    """Capability alone is a DEPLOY input. It must not produce a GOVERN mandate."""
    r = _decide(_fl(capability=9.0, pressure=0.0, adoption=0.0))
    assert r["opportunistic"] is True
    assert r["mandated"] is False and r["expected"] is False
    assert r["govern"] == "no-mandate"
    # ...but it still opens the deploy question
    assert r["deploy"] != "watch"


def test_evidence_floor_marks_thin_calls():
    thin = _decide(_fl(pressure=9.0, n_ruling_evidence=1))
    solid = _decide(_fl(pressure=9.0, n_ruling_evidence=9))
    assert thin["confidence"] == "thin"
    assert solid["confidence"] == "supported"
    assert "thin" in thin["govern_note"]
    # thin does not suppress the verdict, it labels it
    assert thin["govern"] == solid["govern"] == "stand-up-now"


def test_readiness_gates_the_verdict_not_the_mandate():
    not_ready = _decide(_fl(pressure=9.0, n_ruling_evidence=5))
    ready = advisory._decide(
        _fl(pressure=9.0, n_ruling_evidence=5),
        advisory._base_gate(advisory.FirmPosture(pricing="fixed_fee", enablement=2.0)),
        advisory._base_gate(advisory.FirmPosture(pricing="fixed_fee", enablement=2.0))["hourly_full_capture"],
        advisory.FirmPosture(pricing="fixed_fee", enablement=2.0))
    assert not_ready["govern"] == "stand-up-now"
    assert ready["govern"] == "build-capacity-first"
    # the mandate is unchanged by readiness — a duty does not stop being a duty
    assert not_ready["mandated"] is True and ready["mandated"] is True


def test_sequence_orders_duties_before_norms():
    firm = advisory.FirmPosture(pricing="fixed_fee", enablement=7.0)
    rows = [
        _decide(_fl(id="norm_ready", pressure=5.0, adoption=9.0, n_adoption_evidence=9)),
        _decide(_fl(id="nothing", pressure=0.0, adoption=0.0, capability=0.0)),
        _decide(_fl(id="duty_ready", pressure=9.0, n_ruling_evidence=9)),
    ]
    ordered, plan = advisory.sequence(rows)
    assert [r["fault_line"] for r in ordered] == ["duty_ready", "norm_ready", "nothing"]
    assert [p["sequence"] for p in plan] == [1, 2, 3]
    assert plan[0]["tier"] == "duty"


def test_sequence_puts_thin_calls_last_within_tier():
    rows = [
        _decide(_fl(id="thin", pressure=9.0, n_ruling_evidence=1)),
        _decide(_fl(id="solid", pressure=9.0, n_ruling_evidence=9)),
    ]
    ordered, _ = advisory.sequence(rows)
    assert [r["fault_line"] for r in ordered] == ["solid", "thin"]


def test_sequence_is_a_permutation_and_complete():
    """Every row lands in the plan exactly once — no drops, no duplicates."""
    r = advisory.run()
    assert len(r["plan"]) == len(r["rows"]) == 11
    assert sorted(p["sequence"] for p in r["plan"]) == list(range(1, 12))
    assert {p["fault_line"] for p in r["plan"]} == {x["fault_line"] for x in r["rows"]}


def test_govern_discriminates_on_the_real_board():
    """The regression that started this: 10 of 11 lines said `stand-up-now`.

    A ready firm is the interesting posture — below the readiness gate every mandated line
    collapses to `build-capacity-first` no matter what it is, which is correct but hides
    whether the duty/norm distinction is doing any work. So assert on both.
    """
    ready = advisory.run(advisory.FirmPosture(pricing="fixed_fee", refill=0.35, enablement=7.0))
    counts = ready["verdict_counts"]["govern"]
    assert counts.get("stand-up-now", 0) < len(ready["rows"]), counts
    assert len(counts) >= 3, f"GOVERN should return a spread of verdicts, got {counts}"
    # the duty/norm split survives: at least one norm is distinguished from the duties
    assert counts.get("match-the-market", 0) >= 1, counts

    # a firm below the readiness gate still discriminates, just on a different axis
    unready = advisory.run(advisory.FirmPosture(pricing="fixed_fee", enablement=2.0))
    uc = unready["verdict_counts"]["govern"]
    assert uc.get("stand-up-now", 0) == 0, uc
    assert uc.get("build-capacity-first", 0) > 0 and uc.get("no-mandate", 0) > 0, uc


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all advisory tests passed")
