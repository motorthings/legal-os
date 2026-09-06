"""Calibration layer — grade the forecaster against reality, auditably.

The engine earns trust by being scored, not by being confident. This layer:

  1. SNAPSHOT   — records every fault line's pressure at each run (a time series).
  2. BACKTEST   — for each resolution (a ruling/event that actually landed), replay
                  the engine POINT-IN-TIME `lead_days` before it landed, using only
                  evidence available then, and check whether the right fault line was
                  already elevated. "Called?" + how much lead.
  3. AUDIT      — writes an immutable, timestamped run artifact: knobs, evidence,
                  weights, pressure math, predictions, and this backtest. Replayable.

No date predictions. Just called-vs-actual, retro-scored. Honors the legal-os
pillars: deterministic replay, explainable, traceable.
"""
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

from score import score, load_feed, _parse_date, FEED_PATH
import fault_lines as K

HISTORY = Path(__file__).parent / "history"
SNAP_FILE = HISTORY / "snapshots.jsonl"
RES_FILE = HISTORY / "resolutions.jsonl"
RUNS_DIR = HISTORY / "runs"

CALL_THRESHOLD = 7.0   # pressure at/above this = the fault line was "flagged"
LEAD_DAYS = 90         # how far before the event we replay the engine


def _knobs():
    """The exact scoring configuration, captured for replay."""
    return {
        "tier_weights": {t: v["weight"] for t, v in K.SOURCE_TIERS.items()},
        "conflict_discount": K.CONFLICT_DISCOUNT,
        "empirical_boost": K.EMPIRICAL_BOOST,
        "corroboration_step": K.CORROBORATION_STEP,
        "half_life_days": K.HALF_LIFE_DAYS,
        "standing_tiers": sorted(K.STANDING_TIERS),
        "market_weights": K.MARKET_WEIGHTS,
        "adoption_seeds": K.ADOPTION_SEEDS,
        "capability_weights": K.CAPABILITY_WEIGHTS,
        "capability_seeds": K.CAPABILITY_SEEDS,
        "call_threshold": CALL_THRESHOLD,
        "lead_days": LEAD_DAYS,
    }


def load_resolutions():
    if not RES_FILE.exists():
        return []
    out = []
    for line in RES_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


# Which meter each order reads. Each order is graded against the lane it predicts.
_METER = {1: "capability", 2: "pressure", 3: "adoption"}
_EV_KEY = {"capability": "n_capability_evidence", "pressure": "n_evidence",
           "adoption": "n_adoption_evidence"}


def _reading_for(fault_id, as_of, order):
    """Return (value, evidence_count) for the meter that this order predicts."""
    data = score(as_of=as_of)
    meter = _METER.get(order, "pressure")
    ev_key = _EV_KEY.get(meter, "n_evidence")
    for fl in data["fault_lines"]:
        if fl["id"] == fault_id:
            return fl.get(meter), fl.get(ev_key, 0)
    return None, 0


def backtest(feed=None):
    """Replay the engine before each resolution landed, reading the meter for that
    resolution's ORDER. Reports hit rate overall, per order, and the cascade
    (L3 calls that rest on a called L2 for the same fault line)."""
    results = []
    for r in load_resolutions():
        order = r.get("order", 2)
        d = _parse_date(r["date"])
        lead_date = d - timedelta(days=LEAD_DAYS)
        v_lead, n_lead = _reading_for(r["fault_line"], lead_date.isoformat(), order)
        v_event, _ = _reading_for(r["fault_line"], r["date"], order)
        called = v_lead is not None and v_lead >= CALL_THRESHOLD
        results.append({
            "date": r["date"], "order": order, "fault_line": r["fault_line"],
            "title": r["title"], "url": r.get("url", ""),
            "meter": _METER.get(order, "pressure"),
            "reading_at_lead": v_lead, "evidence_at_lead": n_lead,
            "reading_at_event": v_event,
            "lead_days": LEAD_DAYS, "called": called,
        })

    def _rate(rows):
        n = len(rows); h = sum(1 for x in rows if x["called"])
        return {"n": n, "hits": h, "hit_rate": round(h / n, 2) if n else None}

    by_order = {o: _rate([x for x in results if x["order"] == o])
                for o in sorted({x["order"] for x in results})}

    # Cascade conditionals. Each layer only counts if the one it depends on held, so we
    # score the two links directly, per fault line (not across fault lines):
    #   P(L2 called | L1 called) — did the capability call precede the ruling that
    #     reacted to it? Only defined where the fault line has BOTH an L1 and an L2
    #     resolution on record; a called L1 with no L2 event yet means the law hasn't
    #     moved (capability outran the ruling) and is reported separately, not as a fail.
    #   P(L3 called | L2 called) — an adoption call only means something if the ruling
    #     it rests on held. (This is the shipped cascade check, unchanged in spirit.)
    def _conditional(prior_order, post_order):
        called_prior = {x["fault_line"] for x in results
                        if x["order"] == prior_order and x["called"]}
        post = [x for x in results if x["order"] == post_order]
        post_ids = {x["fault_line"] for x in post}
        # denominator: fault lines with a called prior AND a post event to condition on
        eligible = [x for x in post if x["fault_line"] in called_prior]
        backed = [x for x in eligible if x["called"]]
        # called priors that have no post event yet (the "outran" set)
        outran = sorted(called_prior - post_ids)
        return {
            "prior": f"L{prior_order}", "post": f"L{post_order}",
            "n_eligible": len(eligible),
            "n_backed": len(backed),
            "rate": round(len(backed) / len(eligible), 2) if eligible else None,
            "prior_called_without_post_event": outran,
        }

    l1_to_l2 = _conditional(1, 2)   # P(L2 called | L1 called)
    l2_to_l3 = _conditional(2, 3)   # P(L3 called | L2 called)

    # Back-compat cascade block (same numbers the page/artifact already read).
    cascade = {
        "n_l3_called": len([x for x in results if x["order"] == 3 and x["called"]]),
        "n_l3_backed_by_l2": l2_to_l3["n_backed"],
        "backed_rate": l2_to_l3["rate"],
    }

    overall = _rate(results)
    return {
        "resolutions": results,
        "n_resolutions": overall["n"],
        "hits": overall["hits"],
        "hit_rate": overall["hit_rate"],
        "by_order": by_order,
        "cascade": cascade,
        "conditionals": {"L1_to_L2": l1_to_l2, "L2_to_L3": l2_to_l3},
        "call_threshold": CALL_THRESHOLD,
        "lead_days": LEAD_DAYS,
    }


