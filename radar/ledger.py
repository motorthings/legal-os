"""Run-to-run harvester memory (Layer 0): the seen-index and the admission ledger.

Two durable structures let a new research run use what the last one already did:

  SeenIndex        — everything the KB already holds (radar/sources/feed.jsonl),
                     indexed by canonical URL, content hash, and citation. Answers
                     "have we already got this document?" so a candidate that is
                     already in the KB is never re-admitted.

  admissions.jsonl — every candidate a run ever DECIDED on (admit / quarantine /
                     dedup), with the reason. Answers "did a prior run already judge
                     this?" so we never re-evaluate — and a quarantined item stays
                     quarantined until explicitly promoted, instead of being
                     reconsidered on every run.

feed.jsonl records only admissions; the ledger records rejections too. Together they
are the harvester's memory. Both are append-only and human-readable (JSONL), matching
the legal-os auditability pillar.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import dedup
from score import load_feed, FEED_PATH

HISTORY = Path(__file__).parent / "history"
ADMISSIONS_FILE = HISTORY / "admissions.jsonl"


class SeenIndex:
    """What the KB already holds, indexed for O(1) identity checks."""

    def __init__(self, feed=None):
        if feed is None:
            feed = load_feed()
        self.urls = set()
        self.hashes = set()
        self.citations = set()
        for item in feed:
            self.add(item)

    def add(self, item):
        ident = dedup.identity(item)
        if ident["canonical_url"]:
            self.urls.add(ident["canonical_url"])
        self.hashes.add(ident["content_hash"])
        self.citations.update(ident["citations"])

    def seen(self, item):
        """Return a reason string if the KB already holds this document, else None.
        Checked strongest-identity first: identical content, then same permalink, then
        a shared citation (the same authority re-reported by another outlet).
          content_in_kb — byte-identical document (a true duplicate)
          url_in_kb     — same canonical URL (a re-fetch of the same permalink)
          citation_echo — same case citation at a different URL (an echo)"""
        ident = dedup.identity(item)
        if ident["content_hash"] in self.hashes:
            return "content_in_kb"
        if ident["canonical_url"] and ident["canonical_url"] in self.urls:
            return "url_in_kb"
        if any(c in self.citations for c in ident["citations"]):
            return "citation_echo"
        return None


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def run_id():
    """A timestamp-based run id for tagging ledger rows (not used in any score)."""
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")


def load_admissions():
    if not ADMISSIONS_FILE.exists():
        return []
    out = []
    for line in ADMISSIONS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def decided_keys():
    """Set of identity keys (canonical_url and content_hash) a prior run already
    decided on — so this run skips re-evaluating them regardless of the verdict."""
    keys = set()
    for row in load_admissions():
        if row.get("canonical_url"):
            keys.add(("url", row["canonical_url"]))
        if row.get("content_hash"):
            keys.add(("hash", row["content_hash"]))
    return keys


def already_decided(item, keys=None):
    """True iff a prior run recorded a decision for this document."""
    if keys is None:
        keys = decided_keys()
    ident = dedup.identity(item)
    if ident["canonical_url"] and ("url", ident["canonical_url"]) in keys:
        return True
    return ("hash", ident["content_hash"]) in keys


def record_decision(item, decision, reason, run=None, scores=None):
    """Append one immutable decision row to admissions.jsonl."""
    HISTORY.mkdir(exist_ok=True)
    ident = dedup.identity(item)
    row = {
        "ts": _iso_now(),
        "run": run or run_id(),
        "decision": decision,           # admit | quarantine | dedup
        "reason": reason,
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "url": item.get("url", ""),
        "canonical_url": ident["canonical_url"],
        "content_hash": ident["content_hash"],
        "citations": ident["citations"],
        "tier": item.get("tier"),
        "scores": scores or {},
    }
    with open(ADMISSIONS_FILE, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row
