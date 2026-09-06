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


def _pressure_for(fault_id, as_of):
    data = score(as_of=as_of)
    for fl in data["fault_lines"]:
        if fl["id"] == fault_id:
            return fl["pressure"], fl["trend"], fl["n_evidence"]
    return None, None, 0


def backtest(feed=None):
    """Replay the engine before each resolution landed. Returns results + hit rate."""
    results = []
    for r in load_resolutions():
        d = _parse_date(r["date"])
        lead_date = d - timedelta(days=LEAD_DAYS)
        p_lead, trend_lead, n_lead = _pressure_for(r["fault_line"], lead_date.isoformat())
        p_event, _, _ = _pressure_for(r["fault_line"], r["date"])
        called = p_lead is not None and p_lead >= CALL_THRESHOLD
        results.append({
            "date": r["date"], "fault_line": r["fault_line"], "title": r["title"],
            "url": r.get("url", ""),
            "pressure_at_lead": p_lead, "trend_at_lead": trend_lead, "evidence_at_lead": n_lead,
            "pressure_at_event": p_event,
            "lead_days": LEAD_DAYS, "called": called,
        })
    n = len(results)
    hits = sum(1 for x in results if x["called"])
    return {
        "resolutions": results,
        "n_resolutions": n,
        "hits": hits,
        "hit_rate": round(hits / n, 2) if n else None,
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
    print(f"Hit rate: {rep['hit_rate']} ({rep['hits']}/{rep['n_resolutions']}) "
          f"@ threshold {rep['call_threshold']}, {rep['lead_days']}d lead")
    for r in rep["resolutions"]:
        mark = "HIT " if r["called"] else "miss"
        print(f'  {mark} {r["date"]} {r["fault_line"]:<18} '
              f'lead={r["pressure_at_lead"]} event={r["pressure_at_event"]}  {r["title"]}')
