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
    MARKET_WEIGHTS, CONTROLS, ADOPTION_SEEDS, LEAD_BY_HORIZON,
    CAPABILITY_WEIGHTS, CAPABILITY_SEEDS,
)

# Saturation divisors: how fast each meter's evidence saturates toward 10. Larger =
# slower, more conservative. The capability lane is the most conservative on purpose
# — a demonstration should nudge, not shout, so speculation never reads as a ruling.
RULING_DIVISOR = 3.0
ADOPTION_DIVISOR = 2.0
CAP_DIVISOR = 4.0

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


def _market_weight(item, as_of):
    """Third-order weight: how binding the item is ON THE MARKET, not on a court.
    Only items carrying a `market` class count toward control-adoption pressure."""
    cls = item.get("market")
    if cls not in MARKET_WEIGHTS:
        return 0.0, None
    w = MARKET_WEIGHTS[cls]
    if item.get("empirical"):
        w *= EMPIRICAL_BOOST
    # Market momentum decays for non-standing tiers, same as ruling evidence.
    w *= _decay(_parse_date(item["date"]), as_of, item["tier"])
    return w, cls


def _capability_weight(item):
    """First-order weight: how HARD the demonstration is that AI can now do the thing.
    Only items carrying a `capability` class count toward L1. Unlike ruling and market
    evidence, capability does NOT decay — a proven capability persists, it does not
    un-happen. Empirical demonstrations still earn the hard-data boost."""
    cls = item.get("capability")
    if cls not in CAPABILITY_WEIGHTS:
        return 0.0, None
    w = CAPABILITY_WEIGHTS[cls]
    if item.get("empirical"):
        w *= EMPIRICAL_BOOST
    return w, cls


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
        adoption_evidence = []
        market_classes = set()
        capability_evidence = []
        capability_classes = set()
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

            # First-order (L1): does this item demonstrate the capability that CREATES
            # the fault line? (benchmark, study, release ...) Non-decaying.
            cw, ccls = _capability_weight(item)
            if ccls:
                capability_evidence.append({
                    "date": item["date"], "title": item["title"], "tier": item["tier"],
                    "capability": ccls, "weight": round(cw, 3), "matched": hits,
                    "empirical": bool(item.get("empirical")),
                })
                capability_classes.add(ccls)

            # Third-order (L3): does this item also signal the control being adopted?
            mw, cls = _market_weight(item, as_of)
            if cls:
                adoption_evidence.append({
                    "date": item["date"], "title": item["title"], "tier": item["tier"],
                    "market": cls, "weight": round(mw, 3), "matched": hits,
                })
                market_classes.add(cls)

        # Corroboration: reward agreement across distinct tiers (independence).
        corroboration = max(0, len(tiers_seen) - 1) * CORROBORATION_STEP
        weighted = sum(e["weight"] for e in evidence) * (1 + corroboration)

        # L1 — capability pressure: same saturating shape, capability-weighted evidence
        # only, corroborated across distinct demonstration classes. Held deliberately
        # conservative (CAP_DIVISOR) and clearly labeled so a capability that has
        # arrived never reads as a ruling that has landed.
        c_corr = max(0, len(capability_classes) - 1) * CORROBORATION_STEP
        c_weighted = sum(e["weight"] for e in capability_evidence) * (1 + c_corr)
        c_seed = CAPABILITY_SEEDS.get(fl["id"], 2.5)
        c_lift = (10 - c_seed) * (1 - math.exp(-c_weighted / CAP_DIVISOR))
        capability = round(min(10.0, c_seed + c_lift), 1)
        capability_evidence.sort(
            key=lambda e: (CAPABILITY_WEIGHTS[e["capability"]], e["date"]), reverse=True)

        # L2 — ruling pressure: move the seed toward 10 as weighted evidence
        # accumulates (saturating). Unchanged; this is the shipped meter.
        seed = fl["pressure_seed"]
        lift = (10 - seed) * (1 - math.exp(-weighted / RULING_DIVISOR))
        pressure = round(min(10.0, seed + lift), 1)

        # L3 — control-adoption pressure: same shape, market-weighted evidence only,
        # corroborated across distinct market classes (insurer + RFP + deployment ...).
        a_corr = max(0, len(market_classes) - 1) * CORROBORATION_STEP
        a_weighted = sum(e["weight"] for e in adoption_evidence) * (1 + a_corr)
        a_seed = ADOPTION_SEEDS.get(fl["id"], 3.0)
        a_lift = (10 - a_seed) * (1 - math.exp(-a_weighted / ADOPTION_DIVISOR))
        adoption = round(min(10.0, a_seed + a_lift), 1)
        adoption_evidence.sort(key=lambda e: (MARKET_WEIGHTS[e["market"]], e["date"]),
                               reverse=True)

        # The Harbor cell: both meters high == the control is urgent AND about to be
        # mandatory. Product (scaled 0-10) so a low reading on either pulls it down.
        queue = round((pressure / 10.0) * (adoption / 10.0) * 10.0, 1)
        lead = LEAD_BY_HORIZON.get(fl["horizon"], "~1 year")

        # Trend arrow from recent (<=120d) weighted momentum vs standing base.
        recent = sum(e["weight"] for e in evidence
                     if (as_of - _parse_date(e["date"])).days <= 120)
        trend = "rising" if recent >= 0.8 else ("steady" if recent > 0 else "quiet")

        evidence.sort(key=lambda e: (TIER_RANK[e["tier"]], e["date"]), reverse=True)
        results.append({
            **{k: fl[k] for k in ("id", "title", "model_rules", "horizon", "layer",
                                  "vector", "tech_driver", "build_now")},
            # --- first-order (L1) capability layer ---
            "capability_seed": c_seed,
            "capability": capability,
            "capability_weighted": round(c_weighted, 2),
            "capability_classes": sorted(capability_classes),
            "n_capability_evidence": len(capability_evidence),
            "capability_evidence": capability_evidence,
            "pressure_seed": seed,
            "pressure": pressure,
            "trend": trend,
            "weighted_evidence": round(weighted, 2),
            "corroboration": round(corroboration, 2),
            "n_evidence": len(evidence),
            "evidence": evidence,
            # --- third-order (L3) control-adoption layer ---
            "control": CONTROLS.get(fl["id"], ""),
            "adoption_seed": a_seed,
            "adoption": adoption,
            "adoption_weighted": round(a_weighted, 2),
            "market_classes": sorted(market_classes),
            "n_adoption_evidence": len(adoption_evidence),
            "adoption_evidence": adoption_evidence,
            "queue": queue,
            "lead": lead,
        })

    results.sort(key=lambda r: r["pressure"], reverse=True)
    return {"as_of": as_of.isoformat(), "fault_lines": results,
            "tiers": SOURCE_TIERS, "market_weights": MARKET_WEIGHTS,
            "n_items": len(feed)}


if __name__ == "__main__":
    out = score()
    print(f'{"CAP":>4} {"RULE":>5} {"ADOPT":>6} {"QUEUE":>6}  {"LEAD":<12} FAULT LINE')
    for r in sorted(out["fault_lines"], key=lambda r: r["queue"], reverse=True):
        print(f'{r["capability"]:>4} {r["pressure"]:>5} {r["adoption"]:>6} {r["queue"]:>6}  '
              f'{r["lead"]:<12} {r["title"]}  '
              f'[{r["control"]}]  (L1:{r["n_capability_evidence"]}ev '
              f'L2:{r["n_evidence"]}ev L3:{r["n_adoption_evidence"]}ev)')
