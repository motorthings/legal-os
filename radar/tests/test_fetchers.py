"""Fixture tests for the fetcher layer — parsers and the offline safety posture.

No network. Recorded source samples prove the parse -> candidate -> admit path, and the
allowlist boundary is tested directly (a non-allowlisted domain is refused before any
request). Runs with pytest or standalone: `python radar/tests/test_fetchers.py`.
"""
import json
import sys
import tempfile
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import fetchers
import ingest
import ledger

RSS_SAMPLE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Court sanctions lawyer over fabricated AI citations</title>
    <link>https://www.lawnext.com/2026/09/ai-sanction.html?utm_source=feed</link>
    <pubDate>Mon, 07 Sep 2026 10:00:00 +0000</pubDate>
    <description>&lt;p&gt;A judge ordered sanctions, requiring &lt;b&gt;disclosure&lt;/b&gt; of AI use.&lt;/p&gt;</description>
  </item>
  <item>
    <title>No date item</title>
    <link>https://www.lawnext.com/2026/09/nodate.html</link>
    <description>skipped</description>
  </item>
</channel></rss>"""

ATOM_SAMPLE = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Bar opinion on verification duties</title>
    <link href="https://www.artificiallawyer.com/2026/08/verification/"/>
    <updated>2026-08-15T09:00:00Z</updated>
    <summary>New guidance on verification and audit trail for AI work.</summary>
  </entry>
</feed>"""

CL_SAMPLE = json.dumps({"results": [
    {"caseName": "Couvrette v. Wisnovsky",
     "absolute_url": "/opinion/12345/couvrette-v-wisnovsky/",
     "dateFiled": "2025-12-15", "citation": ["114 A.D.3d 947"],
     "snippet": "<p>Sanctions for <b>verification</b> failures.</p>"}
]}).encode()


# --- parsers ----------------------------------------------------------------

def test_parse_rss_titles_links_dates():
    entries = fetchers.parse_rss(RSS_SAMPLE)
    assert len(entries) == 2
    e = entries[0]
    assert "sanctions" in e["title"]
    assert e["link"].startswith("https://www.lawnext.com/")
    assert e["date"].startswith("Mon, 07 Sep 2026")
    assert "<b>" not in e["summary"]  # html stripped


def test_parse_atom():
    entries = fetchers.parse_rss(ATOM_SAMPLE)
    assert len(entries) == 1
    assert entries[0]["link"].endswith("/verification/")


def test_parse_courtlistener():
    entries = fetchers.parse_courtlistener(CL_SAMPLE)
    assert len(entries) == 1
    e = entries[0]
    assert e["title"] == "Couvrette v. Wisnovsky"
    assert e["link"].startswith("https://www.courtlistener.com/opinion/")
    assert e["date"] == "2025-12-15"


# --- candidate shaping ------------------------------------------------------

def test_to_candidate_normalizes_date_and_omits_tier():
    entries = fetchers.parse_rss(RSS_SAMPLE)
    cand = fetchers.to_candidate(entries[0], {"name": "LawSites"})
    assert cand["date"] == "2026-09-07"          # RFC822 -> ISO
    assert cand["source"] == "LawSites"
    assert "tier" not in cand                    # allowlist assigns tier, never the source


def test_to_candidate_skips_missing_date():
    entries = fetchers.parse_rss(RSS_SAMPLE)
    assert fetchers.to_candidate(entries[1], {"name": "LawSites"}) is None


# --- safety posture ---------------------------------------------------------

def test_harvest_offline_by_default_makes_no_calls():
    assert fetchers.harvest(live=False) == []


def test_allowlist_refuses_unknown_domain_before_request():
    bad = {"name": "Sketchy", "url": "https://not-allowlisted.example/feed", "kind": "rss"}
    # fetch on a non-allowlisted domain is refused (no request is attempted)
    try:
        fetchers._fetch(bad["url"])
        assert False, "should have refused"
    except PermissionError:
        pass
    # and harvest() drops it silently
    assert fetchers.harvest(live=True, sources=[bad]) == []


def test_fixture_candidate_flows_through_admit(tmp_path):
    """End-to-end, offline: a parsed fixture candidate clears the gate and lands in the
    harvested store (never the curated feed)."""
    harvested = tmp_path / "harvested.jsonl"
    ledger.ADMISSIONS_FILE = tmp_path / "admissions.jsonl"
    ledger.HISTORY = tmp_path
    entries = fetchers.parse_rss(RSS_SAMPLE)
    cand = fetchers.to_candidate(entries[0], {"name": "LawSites"})
    # lawnext.com is already allowlisted as T4; attribute to a fault line so it clears
    # the relevance gate.
    cand["fault_lines"] = ["disclosure"]
    r = ingest.admit([cand], feed_path=harvested, seen_feed=[])
    assert r["admitted"] == 1, r
    rows = [json.loads(l) for l in harvested.read_text().splitlines() if l.strip()]
    assert rows[0]["harvested"] is True          # provenance marked
    assert rows[0]["tier"] == "T4"               # tier from the allowlist