def snapshot(data):
    """Append today's pressures to the time series (one row per as_of date)."""
    HISTORY.mkdir(exist_ok=True)
    as_of = data["as_of"]
    existing = []
    if SNAP_FILE.exists():
        existing = [json.loads(l) for l in SNAP_FILE.read_text().splitlines() if l.strip()]
    existing = [e for e in existing if e.get("as_of") != as_of]  # replace same-day
    existing.append({
        "as_of": as_of,
        "pressures": {fl["id"]: fl["pressure"] for fl in data["fault_lines"]},
        "adoption": {fl["id"]: fl["adoption"] for fl in data["fault_lines"]},
        "queue": {fl["id"]: fl["queue"] for fl in data["fault_lines"]},
        "trends": {fl["id"]: fl["trend"] for fl in data["fault_lines"]},
    })
    existing.sort(key=lambda e: e["as_of"])
    SNAP_FILE.write_text("\n".join(json.dumps(e) for e in existing) + "\n")
    return len(existing)


def write_run_artifact(data, bt):
    """Immutable, timestamped, replayable record of the full run."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    feed_bytes = Path(FEED_PATH).read_bytes()
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": data["as_of"],
        "knobs": _knobs(),
        "feed_sha256": hashlib.sha256(feed_bytes).hexdigest(),
        "feed_items": data["n_items"],
        "fault_lines": data["fault_lines"],   # full provenance: evidence + weights + math
        "calibration": bt,
    }
    path = RUNS_DIR / f"run-{data['as_of']}-{ts}.json"
    path.write_text(json.dumps(artifact, indent=2))
    return str(path.relative_to(Path(__file__).parent))


def report():
    """Bundle for the page: backtest + current snapshot count."""
    bt = backtest()
    n_snaps = 0
    if SNAP_FILE.exists():
        n_snaps = len([l for l in SNAP_FILE.read_text().splitlines() if l.strip()])
    return {**bt, "snapshots_recorded": n_snaps}


if __name__ == "__main__":
    rep = report()
    print(f"Overall: {rep['hit_rate']} ({rep['hits']}/{rep['n_resolutions']}) "
          f"@ threshold {rep['call_threshold']}, {rep['lead_days']}d lead")
    for o, s in rep["by_order"].items():
        print(f"  L{o} ({K.ORDERS[o]['name']}): {s['hit_rate']} ({s['hits']}/{s['n']})")
    for key in ("L1_to_L2", "L2_to_L3"):
        cd = rep["conditionals"][key]
        rate = "n/a" if cd["rate"] is None else f"{int(cd['rate']*100)}%"
        line = (f"  P({cd['post']} called | {cd['prior']} called): {rate} "
                f"({cd['n_backed']}/{cd['n_eligible']})")
        if cd["prior_called_without_post_event"]:
            line += (f"  · {cd['prior']} called w/ no {cd['post']} event yet: "
                     f"{', '.join(cd['prior_called_without_post_event'])}")
        print(line)
    for r in rep["resolutions"]:
        mark = "HIT " if r["called"] else "miss"
        print(f'  {mark} L{r["order"]} {r["date"]} {r["fault_line"]:<14} '
              f'lead={r["reading_at_lead"]} event={r["reading_at_event"]}  {r["title"]}')
