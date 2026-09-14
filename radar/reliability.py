"""Source-reliability learning (Layer 3) — earned weight, kept honest.

The "use what it learned last time" half of run-to-run memory. Authority (tier) is
fixed; reliability is EARNED: a source whose earlier items kept presaging real rulings
gets a bounded multiplier on its weight (written to history/source_reliability.json,
read by score._item_weight, capped below primary authority).

THE HONESTY GATE. Only OUT-OF-SAMPLE presages count — rulings dated after
KNOBS_FROZEN_AT. In-sample hits are retrodiction (design §5.3): the feed and knobs were
authored knowing those rulings happened, so rewarding a source for "presaging" them would
tune the scorer on hindsight and quietly corrupt the forward-only holdout. Until forward
rulings accrue, every multiplier is 1.0 and scoring is byte-identical to Layer-2 — the
learning loop is wired and dormant, not faked.

A source `presages` a ruling when it has an item attributed to that ruling's fault line,
dated at least LEAD_DAYS before the ruling (early, not coincident). Reliability =
1 + PRESAGE_STEP × (distinct out-of-sample rulings presaged), capped at RELIABILITY_CAP_MULT.
The scorer applies it and then caps the effective weight at RELIABILITY_MAX_EFFECTIVE.
One-directional: the ledger is written here and only read by the scorer.
"""
import json
import hashlib
from datetime import timedelta
from pathlib import Path

import fault_lines as K
from fault_lines import (KNOBS_FROZEN_AT, PRESAGE_STEP, RELIABILITY_CAP_MULT,
                         FAULT_LINES)
from score import load_feed, _parse_date, _attributes_to

HISTORY = Path(__file__).parent / "history"
RELIABILITY_FILE = HISTORY / "source_reliability.json"
RES_FILE = HISTORY / "resolutions.jsonl"
LEAD_DAYS = 90   # a presage must lead the ruling by at least this much (matches calibration)


def _load_resolutions():
    if not RES_FILE.exists():
        return []
    out = []
    for line in RES_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def compute(feed=None, resolutions=None, frozen_at=KNOBS_FROZEN_AT):
    """Return {source: multiplier} earned from OUT-OF-SAMPLE presages only.

    A source earns credit when one of its items, attributed to a ruling's fault line and
    dated >= LEAD_DAYS before the ruling, precedes a real ruling dated AFTER frozen_at."""
    if feed is None:
        feed = load_feed()
    if resolutions is None:
        resolutions = _load_resolutions()

    # Only order-2 (ruling) resolutions dated strictly after the freeze are eligible.
    oos = [r for r in resolutions
           if r.get("order", 2) == 2 and r["date"] > frozen_at]

    presages = {}   # source -> set of ruling keys it presaged
    for r in oos:
        r_date = _parse_date(r["date"])
        fl = next((f for f in FAULT_LINES if f["id"] == r["fault_line"]), None)
        if fl is None:
            continue
        rk = f'{r["fault_line"]}@{r["date"]}'
        for item in feed:
            src = item.get("source", "")
            if not src:
                continue
            if not _attributes_to(item, fl):
                continue
            lead = (r_date - _parse_date(item["date"])).days
            if lead >= LEAD_DAYS:   # early enough to be a genuine presage
                presages.setdefault(src, set()).add(rk)

    multipliers = {}
    for src, rks in presages.items():
        m = min(RELIABILITY_CAP_MULT, 1.0 + PRESAGE_STEP * len(rks))
        if m > 1.0:
            multipliers[src] = round(m, 3)
    return multipliers


def _ledger_payload(multipliers, frozen_at, n_oos):
    return {
        "generated_from": {
            "knobs_frozen_at": frozen_at,
            "out_of_sample_resolutions": n_oos,
            "lead_days": LEAD_DAYS,
            "presage_step": PRESAGE_STEP,
            "cap_mult": RELIABILITY_CAP_MULT,
        },
        "note": ("Earned from OUT-OF-SAMPLE ruling presages only; in-sample hits are "
                 "retrodiction and excluded (design §5.3). Empty until forward rulings land."),
        "source_multipliers": multipliers,
    }


def refresh(feed=None, resolutions=None, frozen_at=KNOBS_FROZEN_AT):
    """Recompute and write the reliability ledger. Returns a summary for logging.
    Writes deterministically (sorted keys) so an unchanged learning state is a no-op diff."""
    if resolutions is None:
        resolutions = _load_resolutions()
    n_oos = len([r for r in resolutions
                 if r.get("order", 2) == 2 and r["date"] > frozen_at])
    multipliers = compute(feed=feed, resolutions=resolutions, frozen_at=frozen_at)
    payload = _ledger_payload(multipliers, frozen_at, n_oos)
    HISTORY.mkdir(exist_ok=True)
    RELIABILITY_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return {"n_boosted": len(multipliers), "out_of_sample_resolutions": n_oos,
            "sources": sorted(multipliers)}


def ledger_hash():
    """sha256 of the current ledger file (captured in run artifacts for replay)."""
    if not RELIABILITY_FILE.exists():
        return None
    return hashlib.sha256(RELIABILITY_FILE.read_bytes()).hexdigest()


if __name__ == "__main__":
    summary = refresh()
    print(f"reliability refreshed: {summary['n_boosted']} sources boosted "
          f"from {summary['out_of_sample_resolutions']} out-of-sample rulings")
    for s in summary["sources"]:
        print(f"  {s}")
    if not summary["n_boosted"]:
        print("  (none yet — learning loop dormant until post-freeze rulings accrue)")
