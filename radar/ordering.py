"""The one ordering rule, shared by both surfaces.

The radar page and the advisory page answer different questions:

    radar page    "what is on the record, and how well supported is it?"  (firm-agnostic)
    advisory page "what should THIS firm do first?"                        (firm-specific)

They used to answer the first question by sorting on evidence strength and the second by
sorting on tier-then-urgency, and the two orders agreed on **none** of six rows. A reader
moving between the pages saw `verification` first and then sixth, with nothing on either
page explaining the inversion.

The fix is not to make the radar page firm-specific. It cannot be: it has no firm. It is
to have both pages read the same ordering rule, because this rule reads ONLY the record:

    1. tier        what requires the control vs what merely expects it, and un-met before met
    2. confidence  thin-evidence lines sort below supported ones
    3. urgency     SHORTEST measured lead first — a line whose antecedents historically bound
                   in 192 days gives less warning than one that bound in 907, so it is the one
                   to start on.

Nothing here reads pricing, carriers, or readiness. Those change a firm's VERDICTS on the
advisory page, and they never change this order — which is why the three demo postures
(hourly, fixed-fee, fixed-fee-building) currently produce the identical sequence. The
advisory page's own `sequence()` already implemented this rule; the radar page did not.

Both call `sort_key`. If the two ever diverge again it will be because one of them stopped
calling this, and `tests/test_ordering.py` fails when that happens.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import milestones  # noqa: E402

_CACHE: dict = {}


def facts():
    """Measured lead times, read once.

    Memoized deliberately: `milestones.grade()` replays the scoring engine once per
    milestone, and both surfaces ask for this repeatedly (the advisory once per posture).
    """
    if "v" in _CACHE:
        return _CACHE["v"]
    lead, overall = {}, []
    report = milestones.grade()
    for m in report["milestones"]:
        if m["status"] == "landed" and m["lead_days"] is not None:
            lead.setdefault(m["fault_line"], []).append(m["lead_days"])
            overall.append(m["lead_days"])
    # One number per line: the median where a line has several antecedents. A line with
    # none is ABSENT from `lead` rather than defaulted, because sort_key has to be able to
    # tell "measured at 0 days" from "never measured".
    med = {k: sorted(v)[len(v) // 2] for k, v in lead.items()}
    _CACHE["v"] = {"lead": med, "overall": sorted(overall)[len(overall) // 2] if overall else None}
    return _CACHE["v"]


def lead_days(line):
    """The measured lead for a line, or the record median, or None. For DISPLAY only.

    `sort_key` does not use this — it must not, or a line with no measurement of its own
    would be ranked against lines that were actually measured.
    """
    f = facts()
    if line in f["lead"]:
        return f["lead"][line], "this line"
    return f["overall"], "record median" if f["overall"] else None


def sort_key(line, *, tier: int = 0, thin: bool = False, pressure: float = 0.0):
    """The ordering tuple. Lower sorts first.

    tier     0 requires / un-met, 1 requires / met, 2 expects / un-met, 3 expects / met,
             4 nothing requires or expects it. The radar page passes 0 throughout, since
             its list contains only lines above the mandate threshold; the advisory page
             computes it from the firm's verdicts.
    thin     thin-evidence calls sort below supported ones within their tier.
    pressure final tiebreak, highest first.
    """
    leads = facts()["lead"]
    measured = line in leads
    return (tier,
            1 if thin else 0,
            0 if measured else 1,
            leads.get(line, 0),
            -pressure)
