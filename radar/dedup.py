"""Deterministic document-identity helpers for run-to-run dedup (Layer 0).

The harvester must never re-admit a document the KB already holds, and must survive
across runs without a database. Identity is derived three ways, cheapest first:

  1. canonical_url   — the same link, normalized (tracking params stripped, query
                       sorted, host lowercased). Catches the literal re-fetch.
  2. content_hash    — sha256 of normalized title+text. Catches the same document
                       served at a different URL.
  3. citations       — reporter/docket citations extracted from title+text. Catches
                       "the same ruling re-reported by five outlets" (echoes), so the
                       primary is kept and the echoes collapse (Layer 1 lite).

Pure functions, no I/O, no deps — so the seen-set replays byte-identical, matching
the radar's determinism ethos.
"""
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Query params that carry no document identity — analytics / share tracking.
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "mc_cid", "mc_eid", "ref", "ref_src", "source",
    "_hsenc", "_hsmi", "igshid", "spm",
}


def domain_of(url):
    """Registrable-ish host, lowercased, `www.` stripped. '' if unparseable."""
    if not url:
        return ""
    host = urlsplit(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def canonical_url(url):
    """Normalize a URL to a stable identity string:
    lowercase scheme+host, drop `www.`, drop fragment, strip tracking params,
    sort remaining query params, drop a trailing slash on the path."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = "https"   # http/https are the same document for identity purposes
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or "/"
    query = urlencode(sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
    ))
    return urlunsplit((scheme, host, path, query, ""))  # fragment dropped


def _normalize_text(s):
    """Lowercase, collapse all whitespace to single spaces, strip. Deterministic."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def content_hash(item):
    """sha256 over normalized title + text. Same content -> same hash, regardless of
    where it was published. Returns a hex digest."""
    basis = _normalize_text(item.get("title", "")) + "\n" + _normalize_text(item.get("text", ""))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


# US reporter citation, e.g. "678 F. Supp. 3d 443", "2023 WL 1234567", "599 U.S. 12".
_REPORTER_RE = re.compile(
    r"\b\d{1,4}\s+"
    r"(?:[A-Z][A-Za-z]*\.?\s*){1,5}"   # reporter abbrev tokens (F., Supp., U.S., WL, Cal. App. ...)
    r"(?:\d{1,2}[a-z]{1,2}\s+)?"        # optional series (3d, 2d, ...)
    r"\d{1,7}\b"
)
# Docket numbers, e.g. "No. 22-1234", "1:22-cv-01461", "Case No. 23-cv-99".
_DOCKET_RE = re.compile(
    r"\b(?:No\.\s?|Case\s+No\.\s?)?\d{1,2}:\d{2}-[a-z]{2,4}-\d{3,6}\b"
    r"|\bNo\.\s?\d{2,4}-\d{2,6}\b"
)


# Rule / statute references (FRAP 38, FRCP 11, Rule 11, 28 U.S.C. 1927 ...) look like
# reporter cites but recur across DISTINCT rulings, so they must never key an echo.
_RULE_TOKENS = ("frap", "frcp", "frcrp", "fre", "usc", "u.s.c", "cfr", "rule", "sec")


def extract_citations(item):
    """Return the sorted set of normalized reporter/docket citations in an item's
    title+text — used to collapse echoes (the same authority re-reported). Rule and
    statute references are excluded because they are shared across distinct rulings.
    Empty when no case citation is present (most commentary/vendor items)."""
    hay = (item.get("title", "") + " " + item.get("text", ""))
    cites = set()
    for rx in (_REPORTER_RE, _DOCKET_RE):
        for m in rx.findall(hay):
            c = _normalize_text(m)
            if not c or c.isdigit():                 # a bare number is not a citation
                continue
            if any(tok in c for tok in _RULE_TOKENS): # rule/statute ref, not a reporter cite
                continue
            cites.add(c)
    return sorted(cites)


def identity(item):
    """The full identity triple used by the seen-index."""
    return {
        "canonical_url": canonical_url(item.get("url", "")),
        "content_hash": content_hash(item),
        "citations": extract_citations(item),
    }
