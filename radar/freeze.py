"""Freeze fingerprint — a sha256 of the feed, seeds, and knobs, committed to git.

This is the "freeze now, hashed" step. Six months from now you recompute the fingerprint
(`python radar/freeze.py`) and compare it to the committed file: if it matches, the
out-of-sample calls were made with exactly these frozen inputs — no retro-fitting
possible. If it differs, the freeze was violated and the out-of-sample column is void.

Inputs hashed: the curated feed, the harvested store, and the three files that define the
forecast (fault_lines.py = taxonomy + seeds + KNOBS_FROZEN_AT, calibration.py = thresholds,
score.py = scoring math). Change any of them after freezing and the fingerprint breaks.
"""
import hashlib
import sys
from pathlib import Path

RADAR = Path(__file__).parent
INPUTS = [
    RADAR / "sources" / "feed.jsonl",
    RADAR / "sources" / "harvested.jsonl",
    RADAR / "fault_lines.py",
    RADAR / "calibration.py",
    RADAR / "score.py",
]
OUT = RADAR / "history" / "freeze_fingerprint.txt"


def fingerprint():
    h = hashlib.sha256()
    for p in INPUTS:
        if p.exists():
            h.update(p.name.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


def main():
    fp = fingerprint()
    OUT.write_text(fp + "\n")
    print(fp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
