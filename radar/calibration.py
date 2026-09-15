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
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from score import score, load_feed, _parse_date, FEED_PATH
import fault_lines as K
from fault_lines import KNOBS_FROZEN_AT

HISTORY = Path(__file__).parent / "history"
SNAP_FILE = HISTORY / "snapshots.jsonl"
RES_FILE = HISTORY / "resolutions.jsonl"
SWRES_FILE = HISTORY / "software_resolutions.jsonl"
RUNS_DIR = HISTORY / "runs"

CALL_THRESHOLD = 9.0   # pressure at/above this = the fault line was "flagged". Raised from
                        # 7.0 (2026-09-15): at 7.0 the engine flagged ~83% of lines — a "forecast"
                        # that calls almost everything is not discriminating. 9.0 flags only the
                        # genuinely-hot lines so a flag is a rare, meaningful signal.
LEAD_DAYS = 90         # how far before the event we replay the engine

SOFTWARE_CALL_THRESHOLD = 6.0   # software momentum at/above this = the build move was flagged
SOFTWARE_LEAD_DAYS = 90         # how far before the build milestone we replay


def _knobs():
    """The exact scoring configuration, captured for replay."""
    return {
        "tier_weights": {t: v["weight"] for t, v in K.SOURCE_TIERS.items()},
        "conflict_discount": K.CONFLICT_DISCOUNT,
        "empirical_boost": K.EMPIRICAL_BOOST,
        "corroboration_step": K.CORROBORATION_STEP,
        "corroboration_cap": K.CORROBORATION_CAP,
        "ruling_tiers": sorted(K.RULING_TIERS),
        "knobs_frozen_at": K.KNOBS_FROZEN_AT,
        "half_life_days": K.HALF_LIFE_DAYS,
        "standing_tiers": sorted(K.STANDING_TIERS),
        "market_weights": K.MARKET_WEIGHTS,
        "adoption_seeds": K.ADOPTION_SEEDS,
        "capability_weights": K.CAPABILITY_WEIGHTS,
        "capability_seeds": K.CAPABILITY_SEEDS,
        "enable_weights": K.ENABLE_WEIGHTS,
        "enable_seeds": K.ENABLE_SEEDS,
        "software_weights": K.SOFTWARE_WEIGHTS,
        "software_seeds": K.SOFTWARE_SEEDS,
        "software_half_life": K.SOFTWARE_HALF_LIFE,
        "software_flag_multiplier": K.FLAG_MULTIPLIER,
        "call_threshold": CALL_THRESHOLD,
        "lead_days": LEAD_DAYS,
        "reliability_ledger_sha256": _reliability_ledger_hash(),
    }


def _reliability_ledger_hash():
    """Hash of the earned-reliability ledger the scorer read, for exact replay."""
    try:
        import reliability
        return reliability.ledger_hash()
    except Exception:
        return None


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
_EV_KEY = {"capability": "n_capability_evidence", "pressure": "n_ruling_evidence",
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
        # Forward-only holdout: an event on/before the freeze is retrodiction (the knobs,
        # seeds, and feed were authored knowing it happened); only events AFTER the freeze
        # are an out-of-sample forecast track record.
        sample = "in_sample" if r["date"] <= KNOBS_FROZEN_AT else "out_of_sample"
        results.append({
            "date": r["date"], "order": order, "fault_line": r["fault_line"],
            "title": r["title"], "url": r.get("url", ""),
            "meter": _METER.get(order, "pressure"),
            "reading_at_lead": v_lead, "evidence_at_lead": n_lead,
            "reading_at_event": v_event,
            "lead_days": LEAD_DAYS, "called": called, "sample": sample,
        })

    def _rate(rows):
        n = len(rows); h = sum(1 for x in rows if x["called"])
        return {"n": n, "hits": h, "hit_rate": round(h / n, 2) if n else None}

    by_order = {o: _rate([x for x in results if x["order"] == o])
                for o in sorted({x["order"] for x in results})}
    by_sample = {s: _rate([x for x in results if x["sample"] == s])
                 for s in ("in_sample", "out_of_sample")}

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
        "by_sample": by_sample,
        "knobs_frozen_at": KNOBS_FROZEN_AT,
        "cascade": cascade,
        "conditionals": {"L1_to_L2": l1_to_l2, "L2_to_L3": l2_to_l3},
        "call_threshold": CALL_THRESHOLD,
        "lead_days": LEAD_DAYS,
    }