def test_auth_header_only_when_token_set(monkeypatch=None):
    """Anonymous by default; the token is sent only when its env var is set."""
    import os
    os.environ.pop("COURTLISTENER_TOKEN", None)
    assert fetchers._auth_headers("https://www.courtlistener.com/api/rest/v4/search/") == {}
    assert fetchers._auth_headers("https://www.lawnext.com/feed/") == {}   # no token mapping
    os.environ["COURTLISTENER_TOKEN"] = "abc123"
    h = fetchers._auth_headers("https://www.courtlistener.com/api/rest/v4/search/")
    assert h == {"Authorization": "Token abc123"}, h   # 'Token' word is required
    os.environ.pop("COURTLISTENER_TOKEN", None)


def test_harvest_report_offline_is_empty():
    assert fetchers.harvest_report(live=False) == []


def test_harvest_report_flags_unallowlisted_source():
    """An unlisted domain is reported as a failed source, not silently dropped — so a
    preview can say WHY a source produced nothing."""
    bad = {"name": "Sketchy", "url": "https://nope.example/feed", "kind": "rss"}
    rep = fetchers.harvest_report(live=True, sources=[bad])
    assert len(rep) == 1
    assert rep[0]["ok"] is False
    assert rep[0]["error"] == "domain_not_allowlisted"
    assert rep[0]["n_candidates"] == 0


# --- AI-context relevance gate ----------------------------------------------

def test_ai_context_gate_word_boundaries():
    assert ingest._has_ai_context({"title": "AI disclosure in briefs", "text": ""})
    assert ingest._has_ai_context({"title": "", "text": "a generative AI tool was used"})
    assert not ingest._has_ai_context({"title": "", "text": "the witness said disclosure"})
    # "ai" inside another word must not fire the gate
    assert not ingest._has_ai_context({"title": "party claimed relief", "text": ""})


def test_uncurated_item_requires_ai_context():
    """A generic legal word without AI context no longer admits; AI context does."""
    generic = {"date": "2026-09-01", "title": "Discovery dispute",
               "url": "https://www.lawnext.com/a.html",
               "text": "The court ordered disclosure of documents.", "source": "x"}
    assert ingest._relevant_fault_lines(generic) == []   # "disclosure" but not about AI
    ai_item = {"date": "2026-09-01", "title": "Court sanctions firm over AI citations",
               "url": "https://www.lawnext.com/b.html",
               "text": "Disclosure of generative AI use is required.",
               "source": "x"}
    assert ingest._relevant_fault_lines(ai_item) != []


def test_curated_item_bypasses_ai_context_gate():
    """A human-attributed `fault_lines` passes through even without an AI keyword —
    curation is the human's vouch."""
    curated = {"date": "2026-09-01", "title": "Some ruling",
               "url": "https://www.courtlistener.com/x", "text": "disclosure",
               "fault_lines": ["disclosure"]}
    assert "disclosure" in ingest._relevant_fault_lines(curated)


def test_dry_run_writes_nothing(tmp_path):
    """The property the first live run depends on: a dry run must not append to the
    store OR the ledger. If it wrote ledger rows, the real run would skip those docs as
    'already decided' — a preview would silently break the run it validates."""
    harvested = tmp_path / "harvested.jsonl"
    ledger.ADMISSIONS_FILE = tmp_path / "admissions.jsonl"
    ledger.HISTORY = tmp_path
    cand = {"date": "2026-09-01", "title": "Court sanctions over fabricated cites",
            "url": "https://www.lawnext.com/x.html", "text": "disclosure required.",
            "fault_lines": ["disclosure"]}
    r = ingest.admit([cand], feed_path=harvested, seen_feed=[], dry_run=True)
    assert r["admitted"] == 1 and r["dry_run"] is True
    assert r["decisions"][0]["decision"] == "admit"
    assert not harvested.exists(), "dry run appended to the store"
    assert not ledger.ADMISSIONS_FILE.exists(), "dry run wrote ledger rows"


def test_dry_run_preview_matches_real_run(tmp_path):
    """A preview must predict the real run exactly (same decisions), then the real run
    must produce them — and the second preview after that must show 'already decided'."""
    harvested = tmp_path / "harvested.jsonl"
    ledger.ADMISSIONS_FILE = tmp_path / "admissions.jsonl"
    ledger.HISTORY = tmp_path
    cand = {"date": "2026-09-01", "title": "Court sanctions over fabricated cites",
            "url": "https://www.lawnext.com/y.html", "text": "disclosure required.",
            "fault_lines": ["disclosure"]}
    prev = ingest.admit([cand], feed_path=harvested, seen_feed=[], dry_run=True)
    real = ingest.admit([cand], feed_path=harvested, seen_feed=[])
    assert prev["decisions"][0]["decision"] == real["decisions"][0]["decision"] == "admit"
    assert real["admitted"] == 1
    # now it is decided; a further run skips it (memory works, and the preview didn't lie)
    again = ingest.admit([cand], feed_path=harvested, seen_feed=[])
    assert again["skipped_decided"] == 1 and again["admitted"] == 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
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
            import traceback; traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
