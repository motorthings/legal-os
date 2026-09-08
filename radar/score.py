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
    CAPABILITY_WEIGHTS, CAPABILITY_SEEDS, FAULT_ANNOTATIONS,
    ENABLE_WEIGHTS, ENABLE_SEEDS,
    SOFTWARE_WEIGHTS, SOFTWARE_SEEDS, SOFTWARE_HALF_LIFE, FLAG_MULTIPLIER,
)

# Saturation divisors: how fast each meter's evidence saturates toward 10. Larger =
# slower, more conservative. The capability lane is the most conservative on purpose
# — a demonstration should nudge, not shout, so speculation never reads as a ruling.
RULING_DIVISOR = 3.0
ADOPTION_DIVISOR = 2.0
CAP_DIVISOR = 4.0
ENABLE_DIVISOR = 2.0   # market enablement (E), same conservative saturating shape as adoption
SOFTWARE_DIVISOR = 2.5 # software capability (S), momentum-shaped; slightly slower than adoption

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


def _attributes_to(item, fault_line):
    """Attribution gate: an item evidences a fault line iff its curated `fault_lines` lists
    it. Signal matching falls back only for uncurated items. Attribution by curation (not
    substring signals) lets one cross-cutting item evidence many lines cleanly and stops
    signal-word leakage (e.g. the signal 'certif' matching 'uncertified')."""
    curated = item.get("fault_lines")
    if curated:
        return fault_line["id"] in curated
    return bool(_matches(item, fault_line))


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


def _enable_weight(item, as_of=None):
    """Market-enablement weight (E): can a firm actually stand the control up from what the
    market offers now? Only items carrying an `enable` class count toward E.

    Unlike ruling/adoption momentum, enable evidence is a PERSISTENT supply fact: once a tool
    is proven at scale, a standard exists, or a provider category matures, it does not un-happen
    a year later. So enable evidence does NOT decay (same logic as capability). Class weights
    already separate a lasting deploy-at-scale (1.00) from a passing launch (0.30)."""
    cls = item.get("enable")
    if cls not in ENABLE_WEIGHTS:
        return 0.0, None
    w = ENABLE_WEIGHTS[cls]
    if item.get("empirical"):
        w *= EMPIRICAL_BOOST
    return w, cls


def _software_weight(item, as_of):
    """Software-capability weight (S): what are legal-AI software vendors enabled to
    build next? Only items carrying a `software` class count. Unlike E (a persistent
    supply fact), S is FORWARD momentum and therefore DECAYS — a funding round from two
    years ago doesn't signal today's build. Uses its own half-life (SOFTWARE_HALF_LIFE),
    shorter than the ruling half-life because build momentum is short-lived.

    A `flag` (continuation/direction_shift/origination) scales the weight: a momentum
    signal can only predict continuation, so a first-of-kind move (origination) earns
    zero and a re-anchoring M&A (direction_shift) earns a reduced share."""
    cls = item.get("software")
    if cls not in SOFTWARE_WEIGHTS:
        return 0.0, None
    w = SOFTWARE_WEIGHTS[cls]
    w *= FLAG_MULTIPLIER.get(item.get("flag"), 1.0)   # missing flag = continuation
    if item.get("empirical"):
        w *= EMPIRICAL_BOOST
    age_days = (as_of - _parse_date(item["date"])).days
    if age_days > 0:
        w *= 0.5 ** (age_days / SOFTWARE_HALF_LIFE)
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


