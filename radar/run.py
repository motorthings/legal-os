"""Radar entrypoint.

  python radar/run.py            # one pass: (ingest) -> score -> regenerate page
  python radar/run.py --watch 30 # background: repeat every 30 minutes (local)
  python radar/run.py --ingest   # also run the harvester/admission gate (phase 2)

In CI (GitHub Actions) we run the one-pass form on a schedule and commit the page.
Logging is structured JSONL to radar/logs/ per the legal-os auditability pillar.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def log(event, **fields):
    LOG_DIR.mkdir(exist_ok=True)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    with open(LOG_DIR / "radar.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"[{rec['ts']}] {event} " + " ".join(f"{k}={v}" for k, v in fields.items()))


def one_pass(do_ingest=False):
    if do_ingest:
        try:
            from ingest import harvest_and_admit
            admitted = harvest_and_admit()
            log("ingest", admitted=admitted)
        except Exception as e:  # ingestion is optional; never block the page build
            log("ingest_skipped", reason=str(e))
    from build import build
    import calibration
    data = build()
    bt = calibration.backtest()
    n_snaps = calibration.snapshot(data)
    artifact = calibration.write_run_artifact(data, bt)
    rising = [f["title"] for f in data["fault_lines"] if f["trend"] == "rising"]
    log("built", n_items=data["n_items"], n_fault_lines=len(data["fault_lines"]),
        as_of=data["as_of"], rising=len(rising),
        hit_rate=bt["hit_rate"], snapshots=n_snaps, artifact=artifact)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, metavar="MIN",
                    help="repeat every N minutes (local background mode)")
    ap.add_argument("--ingest", action="store_true", help="run harvester + admission gate")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))  # allow flat imports in CI

    if args.watch:
        log("watch_start", interval_min=args.watch)
        while True:
            one_pass(do_ingest=args.ingest)
            time.sleep(args.watch * 60)
    else:
        one_pass(do_ingest=args.ingest)


if __name__ == "__main__":
    main()