def software_backtest(feed=None):
    """Grade the software-capability lane (S) against its own build milestones.

    The S lane is a forward momentum signal (what vendors are enabled to build next),
    so it is graded differently from a ruling forecast: for each dated build milestone
    (a funding round, an acquisition, an agentic-tool shipment), we replay the engine
    `SOFTWARE_LEAD_DAYS` before it landed and check whether the S meter on the relevant
    fault line was already elevated. "Called" = the momentum signal pointed the right
    way early. This is the honest answer to "would it have gotten last year's moves
    right" — a forward signal that cannot be graded this way is just a vibe.
    """
    if not SWRES_FILE.exists():
        return {"milestones": [], "n": 0, "hits": 0, "hit_rate": None,
                "threshold": SOFTWARE_CALL_THRESHOLD, "lead_days": SOFTWARE_LEAD_DAYS}
    rows = []
    for r in _load_jsonl(SWRES_FILE):
        d = _parse_date(r["date"])
        lead_date = d - timedelta(days=SOFTWARE_LEAD_DAYS)
        v_lead = _software_reading(r["fault_line"], lead_date.isoformat())
        v_event = _software_reading(r["fault_line"], r["date"])
        called = v_lead is not None and v_lead >= SOFTWARE_CALL_THRESHOLD
        rows.append({
            "date": r["date"], "fault_line": r["fault_line"], "title": r["title"],
            "url": r.get("url", ""),
            "reading_at_lead": v_lead, "reading_at_event": v_event,
            "lead_days": SOFTWARE_LEAD_DAYS, "called": called,
        })
    n = len(rows)
    hits = sum(1 for x in rows if x["called"])
    return {"milestones": rows, "n": n, "hits": hits,
            "hit_rate": round(hits / n, 2) if n else None,
            "threshold": SOFTWARE_CALL_THRESHOLD, "lead_days": SOFTWARE_LEAD_DAYS}


def _software_reading(fault_id, as_of):
    data = score(as_of=as_of)
    for fl in data["fault_lines"]:
        if fl["id"] == fault_id:
            return fl.get("software")
    return None


def _load_jsonl(path):
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def precision_report(step_days=30, window_days=None):
    """The false-positive side of the ledger the recall backtest can't see.

    The `backtest()` above answers "of the rulings that landed, how many did we flag?"
    (recall). It cannot answer "of everything we flagged, how much produced a ruling?"
    (precision) — a model that pins every line high scores perfect recall and is useless.

    This builds a (fault_line × month) grid over the feed's lifespan and, for the ruling
    lane (order 2), scores every cell:
      - flagged  = the L2 meter was >= CALL_THRESHOLD on that date
      - positive = an order-2 resolution for that line lands within the next window_days
      -> precision, recall, flag_rate, base_rate, and LIFT (precision / base_rate).
    Lift <= 1 means the flags carry no skill over flagging blindly. With sparse ground
    truth (few curated resolutions) precision is expected to be low; that is the honest
    finding, reported rather than hidden behind a recall number.
    """
    if window_days is None:
        window_days = LEAD_DAYS
    res = [r for r in load_resolutions() if r.get("order", 2) == 2]
    if not res:
        return {"n_cells": 0, "note": "no order-2 resolutions to grade precision against"}
    fault_ids = [fl["id"] for fl in K.FAULT_LINES]
    res_dates = [_parse_date(r["date"]) for r in res]
    start = min(res_dates) - timedelta(days=window_days)
    end = date.today()

    # grid of as_of dates
    grid = []
    d = start
    while d <= end:
        grid.append(d)
        d += timedelta(days=step_days)

    positives_by_line = {}
    for r in res:
        positives_by_line.setdefault(r["fault_line"], []).append(_parse_date(r["date"]))

    tp = fp = fn = tn = 0
    pos_cells = 0
    for as_of in grid:
        data = score(as_of=as_of.isoformat())
        reading = {fl["id"]: fl["pressure"] for fl in data["fault_lines"]}
        for fid in fault_ids:
            flagged = reading.get(fid, 0) >= CALL_THRESHOLD
            positive = any(as_of < pd <= as_of + timedelta(days=window_days)
                           for pd in positives_by_line.get(fid, []))
            pos_cells += 1 if positive else 0
            if flagged and positive: tp += 1
            elif flagged and not positive: fp += 1
            elif not flagged and positive: fn += 1
            else: tn += 1

    n_cells = tp + fp + fn + tn
    precision = round(tp / (tp + fp), 2) if (tp + fp) else None
    recall = round(tp / (tp + fn), 2) if (tp + fn) else None
    flag_rate = round((tp + fp) / n_cells, 2) if n_cells else None
    base_rate = round(pos_cells / n_cells, 3) if n_cells else None
    lift = round(precision / base_rate, 2) if (precision and base_rate) else None
    return {
        "grid": {"step_days": step_days, "window_days": window_days,
                 "start": start.isoformat(), "end": end.isoformat(),
                 "n_dates": len(grid), "n_lines": len(fault_ids), "n_cells": n_cells},
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall,
        "flag_rate": flag_rate, "base_rate": base_rate, "lift": lift,
        "threshold": CALL_THRESHOLD,
    }