def _two_sided_pressure(net, seed, divisor):
    """Two-sided saturating pressure for the ruling (L2) meter.

    Positive net lifts the seed toward 10 (the existing behavior); negative net drags
    it toward 0, because a counter-ruling (e.g. a court saying disclosure is NOT
    required) genuinely weakens the analyst thesis rather than merely offsetting the
    lift. Symmetric and deterministic, so score replay stays exact."""
    if net >= 0:
        return seed + (10 - seed) * (1 - math.exp(-net / divisor))
    return seed * math.exp(net / divisor)


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
        neg_tiers_seen = set()
        adoption_evidence = []
        market_classes = set()
        capability_evidence = []
        capability_classes = set()
        enable_evidence = []
        enable_classes = set()
        software_evidence = []
        software_classes = set()
        for item in feed:
            # Point-in-time: only evidence available on/before as_of counts.
            # This is what makes backtesting (calibration) honest.
            if _parse_date(item["date"]) > as_of:
                continue
            if not _attributes_to(item, fl):
                continue
            hits = _matches(item, fl)  # provenance strings only; may be empty under curation
            w = _item_weight(item, as_of)
            # Negative evidence: an item can COUNTER a fault line (e.g. a court holding
            # that disclosure is NOT required). `negative_fault_lines` lists the lines the
            # item argues against; its weight is subtracted there and added everywhere else.
            negative = fl["id"] in item.get("negative_fault_lines", [])
            evidence.append({
                "date": item["date"], "title": item["title"], "tier": item["tier"],
                "source": item.get("source", ""), "url": item.get("url", ""),
                "weight": round(-w if negative else w, 3), "matched": hits,
                "empirical": bool(item.get("empirical")),
                "conflict": bool(item.get("conflict")),
                "negative": negative,
            })
            if negative:
                neg_tiers_seen.add(item["tier"])
            else:
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

            # Enablement (E): does this item also show the market can supply the means
            # to stand the control up (deploy_scale, standard, provider ...)?
            ew, ecls = _enable_weight(item, as_of)
            if ecls:
                enable_evidence.append({
                    "date": item["date"], "title": item["title"], "tier": item["tier"],
                    "enable": ecls, "weight": round(ew, 3), "matched": hits,
                    "empirical": bool(item.get("empirical")),
                })
                enable_classes.add(ecls)

            # Software capability (S): does this item signal vendors building toward
            # this control (capital, acquisition, model access, regulatory room)?
            sw, scls = _software_weight(item, as_of)
            if scls:
                software_evidence.append({
                    "date": item["date"], "title": item["title"], "tier": item["tier"],
                    "software": scls, "weight": round(sw, 3), "matched": hits,
                    "empirical": bool(item.get("empirical")),
                    "flag": item.get("flag"),
                })
                software_classes.add(scls)

        # Corroboration: reward agreement across distinct tiers (independence), computed
        # separately for positive and negative evidence so a counter-ruling is not
        # "corroborated" into a larger drag by sharing tiers with supporting evidence.
        pos_corr = max(0, len(tiers_seen) - 1) * CORROBORATION_STEP
        neg_corr = max(0, len(neg_tiers_seen) - 1) * CORROBORATION_STEP
        pos_weighted = sum(e["weight"] for e in evidence if e["weight"] > 0) * (1 + pos_corr)
        neg_weighted = -sum(e["weight"] for e in evidence if e["weight"] < 0) * (1 + neg_corr)
        weighted = pos_weighted - neg_weighted   # net signed evidence
        n_negative = sum(1 for e in evidence if e["negative"])

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

        # L2 — ruling pressure: two-sided saturating. Positive evidence lifts the seed
        # toward 10; negative evidence drags it toward 0 (below the seed), because a
        # counter-ruling weakens the thesis, it does not merely offset the lift.
        seed = fl["pressure_seed"]
        pressure = round(_two_sided_pressure(weighted, seed, RULING_DIVISOR), 1)

        # L3 — control-adoption pressure: same shape, market-weighted evidence only,
        # corroborated across distinct market classes (insurer + RFP + deployment ...).
        a_corr = max(0, len(market_classes) - 1) * CORROBORATION_STEP
        a_weighted = sum(e["weight"] for e in adoption_evidence) * (1 + a_corr)
        a_seed = ADOPTION_SEEDS.get(fl["id"], 3.0)
        a_lift = (10 - a_seed) * (1 - math.exp(-a_weighted / ADOPTION_DIVISOR))
        adoption = round(min(10.0, a_seed + a_lift), 1)
        adoption_evidence.sort(key=lambda e: (MARKET_WEIGHTS[e["market"]], e["date"]),
                               reverse=True)

        # E — market enablement: same shape, enable-weighted evidence only, corroborated
        # across distinct enable classes. Part B (T-market): never a backtested call.
        e_corr = max(0, len(enable_classes) - 1) * CORROBORATION_STEP
        e_weighted = sum(e["weight"] for e in enable_evidence) * (1 + e_corr)
        e_seed = ENABLE_SEEDS.get(fl["id"], 3.0)
        e_lift = (10 - e_seed) * (1 - math.exp(-e_weighted / ENABLE_DIVISOR))
        enable = round(min(10.0, e_seed + e_lift), 1)
        enable_evidence.sort(key=lambda e: (ENABLE_WEIGHTS[e["enable"]], e["date"]),
                             reverse=True)

        # S — software capability: momentum-shaped, software-weighted evidence only,
        # corroborated across distinct software classes. Part B (T-market), forward.
        s_corr = max(0, len(software_classes) - 1) * CORROBORATION_STEP
        s_weighted = sum(e["weight"] for e in software_evidence) * (1 + s_corr)
        s_seed = SOFTWARE_SEEDS.get(fl["id"], 3.0)
        s_lift = (10 - s_seed) * (1 - math.exp(-s_weighted / SOFTWARE_DIVISOR))
        software = round(min(10.0, s_seed + s_lift), 1)
        software_evidence.sort(key=lambda e: (SOFTWARE_WEIGHTS[e["software"]], e["date"]),
                               reverse=True)

        # The Harbor cell: both meters high == the control is urgent AND about to be
        # mandatory. Product (scaled 0-10) so a low reading on either pulls it down.
        queue = round((pressure / 10.0) * (adoption / 10.0) * 10.0, 1)
        lead = LEAD_BY_HORIZON.get(fl["horizon"], "~1 year")

        # Trend arrow from recent (<=120d) weighted momentum vs standing base. Signed:
        # a recent counter-ruling can pull the trend to "quiet", not just "steady".
        recent = sum(e["weight"] for e in evidence
                     if (as_of - _parse_date(e["date"])).days <= 120)
        trend = "rising" if recent >= 0.8 else ("steady" if recent > -0.8 else "quiet")

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
            "weighted_positive": round(pos_weighted, 2),
            "weighted_negative": round(neg_weighted, 2),
            "corroboration": round(pos_corr, 2),
            "neg_corroboration": round(neg_corr, 2),
            "n_evidence": len(evidence),
            "n_negative": n_negative,
            "evidence": evidence,
            # --- third-order (L3) control-adoption layer ---
            "control": CONTROLS.get(fl["id"], ""),
            "seam": FAULT_ANNOTATIONS.get(fl["id"], {}).get("seam", "codifiable"),
            "driver": FAULT_ANNOTATIONS.get(fl["id"], {}).get("driver", "market"),
            "adoption_seed": a_seed,
            "adoption": adoption,
            "adoption_weighted": round(a_weighted, 2),
            "market_classes": sorted(market_classes),
            "n_adoption_evidence": len(adoption_evidence),
            "adoption_evidence": adoption_evidence,
            # --- enablement (E) — market deployability (Part B) ---
            "enable_seed": e_seed,
            "enable": enable,
            "enable_weighted": round(e_weighted, 2),
            "enable_classes": sorted(enable_classes),
            "n_enable_evidence": len(enable_evidence),
            "enable_evidence": enable_evidence,
            # --- software capability (S) — vendor build trajectory (Part B) ---
            "software_seed": s_seed,
            "software": software,
            "software_weighted": round(s_weighted, 2),
            "software_classes": sorted(software_classes),
            "n_software_evidence": len(software_evidence),
            "software_evidence": software_evidence,
            "queue": queue,
            "lead": lead,
        })

    results.sort(key=lambda r: r["pressure"], reverse=True)
    return {"as_of": as_of.isoformat(), "fault_lines": results,
            "tiers": SOURCE_TIERS, "market_weights": MARKET_WEIGHTS,
            "enable_weights": ENABLE_WEIGHTS, "enable_seeds": ENABLE_SEEDS,
            "software_weights": SOFTWARE_WEIGHTS, "software_seeds": SOFTWARE_SEEDS,
            "software_flag_multiplier": FLAG_MULTIPLIER,
            "n_items": len(feed)}


if __name__ == "__main__":
    out = score()
    print(f'{"CAP":>4} {"RULE":>5} {"ADOPT":>6} {"ENABLE":>7} {"SOFT":>5} {"QUEUE":>6}  {"LEAD":<12} FAULT LINE')
    for r in sorted(out["fault_lines"], key=lambda r: r["queue"], reverse=True):
        print(f'{r["capability"]:>4} {r["pressure"]:>5} {r["adoption"]:>6} {r["enable"]:>7} {r["software"]:>5} '
              f'{r["queue"]:>6}  {r["lead"]:<12} {r["title"]}  '
              f'[{r["control"]}]  (L1:{r["n_capability_evidence"]}ev '
              f'L2:{r["n_evidence"]}ev L3:{r["n_adoption_evidence"]}ev E:{r["n_enable_evidence"]}ev S:{r["n_software_evidence"]}ev)')
