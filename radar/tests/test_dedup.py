"""Fixture tests for the Layer-0 run-to-run dedup memory.

Proves the four properties the harvester's memory must have:
  1. idempotency      — running twice admits a candidate once
  2. KB skip          — a URL already in the KB is never re-admitted
  3. echo dedup       — the same ruling at a different URL (shared citation) collapses
  4. sticky quarantine — a quarantined candidate is not reconsidered next run

Runs with pytest or standalone: `python radar/tests/test_dedup.py`.
No network, no embeddings — pure Layer 0.
"""
import json
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import dedup
import ledger
import ingest


def _setup(tmp_path, kb_items):
    """Point the feed + admission ledger at temp files and seed the KB."""
    feed = tmp_path / "feed.jsonl"
    feed.write_text("".join(json.dumps(i) + "\n" for i in kb_items))
    ledger.ADMISSIONS_FILE = tmp_path / "admissions.jsonl"
    ledger.HISTORY = tmp_path
    return feed


def _count_feed(feed):
    return len([l for l in feed.read_text().splitlines() if l.strip()])


# --- dedup.py unit checks ---------------------------------------------------

def test_canonical_url_strips_tracking_and_sorts():
    a = dedup.canonical_url("https://www.Courtlistener.com/x/?utm_source=nl&b=2&a=1#frag")
    b = dedup.canonical_url("http://courtlistener.com/x?a=1&b=2")
    assert a == b, (a, b)


def test_content_hash_ignores_whitespace_and_case():
    h1 = dedup.content_hash({"title": "A  Ruling", "text": "Sanctions  ordered."})
    h2 = dedup.content_hash({"title": "a ruling", "text": "sanctions ordered."})
    assert h1 == h2


def test_extract_citations_finds_reporter_and_docket():
    cites = dedup.extract_citations(
        {"title": "Couvrette v. Wisnovsky", "text": "See 678 F. Supp. 3d 443 (No. 22-1461)."})
    assert any("f. supp" in c for c in cites), cites


# --- pipeline behavior ------------------------------------------------------

def test_kb_skip_and_idempotency(tmp_path):
    kb = [{"date": "2023-06-22", "tier": "T1", "title": "Mata v. Avianca",
           "url": "https://courtlistener.com/mata", "text": "Rule 11 sanctions.",
           "fault_lines": ["disclosure"]}]
    feed = _setup(tmp_path, kb)
    cand = {"date": "2024-01-01", "title": "Mata v. Avianca (reprint)",
            "url": "https://www.courtlistener.com/mata?utm_source=x",
            "text": "Rule 11 sanctions.", "tier": "T1"}
    r1 = ingest.admit([cand], feed_path=feed)
    assert r1["admitted"] == 0 and r1["skipped_in_kb"] == 1
    assert _count_feed(feed) == 1  # unchanged
    # run again — still idempotent
    r2 = ingest.admit([cand], feed_path=feed)
    assert r2["skipped_decided"] + r2["skipped_in_kb"] == 1
    assert _count_feed(feed) == 1


def test_admit_new_then_dedupe_same_batch(tmp_path):
    feed = _setup(tmp_path, [])
    new = {"date": "2026-09-01", "title": "New sanction over hallucinated cites",
           "url": "https://courtlistener.com/newcase", "text": "Verification duty. 999 F.3d 1.",
           "tier": "T1", "fault_lines": ["verification"]}
    dup = {**new, "url": "https://lawnext.com/newcase-writeup",
           "title": "Court sanctions lawyer (writeup)"}  # different url+title, SAME citation
    r = ingest.admit([new, dup], feed_path=feed)
    assert r["admitted"] == 1, r
    assert r["skipped_in_kb"] == 1  # the echo collapsed via shared citation
    assert _count_feed(feed) == 1


def test_unknown_source_quarantined_and_sticky(tmp_path):
    feed = _setup(tmp_path, [])
    cand = {"date": "2026-09-01", "title": "Random blog take",
            "url": "https://somerandomblog.example/post", "text": "AI opinions.",
            "fault_lines": ["verification"]}
    r1 = ingest.admit([cand], feed_path=feed)
    assert r1["quarantined"] == 1 and r1["admitted"] == 0
    # next run: prior decision remembered, not re-evaluated
    r2 = ingest.admit([cand], feed_path=feed)
    assert r2["skipped_decided"] == 1 and r2["quarantined"] == 0


def test_irrelevant_candidate_quarantined(tmp_path):
    feed = _setup(tmp_path, [])
    cand = {"date": "2026-09-01", "title": "Unrelated tax ruling",
            "url": "https://courtlistener.com/tax", "text": "Estate tax basis rules.",
            "tier": "T1"}
    r = ingest.admit([cand], feed_path=feed)
    assert r["quarantined"] == 1 and r["admitted"] == 0


if __name__ == "__main__":
    import tempfile, traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            if t.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as d:
                    t(Path(d))
            else:
                t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
