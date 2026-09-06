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


# Which meter each order reads. L1 (capability) is the backlog lane — no resolutions yet.
_METER = {2: "pressure", 3: "adoption"}


def _reading_for(fault_id, as_of, order):
    """Return (value, evidence_count) for the meter that this order predicts."""
    data = score(as_of=as_of)
    meter = _METER.get(order, "pressure")
    ev_key = "n_evidence" if meter == "pressure" else "n_adoption_evidence"
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

    # Cascade: an L3 call only means something if the L2 it sits on held. For each
    # called L3, check the same fault line has a called L2. Each layer depends on the last.
    called_l2 = {x["fault_line"] for x in results if x["order"] == 2 and x["called"]}
    l3 = [x for x in results if x["order"] == 3]
    l3_called = [x for x in l3 if x["called"]]
    l3_backed = [x for x in l3_called if x["fault_line"] in called_l2]
    cascade = {
        "n_l3_called": len(l3_called),
        "n_l3_backed_by_l2": len(l3_backed),
        "backed_rate": round(len(l3_backed) / len(l3_called), 2) if l3_called else None,
    }

    overall = _rate(results)
    return {
        "resolutions": results,
        "n_resolutions": overall["n"],
        "hits": overall["hits"],
        "hit_rate": overall["hit_rate"],
        "by_order": by_order,
        "cascade": cascade,
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
    c = rep["cascade"]
    print(f"  Cascade: {c['n_l3_backed_by_l2']}/{c['n_l3_called']} L3 calls backed by a called L2")
    for r in rep["resolutions"]:
        mark = "HIT " if r["called"] else "miss"
        print(f'  {mark} L{r["order"]} {r["date"]} {r["fault_line"]:<14} '
              f'lead={r["reading_at_lead"]} event={r["reading_at_event"]}  {r["title"]}')
