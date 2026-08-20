"""Cite-check chunking + span-merge regression tests.

A large brief exceeds the Descrybe request timeout when extracted in one call,
so ``run_cite_check`` chunks the document. These tests lock in that the chunker
splits correctly and that ``run_cite_check`` shifts citation spans back to
global offsets and merges duplicate authorities across chunk boundaries.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from app.services import cite_check
from app.services.cite_check import _chunk_text, _EXTRACT_CHUNK_CHARS, run_cite_check


def _drain(agen):
    """Collect every event from an async generator into a list."""
    async def go():
        return [ev async for ev in agen]
    return asyncio.run(go())


def test_chunk_text_small_is_single_chunk():
    assert _chunk_text("short text") == [(0, "short text")]


def test_chunk_text_offsets_reconstruct_original():
    text = ("word " * 100 + "\n\n") * 400
    text = text[:104_843]
    chunks = _chunk_text(text)

    assert len(chunks) > 1
    assert "".join(c for _, c in chunks) == text            # lossless
    assert all(text[o:o + len(c)] == c for o, c in chunks)  # offsets valid
    assert all(len(c) <= _EXTRACT_CHUNK_CHARS for _, c in chunks)


class _FakeClient:
    """Stand-in Descrybe client: one resolved ref per chunk, local span 0..12."""

    def __init__(self, *_, **__):
        pass

    async def extract_references(self, text: str, resolve: bool = False):
        # Same case_id every chunk so the merge path is exercised.
        return {
            "references": [{
                "case_id": "c1",
                "citation_text": "347 U.S. 483",
                "span": {"start": 0, "end": 12},
                "spans": [{"start": 0, "end": 12}],
                "occurrence_count": 1,
                "resolution": {"resolved": {"case_id": "c1", "title": "Brown v. Board"}},
                "treatment": {"indicator": "positive"},
            }]
        }

    async def verify_quote(self, case_id: str, quote: str):
        return {"found": True}


def _run(monkeypatch_text):
    events = _drain(run_cite_check(monkeypatch_text, "brief", uuid4()))
    return {e["type"]: e for e in events if e["type"] in ("report", "error")}, events


def test_run_cite_check_merges_dupes_and_globalizes_spans(monkeypatch):
    monkeypatch.setattr(cite_check, "DescrybeClient", _FakeClient)
    text = ("word " * 100 + "\n\n") * 400
    text = text[:104_843]

    by_type, events = _run(text)

    assert "error" not in by_type
    report = by_type["report"]["report"]
    # Duplicate case across 6 chunks collapses to a single reference...
    assert report["total_references"] == 1
    # ...and the annotated brief must not throw on the globalized spans.
    assert any(e["type"] == "brief" for e in events)


def test_quote_owner_requires_proximity():
    from app.services.cite_check import _resolve_quote_owner, _QUOTE_PROXIMITY_CHARS

    refs = [{"span": {"start": 0, "end": 12}, "case_id": "c1"}]
    # Quote right after the cite → attributed.
    assert _resolve_quote_owner(refs, 20, 60) is refs[0]
    # Quote far past the proximity window → not a case quote.
    far = _QUOTE_PROXIMITY_CHARS + 100
    assert _resolve_quote_owner(refs, far, far + 40) is None


def test_quote_classification_buckets(monkeypatch):
    # One resolved cite; a quote next to it that verify_quote rejects → misquote.
    # A quote with no cite anywhere near → unverifiable, NOT a failure.
    class _Client(_FakeClient):
        async def extract_references(self, text, resolve=False):
            return {"references": [{
                "case_id": "c1", "citation_text": "1 U.S. 1",
                "span": {"start": 0, "end": 10}, "spans": [{"start": 0, "end": 10}],
                "resolution": {"resolved": {"case_id": "c1", "title": "A v. B"}},
                "treatment": {"indicator": "positive"},
            }]}

        async def verify_quote(self, case_id, quote):
            return {"found": False}

    monkeypatch.setattr(cite_check, "DescrybeClient", _Client)
    text = '1 U.S. 1 said "this exact phrase here" and later.' + (" filler" * 200) + ' then "an orphan quote with no cite"'
    by_type, _ = _run(text)
    report = by_type["report"]["report"]
    assert report["quotes_failed"] == 1          # the near-cite mismatch
    assert report["quotes_unverifiable"] == 1    # the orphan quote
    assert report["quotes_verified"] == 0


def test_deep_pass_pulls_fixes(monkeypatch):
    class _Client(_FakeClient):
        async def extract_references(self, text, resolve=False):
            return {"references": [{
                "case_id": "c1", "citation_text": "1 U.S. 1",
                "span": {"start": 0, "end": 10}, "spans": [{"start": 0, "end": 10}],
                "resolution": {"resolved": {"case_id": "c1", "title": "A v. B"}},
                "treatment": {"indicator": "caution", "category": "distinguished"},
            }]}

        async def verify_quote(self, case_id, quote):
            return {"found": False}

        async def get_case_passages(self, case_id, focus):
            return {"passages": [{"text": "the real language from the opinion"}]}

        async def find_cases_that_cite(self, case_id):
            return {"results": [{"title": "C v. D", "treatment": {"indicator": "negative", "category": "overruled"}}]}

    monkeypatch.setattr(cite_check, "DescrybeClient", _Client)
    text = '1 U.S. 1 held "a phrase that will not match".'
    events = _drain(cite_check.run_cite_check(text, "brief", uuid4(), deep=True))
    report = next(e["report"] for e in events if e["type"] == "report")

    fixes = report["fixes"]
    assert fixes["misquotes"][0]["correct_passage"] == "the real language from the opinion"
    assert len(fixes["caution"][0]["negative_citing"]) == 1
    # deep-pass fix section makes it into the downloadable brief
    brief = next(e["content"] for e in events if e["type"] == "brief")
    assert "Suggested Fixes (deep pass)" in brief


def test_run_cite_check_surfaces_named_error(monkeypatch):
    class _BoomClient(_FakeClient):
        async def extract_references(self, text: str, resolve: bool = False):
            raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(cite_check, "DescrybeClient", _BoomClient)
    by_type, _ = _run("x" * 50)  # single chunk

    assert "error" in by_type
    msg = by_type["error"]["message"]
    assert "TimeoutError" in msg and "timed out" in msg
