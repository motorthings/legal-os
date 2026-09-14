"""Harvest preview — see what a live run WOULD do, before it does it.

The safe way to run the harvester for the first time (and every time). It fetches the
allowlisted sources and runs the full admission gate in dry-run: every candidate's
decision and reason is shown, and NOTHING is written — no feed append, no ledger row, no
change to the KB. So a preview can never poison the run it is meant to validate.

Usage:
    python radar/harvest_preview.py                # preflight + live fetch, preview (no writes)
    python radar/harvest_preview.py --offline      # no network: preview over built-in samples
    python radar/harvest_preview.py --file cands.json
    python radar/harvest_preview.py --json         # machine-readable preview

Then, when the preview looks right, run it for real:
    RADAR_LIVE_FETCH=1 python radar/run.py --ingest
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import ingest
import fetchers
import dedup
import ledger


def preflight():
    """Static checks before any network call. Returns (ok, [messages])."""
    problems = []
    # Every configured source must be allowlisted — otherwise it would be skipped at
    # fetch time and the run would silently harvest nothing.
    for src in fetchers.SOURCES:
        d = dedup.domain_of(src["url"])
        if d not in ingest.SOURCE_ALLOWLIST:
            problems.append(f"source domain not allowlisted: {d} ({src['name']})")
    # The stores must be writable.
    try:
        ledger.HISTORY.mkdir(exist_ok=True)
    except OSError as e:
        problems.append(f"cannot create ledger dir {ledger.HISTORY}: {e}")
    if not ingest.HARVESTED_PATH.parent.exists():
        problems.append(f"missing harvested dir: {ingest.HARVESTED_PATH.parent}")
    return (not problems), problems


def preview(live=True, candidates=None):
    """Fetch (unless candidates given) then run the admission gate in dry-run. Writes
    nothing. Returns the dispatch summary with live/source counts folded in."""
    if candidates is None:
        candidates = fetchers.harvest(live=live)
    summary = ingest.admit(candidates, dry_run=True)
    summary["live"] = bool(live)
    summary["sources_allowlisted"] = len(fetchers.SOURCES)
    return summary


# Built-in samples so `--offline` demonstrates the whole flow with no network.
_SAMPLE = [
    {"date": "2026-09-01", "title": "Court sanctions firm over fabricated AI citations",
     "url": "https://www.lawnext.com/2026/09/ai-sanction.html",
     "text": "The order requires disclosure of AI use and a verification record.",
     "source": "LawSites"},
    {"date": "2026-09-02", "title": "Vendor launches new AI drafting tool",
     "url": "https://www.artificiallawyer.com/2026/09/tool.html",
     "text": "A product announcement.", "source": "Artificial Lawyer"},
    {"date": "2026-09-03", "title": "Off-allowlist aggregator post",
     "url": "https://not-allowlisted.example/post", "text": "disclosure", "source": "?"},
]


def _render(summary, problems):
    if problems:
        print("PREFLIGHT FAILED:")
        for p in problems:
            print(f"  - {p}")
        print()
    print(f"live={summary['live']}  sources_allowlisted={summary['sources_allowlisted']}  "
          f"candidates={summary['n_candidates']}  (dry run — nothing written)")
    print(f"  would admit:      {summary['admitted']}")
    print(f"  already in KB:    {summary['skipped_in_kb']}")
    print(f"  already decided:  {summary['skipped_decided']}")
    print(f"  quarantined:      {summary['quarantined']}")
    if not summary["decisions"]:
        print("\n  (no candidates — check RADAR_LIVE_FETCH / source reachability)")
        return
    print("\n  decisions:")
    for d in summary["decisions"]:
        mark = {"admit": "ADMIT ", "dedup": "dupe  ", "quarantine": "QUAR ",
                "skip": "skip  "}.get(d["decision"], d["decision"])
        print(f"    {mark} {d['reason']:<22} {d['title'][:68]}")
    reasons = Counter(d["reason"] for d in summary["decisions"])
    print("\n  reason tally: " + ", ".join(f"{r}={n}" for r, n in reasons.most_common()))


def main():
    ap = argparse.ArgumentParser(description="Preview a harvest run without writing anything.")
    ap.add_argument("--offline", action="store_true",
                    help="no network: preview over built-in samples")
    ap.add_argument("--file", help="read candidates from this JSON file (implies offline)")
    ap.add_argument("--json", action="store_true", help="emit the preview as JSON")
    ap.add_argument("--no-preflight", action="store_true", help="skip the preflight check")
    args = ap.parse_args()

    ok, problems = preflight()
    if problems and not args.json:
        # A preflight failure is informational here (the preview writes nothing), but it
        # predicts a real run would harvest nothing, so surface it loudly.
        pass

    if args.file:
        summary = preview(live=False, candidates=json.loads(Path(args.file).read_text()))
    elif args.offline:
        summary = preview(live=False, candidates=_SAMPLE)
    else:
        summary = preview(live=True)

    if args.json:
        print(json.dumps({"preflight_ok": ok, "preflight_problems": problems,
                          **summary}, indent=2))
    else:
        _render(summary, problems)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
