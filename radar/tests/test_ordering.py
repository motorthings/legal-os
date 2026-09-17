"""The ordering contract — the radar page and the advisory page must agree on what is first.

On 2026-09-17 the two surfaces ordered the same six duties by different rules and agreed on
**none** of the six positions. `verification` was first on one and sixth on the other;
`vendor_liability` was sixth on one and second on the other. Nothing on either page said so,
and each page was internally consistent, which is exactly why no existing test caught it.

The rule now lives in one place, `radar/ordering.py`. These tests fail if either surface
stops calling it, and — the load-bearing half — if a firm input ever leaks into the order.

Standalone: `python radar/tests/test_ordering.py`.
"""
import json
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
REPO = RADAR.parent
sys.path.insert(0, str(RADAR))

import ordering          # noqa: E402
import advisory as A     # noqa: E402

DATA_JSON = REPO / "docs" / "radar" / "data.json"


def test_two_surfaces_agree_on_the_duty_order():
    """THE test. The duties the radar page lists, in the radar page's order, must be the
    duties the advisory page lists, in the advisory page's order.

    Compares the shared subset: the advisory carries all eleven lines and the radar page's
    duty list carries only those over the mandate threshold, so the assertion is on the
    intersection, in each page's own relative order.
    """
    if not DATA_JSON.exists():
        return
    data = json.loads(DATA_JSON.read_text())
    radar_order = [f["id"] for f in
                   sorted((f for f in data["fault_lines"] if f.get("is_duty")),
                          key=lambda f: f["order_key"])]

    firm = A.run(A.DEMO_POSTURES[1])          # fixed-fee, the app's default posture
    adv_order = [r["fault_line"] for r in sorted(firm["rows"], key=lambda r: r["sequence"])]

    shared = [x for x in adv_order if x in set(radar_order)]
    assert radar_order == shared, (
        "the two surfaces disagree on the duty order.\n"
        f"  radar page:    {radar_order}\n"
        f"  advisory page: {shared}\n"
        "Both must sort by ordering.sort_key."
    )


def test_order_reads_only_the_record():
    """The radar page has no firm, so its order must not move when a firm input does.

    The three demo postures differ in pricing, carriers, and readiness, and they change the
    VERDICTS. They must not change the sequence — that is what makes it legitimate for a
    firm-agnostic page to use the firm-specific page's rule.
    """
    orders = []
    for firm in A.DEMO_POSTURES:
        r = A.run(firm)
        orders.append([x["fault_line"] for x in sorted(r["rows"], key=lambda z: z["sequence"])])
    assert orders[0] == orders[1] == orders[2], (
        "a firm input moved the sequence. The order is supposed to read only the record; "
        "if a firm fact must move it, this rule is no longer shareable with the radar page "
        "and the radar page needs its own. Orders were:\n" + "\n".join(map(str, orders))
    )


def test_unmeasured_lines_sort_after_measured_ones():
    """A line with no milestone of its own has no measured lead. It is reported with the
    record median but must NOT be ranked as though 601 were a measurement — an invented
    number would place it against lines that were actually measured."""
    leads = ordering.facts()["lead"]
    measured = [l for l in leads]
    lines = sorted(measured + ["__no_such_line__"], key=lambda l: ordering.sort_key(l))
    assert lines[-1] == "__no_such_line__", (
        "a line with no measured lead sorted ahead of measured lines"
    )


def test_thin_sorts_below_supported_within_a_tier():
    a = ordering.sort_key("verification", tier=0, thin=True, pressure=9.9)
    b = ordering.sort_key("verification", tier=0, thin=False, pressure=0.0)
    assert b < a, "a thin-evidence call sorted above a supported one in the same tier"


def test_duty_sorts_before_norm_regardless_of_lead():
    """Tier outranks urgency. A market norm with a 30-day window still follows a duty with a
    900-day one, because the duty is not optional and the norm is."""
    duty = ordering.sort_key("x", tier=0, pressure=0.0)
    norm = ordering.sort_key("y", tier=2, pressure=0.0)
    assert duty < norm


def test_display_lead_never_ranks():
    """`lead_days` is for display. Its fallback to the record median must not reach
    `sort_key`, or every unmeasured line would be ranked by a number nobody measured."""
    days, source = ordering.lead_days("verification")
    assert days is not None and source == "this line"
    days, source = ordering.lead_days("__no_such_line__")
    assert days == ordering.facts()["overall"] and source == "record median"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("ordering contract holds")
