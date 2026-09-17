"""Report which fault lines need attention, for the weekly CI nudge.

Reads the LIVE landscape when one exists, falling back to the frozen data.json. This
matters more than it looks:

  The nudge used to read the frozen `data.json` while the re-curation skill wrote the
  frozen `feed.jsonl`, so the two agreed. After the 2026-09-17 fork, curation writes the
  LIVE corpus. Reading the frozen landscape would have made this a loop by construction:
  act on the nudge, change nothing it measures, get the same nudge next week forever.

A line needs attention when it is stale (no new authority in >180 days) or thin (<=2 of 5
lanes populated). The two are NOT the same problem and do not take the same fix:

  stale             -> case-law discovery (`/refresh-radar`) can resolve it
  thin on ruling    -> case-law discovery can resolve it
  thin on adoption  -> it usually cannot. Verified 2026-09-17: nine T1 orders admitted
                       across `disclosure` and `confidentiality` moved neither line off
                       2/5 lanes, because every item landed in the ruling lane, which was
                       already the populated one. Those lanes fill from market actors
                       (insurer / procurement / deployment), not from primary law.

So the report now says which fix applies. A thin-on-adoption line is often not a debt at
all: on 2026-09-17 the ACC/Everlaw survey showed 80% of in-house counsel neither require
nor encourage GenAI use by outside counsel and 59% do not know whether their firms use it,
so the empty adoption lane was an accurate reading rather than a curation gap. Where that
is the finding, mark the line reviewed rather than padding it.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "docs" / "radar" / "live.json"     # refreshable — what curation can change
FROZEN = REPO / "docs" / "radar" / "data.json"   # the experiment's landscape

# Lanes that primary-law discovery cannot fill: they need a market actor.
MARKET_LANES = ("adoption", "enable", "software")


def landscape_path():
    return LIVE if LIVE.exists() else FROZEN


def diagnose(f):
    """(needs_attention, why, fix) for one fault line."""
    stale_days = f.get("stale_days") or 0
    lanes = f.get("lanes_populated") or 0
    reviewed_days = f.get("reviewed_days")   # None if never reviewed
    stale = stale_days > 180
    thin = lanes <= 2
    # A line reviewed within 30 days is "checked, dormant" — not a re-curation gap.
    if (not (stale or thin)) or (reviewed_days is not None and reviewed_days <= 30):
        return False, "", ""

    populated = {k for k, v in (f.get("lanes") or {}).items() if v > 0}
    empty_market = [l for l in MARKET_LANES if l not in populated]
    why = []
    if stale:
        why.append(f"stale {stale_days}d")
    if thin:
        why.append(f"{lanes}/5 lanes")
    if thin and empty_market and "ruling" in populated:
        return (True, ", ".join(why),
                f"market discovery (empty: {'/'.join(empty_market)}) — case search will not move it")
    return True, ", ".join(why), "case-law discovery (/refresh-radar)"


def needy_lines(data):
    out = []
    for f in data.get("fault_lines", []):
        needs, why, fix = diagnose(f)
        if needs:
            out.append(f"{f['id']} ({why}) — {fix}")
    return out


def main():
    path = landscape_path()
    if not path.exists():
        print("no radar landscape yet")
        return 0
    data = json.loads(path.read_text())
    needy = needy_lines(data)
    print("needs re-curation: " + " | ".join(needy) if needy else "all fault lines current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
