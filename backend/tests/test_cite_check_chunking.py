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


def test_run_cite_check_surfaces_named_error(monkeypatch):
    class _BoomClient(_FakeClient):
        async def extract_references(self, text: str, resolve: bool = False):
            raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(cite_check, "DescrybeClient", _BoomClient)
    by_type, _ = _run("x" * 50)  # single chunk

    assert "error" in by_type
    msg = by_type["error"]["message"]
    assert "TimeoutError" in msg and "timed out" in msg
