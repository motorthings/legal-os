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


def check():
    """Compare the current fingerprint to the committed one WITHOUT rewriting it.

    Writing on every run would erase the evidence: a violation would overwrite the
    committed baseline with the new hash and look identical to a clean run. Verification
    must never mutate the thing it is verifying, so --check is read-only and exits
    non-zero on a mismatch (CI uses that to fail loudly rather than commit quietly).
    """
    current = fingerprint()
    committed = OUT.read_text().strip() if OUT.exists() else ""
    if not committed:
        print(f"no committed fingerprint at {OUT}; run `python radar/freeze.py` to set it")
        return 1
    if current == committed:
        print(f"FREEZE HELD {current}")
        return 0
    print(f"FREEZE VIOLATED\n  committed {committed}\n  current   {current}\n"
          f"  a frozen input changed; the out-of-sample column is void unless this was "
          f"a deliberate re-freeze (which must bump KNOBS_FROZEN_AT and record why)")
    return 1


def main(argv=None):
    import sys as _sys
    argv = argv if argv is not None else _sys.argv[1:]
    if "--check" in argv:
        return check()
    fp = fingerprint()
    OUT.write_text(fp + "\n")
    print(fp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
