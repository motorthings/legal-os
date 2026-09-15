"""Report which fault lines need re-curation (stale or thin), for the weekly CI nudge.

Reads the already-regenerated data.json and prints a one-line summary to stdout. The CI
folds this into its commit message and opens a GitHub issue when the list is non-empty,
so the gap surfaces in git AND pings via GitHub notifications — instead of requiring a
human to open the app and read the Coverage column.

A line "needs re-curation" when it is stale (no new authority in >180 days) or thin
(<=2 of the 5 evidence lanes populated). Both are the honest signals that the duty has
not crystallized into law yet and a Descrybe pass may find nothing — still worth surfacing.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "docs" / "radar" / "data.json"


def needy_lines(data):
    out = []
    for f in data.get("fault_lines", []):
        stale_days = f.get("stale_days") or 0
        lanes = f.get("lanes_populated") or 0
        stale = stale_days > 180
        thin = lanes <= 2
        if not (stale or thin):
            continue
        why = []
        if stale:
            why.append(f"stale {stale_days}d")
        if thin:
            why.append(f"{lanes}/5 lanes")
        out.append(f"{f['id']} ({', '.join(why)})")
    return out


def main():
    if not DATA.exists():
        print("no radar data.json yet")
        return 0
    data = json.loads(DATA.read_text())
    needy = needy_lines(data)
    print("needs re-curation: " + ", ".join(needy) if needy else "all fault lines current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
