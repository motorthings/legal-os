"""Live corpus — the refreshable half of the fork.

The frozen experiment grades a forecast against rulings that land after 2026-09-15, and
it can only do that if its inputs never move (`FREEZE.md`). A firm engagement needs the
opposite: a corpus that stays current, because the advisory answers "what does the record
already oblige us to do" and a stale record gives a stale answer. Those are two consumers
of one engine, so they read two corpora:

    experiment   sources/feed.jsonl + sources/harvested.jsonl        NEVER refreshed
    advisory     the experiment corpus + sources/feed_live.jsonl
                 + sources/harvested_live.jsonl                      refreshed freely

The advisory corpus is a SUPERSET: the curated feed is the base and live additions layer
on top. Nothing is copied, so the two corpora cannot drift apart in what they share, and
nothing frozen is ever written. `python radar/freeze.py` still prints the committed
fingerprint after any amount of advisory re-curation.

Freshness is not a prediction claim. It makes the advisory a better answer to a present
question. It does not make it a forecast, and it does not move the out-of-sample column.

Harvesting into the live store (offline by default, as everywhere else):

    RADAR_LIVE_FETCH=1 python radar/live.py --harvest
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from score import score, load_corpus, load_feed          # noqa: E402

LIVE_FEED_PATH = HERE / "sources" / "feed_live.jsonl"
LIVE_HARVESTED_PATH = HERE / "sources" / "harvested_live.jsonl"

REPO = HERE.parent
DOCS_JSON = REPO / "docs" / "radar" / "live.json"
FRONTEND_JSON = REPO / "frontend" / "public" / "radar" / "live.json"

# The frozen inputs. Named here so the guard below is explicit rather than a comment
# somebody has to remember: the live path must never touch these.
FROZEN_INPUTS = {HERE / "sources" / "feed.jsonl", HERE / "sources" / "harvested.jsonl"}


def _read(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def load_live():
    """Items added since the freeze, from the curated live file and the live harvested
    store. Both are optional; absent files mean the advisory runs on the curated feed
    alone, which is exactly how it behaves on day one."""
    out = []
    for path in (LIVE_FEED_PATH, LIVE_HARVESTED_PATH):
        for item in _read(path):
            item["live"] = True
            item.setdefault("harvested", path is LIVE_HARVESTED_PATH)
            out.append(item)
    return out


def live_corpus():
    """Curated feed (base) + live additions. The scorer is a pure function of this."""
    base = load_corpus()
    for item in base:
        item.setdefault("live", False)
    return base + load_live()


def freshness():
    """How current is the advisory corpus? A firm-facing run should be able to state the
    date of its newest evidence, so this is computed rather than assumed."""
    live = load_live()
    base = load_corpus()
    newest = max((i["date"] for i in base + live), default=None)
    newest_live = max((i["date"] for i in live), default=None)
    return {
        "n_curated": len(base),
        "n_live": len(live),
        "newest_evidence": newest,
        "newest_live_evidence": newest_live,
        "days_since_newest_live": ((date.today() - date.fromisoformat(newest_live)).days
                                   if newest_live else None),
    }


def _guard(paths):
    """Refuse to write into the frozen experiment's inputs."""
    for p in paths:
        if Path(p).resolve() in {f.resolve() for f in FROZEN_INPUTS}:
            raise RuntimeError(f"refusing to write a frozen input: {p}")


def build_live(as_of=None):
    """Score the live corpus and write the advisory landscape.

    Same scorer, same knobs, same determinism contract as the experiment. The only
    difference is which corpus it is handed.
    """
    corpus = live_corpus()
    data = score(feed=corpus, as_of=as_of)
    data["as_of"] = as_of or date.today().isoformat()
    data["n_items"] = len(corpus)
    data["freshness"] = freshness()
    data["corpus"] = "live (frozen curated feed + live additions)"
    _guard([DOCS_JSON, FRONTEND_JSON])
    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json.dumps(data, indent=2))
    if FRONTEND_JSON.parent.exists():
        FRONTEND_JSON.write_text(json.dumps(data, indent=2))
    return data


def landscape_path(prefer_live=True):
    """Which landscape the advisory should read. Prefers the live one when it exists,
    falls back to the frozen `data.json` so the advisory keeps working before the first
    live build."""
    frozen = REPO / "docs" / "radar" / "data.json"
    if prefer_live and DOCS_JSON.exists():
        return DOCS_JSON
    return frozen


def harvest_live(live=None):
    """Run the harvester + admission gate against the LIVE store only.

    `ingest.harvest_and_admit` already takes a target path, so the live path reuses the
    same allowlist, tier gate, and dedup memory as the frozen one. The difference is
    where the rows land: nothing a live harvest admits can reach `feed.jsonl` or
    `harvested.jsonl`, so the freeze holds no matter how often this runs.
    """
    _guard([LIVE_FEED_PATH, LIVE_HARVESTED_PATH])
    import ingest
    return ingest.harvest_and_admit(feed_path=LIVE_HARVESTED_PATH, live=live)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Build the live advisory corpus + landscape.")
    p.add_argument("--harvest", action="store_true",
                   help="run the harvester + admission gate into the LIVE store")
    a = p.parse_args()
    if a.harvest:
        print(json.dumps(harvest_live(), indent=2))
    data = build_live()
    f = data["freshness"]
    print(f"live landscape: {data['n_items']} items "
          f"({f['n_curated']} curated + {f['n_live']} live) -> {DOCS_JSON}")
    print(f"newest evidence: {f['newest_evidence']}"
          + (f" (newest live: {f['newest_live_evidence']}, "
             f"{f['days_since_newest_live']}d ago)" if f["newest_live_evidence"] else
             " — no live additions yet; advisory runs on the curated feed alone"))
