"""Deterministic text normalization and clause-aware segmentation for legal documents.

Self-contained by design: no imports from ``config`` or any other backend module,
so it can be imported, tested, and adopted independently of the (currently
broken) ``config.constants`` import graph.

Two jobs, matching the two gaps in ``document_processor.py``:

1. :func:`normalize_text` — clean raw extraction before chunking/embedding.
   Strips injected page markers, collapses whitespace, and drops repeated
   header/footer lines so they stop polluting vectors.
2. :func:`split_sentences` / :func:`find_last_sentence_boundary` — legal-aware
   sentence segmentation that does not split on ``Mr.``, ``Inc.``, ``§4.2(a)``,
   decimals, or ``U.S.`` the way the current ``rfind('.')`` heuristic does.

Deterministic and rule-based. This is intentionally *not* a statistical model:
every decision is reproducible, which matters for the audit-trail pillar. If a
heavier segmenter is ever warranted, ``PySBD`` is the drop-in upgrade (same call
shape, still rule-based, no model download).
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

__all__ = [
    "normalize_text",
    "split_sentences",
    "find_last_sentence_boundary",
    "ABBREVIATIONS",
]

# Single-token abbreviations that must NOT terminate a sentence. Stored without
# the trailing period and with internal dots stripped, so "U.S." -> "us".
ABBREVIATIONS: frozenset[str] = frozenset({
    # honorifics / titles
    "mr", "mrs", "ms", "dr", "prof", "hon", "sr", "jr", "esq", "st",
    # entities / corporate forms
    "inc", "corp", "co", "llc", "llp", "ltd", "plc", "lp", "bros", "assn",
    "assoc", "dept", "govt", "univ", "div", "gen",
    # legal citation / reference
    "no", "nos", "vs", "cf", "ca", "viz", "al", "seq", "p", "pp", "re",
    "ed", "eds", "sec", "secs", "art", "arts", "ex", "exs", "fig", "figs",
    "vol", "vols", "id", "ibid", "supra", "infra", "op", "n", "nn", "d",
    "j", "v", "etc",
    # multi-dot jurisdictions / reporters (dots stripped on lookup)
    "us", "usa", "uk", "eu", "dc", "usc", "cfr", "fed", "f",
})

_PAGE_MARKER_RE = re.compile(r"={2,}\s*Page\s+\d+\s*={2,}", re.IGNORECASE)
_INLINE_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")
# A short line (likely header/footer) that appears this many times gets deduped.
_DEDUPE_MIN_COUNT = 3
_DEDUPE_MAX_LEN = 60


def _dedupe_repeated_lines(lines: List[str]) -> List[str]:
    """Drop short header/footer lines that repeat across pages, keeping the first.

    Conservative: only touches lines under ``_DEDUPE_MAX_LEN`` chars that appear at
    least ``_DEDUPE_MIN_COUNT`` times. Long clauses are never touched even if they
    recur, since a repeated clause is signal, not boilerplate.
    """
    counts: dict[str, int] = {}
    for line in lines:
        if 0 < len(line) <= _DEDUPE_MAX_LEN:
            counts[line] = counts.get(line, 0) + 1
    seen: set[str] = set()
    out: List[str] = []
    for line in lines:
        if 0 < len(line) <= _DEDUPE_MAX_LEN and counts[line] >= _DEDUPE_MIN_COUNT:
            if line in seen:
                continue
            seen.add(line)
        out.append(line)
    return out


def normalize_text(
    text: str,
    *,
    lowercase: bool = False,
    strip_page_markers: bool = True,
    dedupe_repeated_lines: bool = True,
) -> str:
    """Clean extracted text for chunking/embedding.

    Returns a single string with canonical whitespace and no page artifacts.
    Preserves case by default (downstream LLM reasoning wants the real text);
    set ``lowercase=True`` when the output feeds an embedding-only path.
    """
    if not text:
        return ""

    # Canonical unicode (NBSP, smart quotes, ligatures -> ascii equivalents).
    text = unicodedata.normalize("NFKC", text)

    if strip_page_markers:
        text = _PAGE_MARKER_RE.sub("\n", text)

    # Normalize line endings and vertical control chars.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\f", "\n").replace("\v", "\n")

    lines = [_INLINE_WS_RE.sub(" ", ln).strip() for ln in text.split("\n")]
    if dedupe_repeated_lines:
        lines = _dedupe_repeated_lines(lines)

    text = "\n".join(ln for ln in lines if ln)
    text = _BLANK_RE.sub("\n\n", text)

    if lowercase:
        text = text.lower()

    return text.strip()


def _is_abbreviation(text: str, i: int) -> bool:
    """True if the ``'.'`` at ``text[i]`` is part of an abbreviation, number, or
    section reference — i.e. NOT a sentence boundary. ``i`` must index a period.
    """
    if i <= 0 or i >= len(text) - 1:
        # Period at start/end of string has no preceding token; treat as boundary.
        return False

    prev = text[i - 1]
    nxt = text[i + 1]

    # Decimal / version / section number: "1,250,000.00", "4.2", "§4.2(a)".
    if prev.isdigit() and (nxt.isdigit() or nxt == "("):
        return True

    # Known abbreviation token immediately before the period (strip dots, lowercase).
    j = i - 1
    while j >= 0 and not text[j].isspace():
        j -= 1
    token = text[j + 1:i]
    if token:
        key = token.rstrip(".").replace(".", "").lower()
        if key in ABBREVIATIONS:
            return True
        # Single uppercase initial followed by a space and another uppercase
        # letter: "John A. Smith", "U. S." — an initial, not a boundary.
        if len(token) == 1 and token.isupper():
            k = i + 1
            while k < len(text) and text[k].isspace():
                k += 1
            if k < len(text) and text[k].isupper():
                return True

    return False


def _is_sentence_end(text: str, i: int) -> bool:
    """True if ``text[i]`` is a sentence-terminating ``.``, ``?``, or ``!``."""
    c = text[i]
    if c in "?!":
        return True
    if c == ".":
        return not _is_abbreviation(text, i)
    return False


def split_sentences(text: str) -> List[str]:
    """Split text into sentences without breaking on legal abbreviations or refs."""
    sentences: List[str] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        if text[i] in ".?!" and _is_sentence_end(text, i):
            sentences.append(text[start:i + 1].strip())
            start = i + 1
            i = start
            continue
        i += 1
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return [s for s in sentences if s]


def find_last_sentence_boundary(window: str, threshold: float = 0.5) -> Optional[int]:
    """Offset (exclusive) of the last real sentence boundary in ``window``.

    Mirrors the intent of ``document_processor.chunk_text``'s
    ``rfind('.')`` / ``rfind('?')`` / ``rfind('!')`` logic, but legal-aware:
    only counts a period that is a genuine sentence end. Returns ``None`` if no
    boundary falls within the trailing ``threshold`` fraction of the window.
    """
    n = len(window)
    if n == 0:
        return None
    lo = int(threshold * n)
    for i in range(n - 1, lo - 1, -1):
        if window[i] in ".?!" and _is_sentence_end(window, i):
            return i + 1
    return None
