"""Network fetchers — allowlist-only ingestion of candidate docs.

The harvesting half of Phase 2. Every source is pre-assigned a tier by the allowlist in
``ingest.SOURCE_ALLOWLIST``; there is no open-web crawl by design (noise control is the
point). Fetchers turn a source's native format — RSS/Atom or the CourtListener JSON API —
into *candidates* (feed-schema-shaped dicts), which are then handed to ``ingest.admit()``,
which supplies all the run-to-run dedup memory.

SAFETY POSTURE (deliberate):
  * Live network is OPT-IN. ``harvest()`` returns nothing unless explicitly enabled
    (``live=True`` or ``RADAR_LIVE_FETCH=1``), so CI, tests, and default runs are
    deterministic and make no outbound calls.
  * Fetch is restricted to the allowlist. A URL whose domain is not allowlisted is
    skipped before any request is made — the allowlist is the boundary, not a filter
    applied afterward.
  * Fetched docs are written to ``sources/harvested.jsonl``, NEVER the hand-curated
    ``sources/feed.jsonl``. Curated stays curated (see ingest/score load_corpus).

Stdlib only (urllib + xml.etree) — no new dependency for the radar.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ingest import SOURCE_ALLOWLIST
import dedup

USER_AGENT = "legal-os-faultline-radar/1.0 (+https://github.com/motorthings/legal-os)"
TIMEOUT = 20  # seconds

# The allowlisted harvesting targets. Each entry's domain MUST be in SOURCE_ALLOWLIST;
# tier is taken from the allowlist at admission, never from the source's own claim.
SOURCES = [
    {"name": "CourtListener opinions (AI sanctions)",
     "url": "https://www.courtlistener.com/api/rest/v4/search/?q=AI%20hallucination%20sanctions&type=o",
     "kind": "courtlistener"},
    {"name": "LawSites (RSS)",
     "url": "https://www.lawnext.com/feed/", "kind": "rss"},
    {"name": "Artificial Lawyer (RSS)",
     "url": "https://www.artificiallawyer.com/feed/", "kind": "rss"},
]

_ATOM = "{http://www.w3.org/2005/Atom}"


def _domain_allowed(url):
    return dedup.domain_of(url) in SOURCE_ALLOWLIST


# --- parsers (pure; the unit under test) ------------------------------------

def _text(el):
    return (el.text or "").strip() if el is not None else ""


def parse_rss(xml_bytes):
    """Parse RSS 2.0 or Atom into raw entries [{title, link, date, summary}]. Stdlib."""
    root = ET.fromstring(xml_bytes)
    entries = []
    # RSS 2.0: rss/channel/item
    for item in root.iter("item"):
        entries.append({
            "title": _text(item.find("title")),
            "link": _text(item.find("link")),
            "date": _text(item.find("pubDate")),
            "summary": _strip_html(_text(item.find("description"))),
        })
    # Atom: feed/entry
    for entry in root.iter(f"{_ATOM}entry"):
        link_el = entry.find(f"{_ATOM}link")
        link = link_el.get("href") if link_el is not None else ""
        entries.append({
            "title": _text(entry.find(f"{_ATOM}title")),
            "link": link,
            "date": _text(entry.find(f"{_ATOM}updated")) or _text(entry.find(f"{_ATOM}published")),
            "summary": _strip_html(_text(entry.find(f"{_ATOM}summary"))),
        })
    return [e for e in entries if e["title"] and e["link"]]


_TAGS = re.compile(r"<[^>]+>")


def _strip_html(s):
    return re.sub(r"\s+", " ", _TAGS.sub(" ", s or "")).strip()


def parse_courtlistener(json_bytes):
    """Parse a CourtListener search API response into raw entries."""
    data = json.loads(json_bytes)
    out = []
    for r in data.get("results", []):
        cites = r.get("citation") or []
        snippet = r.get("snippet") or ""
        out.append({
            "title": r.get("caseName") or r.get("case_name") or "",
            "link": "https://www.courtlistener.com" + (r.get("absolute_url") or ""),
            "date": r.get("dateFiled") or r.get("date_filed") or "",
            "summary": _strip_html(snippet),
            "citation": cites[0] if cites else "",
        })
    return [e for e in out if e["title"] and e["link"]]


def _norm_date(s):
    """Best-effort ISO date from RSS pubDate / RFC822 / Atom / CourtListener forms."""
    s = (s or "").strip()
    if not s:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):        # already ISO (possibly with time)
        return s[:10]
    try:
        return parsedate_to_datetime(s).date().isoformat()   # RFC 822 (RSS)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def to_candidate(entry, source=None):
    """Raw entry -> feed-schema candidate for admission. Returns None if it lacks a
    usable date (the scorer requires one) or link. Tier is left unset so the allowlist
    assigns it at admission — a source never sets its own authority."""
    date = _norm_date(entry.get("date"))
    link = entry.get("link", "")
    if not date or not link:
        return None
    return {
        "date": date,
        "title": entry.get("title", ""),
        "url": link,
        "source": (source or {}).get("name", dedup.domain_of(link)),
        "text": entry.get("summary", "") or entry.get("citation", ""),
        # tier intentionally omitted -> ingest._assign_tier() decides from the allowlist
    }


# --- network (opt-in) -------------------------------------------------------

# Optional API tokens, per domain. Public RSS needs none; CourtListener's API is "open by
# default" but rate-limited hard (125/day authenticated, less anonymous), so a token raises
# the ceiling. Absent the env var the request is anonymous, exactly as before — no token is
# required to run, and nothing breaks when one isn't set.
DOMAIN_TOKEN_ENV = {
    "courtlistener.com": "COURTLISTENER_TOKEN",
}


def _auth_headers(url):
    """Auth header for a domain, when its token env var is set. CourtListener requires the
    literal word 'Token' before the key — a documented common error to omit it."""
    env = DOMAIN_TOKEN_ENV.get(dedup.domain_of(url))
    token = os.environ.get(env) if env else None
    return {"Authorization": f"Token {token}"} if token else {}


def _fetch(url):
    """GET a URL with a UA and timeout. Only ever called for allowlisted domains."""
    if not _domain_allowed(url):
        raise PermissionError(f"domain not allowlisted: {dedup.domain_of(url)}")
    headers = {"User-Agent": USER_AGENT, **_auth_headers(url)}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _fetch_source(src):
    """Fetch + parse ONE source. Returns (entries, error_or_None). Never raises — a
    per-source failure is isolated so one dead feed never blocks the pass."""
    if not _domain_allowed(src["url"]):
        return [], "domain_not_allowlisted"
    try:
        body = _fetch(src["url"])
        entries = (parse_courtlistener(body) if src["kind"] == "courtlistener"
                   else parse_rss(body))
        return entries, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def harvest_report(live=None, sources=None):
    """Per-source fetch outcomes, for diagnosing a run (which source responded, and
    why one didn't). Returns [] when not live. Each row:
    {name, domain, authenticated, ok, n_entries, n_candidates, error, candidates}.
    `authenticated` distinguishes "anonymous and fine" from "token was actually used"."""
    if live is None:
        live = os.environ.get("RADAR_LIVE_FETCH") == "1"
    if not live:
        return []
    report = []
    for src in (sources or SOURCES):
        entries, err = _fetch_source(src)
        cands = [c for c in (to_candidate(e, src) for e in entries) if c]
        report.append({
            "name": src["name"], "domain": dedup.domain_of(src["url"]),
            "authenticated": bool(_auth_headers(src["url"])),
            "ok": err is None, "n_entries": len(entries), "n_candidates": len(cands),
            "error": err, "candidates": cands,
        })
    return report


def harvest(live=None, sources=None):
    """Return candidate dicts from the allowlisted sources.

    Off by default: with live unset (and RADAR_LIVE_FETCH not '1') this makes no network
    calls and returns []. Pass live=True to actually fetch. A per-source failure is
    skipped — one dead feed never blocks the pass. Use harvest_report() to see which
    sources responded.
    """
    if live is None:
        live = os.environ.get("RADAR_LIVE_FETCH") == "1"
    if not live:
        return []
    return [c for r in harvest_report(live=True, sources=sources) for c in r["candidates"]]