def seed_ablation():
    """Isolate how much of the backtest 'calls' come from evidence vs the analyst seeds.

    Re-runs the point-in-time backtest with every seed neutralized to NEUTRAL_SEED. If the
    neutral-seed hit rate collapses relative to default seeds, the calls were seed-driven,
    not earned by evidence. Deterministic: same feed, same knobs, seeds swapped only.
    """
    def _hits(seeds):
        rows = []
        for r in load_resolutions():
            order = r.get("order", 2)
            meter = _METER.get(order, "pressure")
            lead_date = (_parse_date(r["date"]) - timedelta(days=LEAD_DAYS)).isoformat()
            data = score(as_of=lead_date, seeds=seeds)
            v = next((fl.get(meter) for fl in data["fault_lines"]
                      if fl["id"] == r["fault_line"]), None)
            rows.append(v is not None and v >= CALL_THRESHOLD)
        n = len(rows); h = sum(rows)
        return {"n": n, "hits": h, "hit_rate": round(h / n, 2) if n else None}

    default = _hits("default")
    neutral = _hits("neutral")
    return {
        "default_seeds": default,
        "neutral_seeds": neutral,
        "seed_dependence": (None if default["hit_rate"] is None
                            else round(default["hit_rate"] - neutral["hit_rate"], 2)),
        "neutral_seed": K.NEUTRAL_SEED,
        "note": ("hits lost when seeds are neutralized = calls that rested on the analyst "
                 "baseline rather than on point-in-time evidence"),
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
    """Bundle for the page: recall backtest + precision + seed ablation + snapshots."""
    bt = backtest()
    n_snaps = 0
    if SNAP_FILE.exists():
        n_snaps = len([l for l in SNAP_FILE.read_text().splitlines() if l.strip()])
    return {**bt, "precision": precision_report(), "seed_ablation": seed_ablation(),
            "snapshots_recorded": n_snaps}


if __name__ == "__main__":
    rep = report()
    print(f"Overall recall: {rep['hit_rate']} ({rep['hits']}/{rep['n_resolutions']}) "
          f"@ threshold {rep['call_threshold']}, {rep['lead_days']}d lead")
    for o, s in rep["by_order"].items():
        print(f"  L{o} ({K.ORDERS[o]['name']}): {s['hit_rate']} ({s['hits']}/{s['n']})")
    print(f"\nForward-only holdout (knobs frozen {rep['knobs_frozen_at']}):")
    for s, lbl in (("in_sample", "in-sample (RETRODICTION — not a track record)"),
                   ("out_of_sample", "out-of-sample (real forecast track record)")):
        st = rep["by_sample"][s]
        print(f"  {lbl}: {st['hit_rate']} ({st['hits']}/{st['n']})")
    pr = rep["precision"]
    if pr.get("grid"):
        print(f"\nPrecision / base-rate (L2 ruling lane, {pr['grid']['n_cells']} cells):")
        print(f"  precision={pr['precision']} recall={pr['recall']} "
              f"flag_rate={pr['flag_rate']} base_rate={pr['base_rate']} LIFT={pr['lift']}")
        print(f"  TP={pr['tp']} FP={pr['fp']} FN={pr['fn']} TN={pr['tn']}  "
              f"(lift<=1 => flags carry no skill over flagging blindly)")
    ab = rep["seed_ablation"]
    print(f"\nSeed ablation: default={ab['default_seeds']['hit_rate']} "
          f"neutral={ab['neutral_seeds']['hit_rate']} "
          f"seed_dependence={ab['seed_dependence']} "
          f"(hits that rest on the seed, not evidence)")
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
