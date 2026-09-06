"""Deterministic, explainable scorer for the Fault-Line Radar.

A fault line's pressure is the seed thesis moved by *weighted* evidence, where
weight is earned by source authority, corroborated by independent tiers, boosted
by hard data, and discounted for conflict of interest. Volume alone moves nothing.

Pure function of (feed, fault_lines, as_of) + the explicit knobs in fault_lines.py,
so any score replays exactly. Every fault line reports the evidence that moved it.
"""
import json
import math
from datetime import date, datetime
from pathlib import Path

from fault_lines import (
    FAULT_LINES, SOURCE_TIERS, CONFLICT_DISCOUNT, EMPIRICAL_BOOST,
    CORROBORATION_STEP, HALF_LIFE_DAYS, STANDING_TIERS,
)

FEED_PATH = Path(__file__).parent / "sources" / "feed.jsonl"
TIER_RANK = {"T1": 5, "T2": 4, "T3": 3, "T4": 2, "T5": 1}


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def load_feed(path=FEED_PATH):
    items = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def _decay(item_date, as_of, tier):
    """Momentum decay. Standing authority (T1/T2) never decays out."""
    if tier in STANDING_TIERS:
        return 1.0
    age_days = (as_of - item_date).days
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def _item_weight(item, as_of):
    tier = item["tier"]
    w = SOURCE_TIERS[tier]["weight"]
    if item.get("conflict"):
        w *= CONFLICT_DISCOUNT
    if item.get("empirical"):
        w *= EMPIRICAL_BOOST
    w *= _decay(_parse_date(item["date"]), as_of, tier)
    return w


def _matches(item, fault_line):
    hay = (item.get("title", "") + " " + item.get("text", "")).lower()
    return [s for s in fault_line["signals"] if s in hay]


def score(feed=None, as_of=None):
    """Return a list of scored fault lines with full provenance."""
    if feed is None:
        feed = load_feed()
    if as_of is None:
        as_of = date.today()
    elif isinstance(as_of, str):
        as_of = _parse_date(as_of)

    results = []
    for fl in FAULT_LINES:
        evidence = []
        tiers_seen = set()
        for item in feed:
            # Point-in-time: only evidence available on/before as_of counts.
            # This is what makes backtesting (calibration) honest.
            if _parse_date(item["date"]) > as_of:
                continue
            hits = _matches(item, fl)
            if not hits:
                continue
            w = _item_weight(item, as_of)
            evidence.append({
                "date": item["date"], "title": item["title"], "tier": item["tier"],
                "source": item.get("source", ""), "url": item.get("url", ""),
                "weight": round(w, 3), "matched": hits,
                "empirical": bool(item.get("empirical")),
                "conflict": bool(item.get("conflict")),
            })
            tiers_seen.add(item["tier"])

        # Corroboration: reward agreement across distinct tiers (independence).
        corroboration = max(0, len(tiers_seen) - 1) * CORROBORATION_STEP
        weighted = sum(e["weight"] for e in evidence) * (1 + corroboration)

        # Move the seed toward 10 as weighted evidence accumulates (saturating).
        seed = fl["pressure_seed"]
        lift = (10 - seed) * (1 - math.exp(-weighted / 3.0))
        pressure = round(min(10.0, seed + lift), 1)

        # Trend arrow from recent (<=120d) weighted momentum vs standing base.
        recent = sum(e["weight"] for e in evidence
                     if (as_of - _parse_date(e["date"])).days <= 120)
        trend = "rising" if recent >= 0.8 else ("steady" if recent > 0 else "quiet")

        evidence.sort(key=lambda e: (TIER_RANK[e["tier"]], e["date"]), reverse=True)
        results.append({
            **{k: fl[k] for k in ("id", "title", "model_rules", "horizon", "layer",
                                  "vector", "tech_driver", "build_now")},
            "pressure_seed": seed,
            "pressure": pressure,
            "trend": trend,
            "weighted_evidence": round(weighted, 2),
            "corroboration": round(corroboration, 2),
            "n_evidence": len(evidence),
            "evidence": evidence,
        })

    results.sort(key=lambda r: r["pressure"], reverse=True)
    return {"as_of": as_of.isoformat(), "fault_lines": results,
            "tiers": SOURCE_TIERS, "n_items": len(feed)}


if __name__ == "__main__":
    out = score()
    for r in out["fault_lines"]:
        print(f'{r["pressure"]:>4}  {r["trend"]:<7} {r["title"]}  '
              f'({r["n_evidence"]} ev, w={r["weighted_evidence"]})')
