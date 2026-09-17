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


def one_pass(do_ingest=False, trace=False):
    import ingest
    # Always-on run-to-run dedup memory: enforce KB integrity on EVERY pass, harvest
    # or not, so the seen-memory is part of the OS and duplicates never accrue silently.
    recon = ingest.reconcile_kb()
    log("kb_reconciled", n_items=recon["n_items"],
        duplicates=recon["n_duplicates"], shared_source=recon["n_shared_source"])
    for d in recon["duplicates"]:   # true content dupes — surface loudly
        log("kb_duplicate", title=d["title"][:80], reason=d["reason"])
    # Layer 3: refresh earned source-reliability from OUT-OF-SAMPLE presages only, then
    # the scorer reads the updated ledger. Dormant (all multipliers 1.0) until forward
    # rulings accrue, so scoring is unchanged today.
    import reliability
    rel = reliability.refresh()
    log("reliability", boosted=rel["n_boosted"],
        out_of_sample_rulings=rel["out_of_sample_resolutions"])
    if do_ingest:
        try:
            s = ingest.harvest_and_admit()
            log("ingest", live=s["live"], candidates=s["n_candidates"],
                admitted=s["admitted"], deduped=s["skipped_in_kb"],
                quarantined=s["quarantined"], sources=s["sources_allowlisted"])
            if not s["live"]:
                log("ingest_offline", reason="RADAR_LIVE_FETCH not set; no network calls")
        except Exception as e:  # network fetchers optional; never block the page build
            log("ingest_skipped", reason=str(e))
    from build import build
    import calibration
    data = build()
    bt = calibration.report()   # recall backtest + precision + seed ablation + holdout
    n_snaps = calibration.snapshot(data)
    # Run artifacts are OFF by default (2026-09-17). They are write-only — nothing in the
    # repo reads them — and each one re-embeds the full evidence set and weight math, so a
    # single afternoon of work added 47k lines and 4 MB. `--trace` writes one when a
    # replayable record of a specific run is actually wanted. The writer in calibration.py
    # is untouched: that file is a frozen input, and this decision should not cost a
    # re-freeze.
    artifact = calibration.write_run_artifact(data, bt) if trace else None
    rising = [f["title"] for f in data["fault_lines"] if f["trend"] == "rising"]
    log("built", n_items=data["n_items"], n_fault_lines=len(data["fault_lines"]),
        as_of=data["as_of"], rising=len(rising),
        hit_rate=bt["hit_rate"], snapshots=n_snaps,
        artifact=artifact or "not traced (pass --trace)")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, metavar="MIN",
                    help="repeat every N minutes (local background mode)")
    ap.add_argument("--ingest", action="store_true", help="run harvester + admission gate")
    ap.add_argument("--trace", action="store_true",
                    help="also write an immutable run artifact to history/runs/ (off by "
                         "default; nothing reads these, and each re-embeds the full evidence set)")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))  # allow flat imports in CI

    if args.watch:
        log("watch_start", interval_min=args.watch)
        while True:
            one_pass(do_ingest=args.ingest, trace=args.trace)
            time.sleep(args.watch * 60)
    else:
        one_pass(do_ingest=args.ingest, trace=args.trace)


if __name__ == "__main__":
    main()
