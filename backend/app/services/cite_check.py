"""
Legal AI OS — Cite Check Service

Validates a legal brief/filing against the Descrybe Legal Engine:
  1. extract_case_references  -> every citation, resolved to a case_id, with
                                 good-law treatment (all in one tool call)
  2. verify_quote             -> word-for-word accuracy of each quoted passage
  3. emit a findings report + an annotated copy of the brief (new name)

This is an async generator that yields progress/log events, then a ``report``
event and a ``brief`` event, so the frontend can stream a live log.
"""

from __future__ import annotations

import re
from uuid import UUID

from app.services.descrybe import DescrybeClient

QUOTE_RE = re.compile(r'"([^"\n]{15,})"|“([^”\n]{15,})”')

# Extraction over a very large document in a single Descrybe call can exceed the
# request timeout (resolve=True resolves + reads treatment for every citation in
# one round trip). Split anything past this threshold into chunks that each stay
# comfortably under the timeout, then stitch the results back together with
# corrected global character offsets.
_EXTRACT_CHUNK_CHARS = 20_000


def _chunk_text(text: str, max_chars: int = _EXTRACT_CHUNK_CHARS) -> list[tuple[int, str]]:
    """Split text into (offset, chunk) pairs, preferring paragraph boundaries.

    Offsets are character positions into the original ``text`` so extracted
    citation spans can be shifted back to global coordinates.
    """
    if len(text) <= max_chars:
        return [(0, text)]

    chunks: list[tuple[int, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        end = min(pos + max_chars, n)
        if end < n:
            # Back up to the last paragraph/line/space break to avoid slicing a
            # citation in half; fall back to a hard cut if none is found.
            window = text[pos:end]
            for sep in ("\n\n", "\n", " "):
                idx = window.rfind(sep)
                if idx > max_chars // 2:
                    end = pos + idx + len(sep)
                    break
        chunks.append((pos, text[pos:end]))
        pos = end
    return chunks

# Map Descrybe treatment indicator -> a compact status label + glyph
_STATUS = {
    "positive": ("good", "✓"),
    "negative": ("bad", "✗"),
    "caution": ("caution", "⚠"),
    "unknown": ("unknown", "?"),
}


def _extract_quotes(text: str) -> list[tuple[int, str]]:
    """Return (start_offset, quote_text) for each meaningful quoted passage."""
    quotes = []
    for m in QUOTE_RE.finditer(text):
        q = m.group(1) or m.group(2)
        if q:
            quotes.append((m.start(), q.strip()))
    return quotes


def _resolve_quote_owner(refs: list[dict], quote_start: int) -> dict | None:
    """Attribute a quote to the most recent citation whose span ends before it."""
    best = None
    for ref in refs:
        span = ref.get("span") or {}
        end = span.get("end", 0)
        if end <= quote_start:
            if best is None or end > (best.get("span") or {}).get("end", 0):
                best = ref
    return best


def _derive_name(name: str | None) -> str:
    base = (name or "brief").strip() or "brief"
    base = re.sub(r"\.(md|txt|docx?)$", "", base, flags=re.IGNORECASE)
    return f"{base} (cite-checked).md"


def _annotate_brief(text: str, refs: list[dict]) -> str:
    """Insert a status glyph after each citation span, right-to-left."""
    markers = []
    for ref in refs:
        span = ref.get("span") or {}
        end = span.get("end")
        if end is None:
            continue
        indicator = ((ref.get("treatment") or {}).get("indicator")) or "unknown"
        _, glyph = _STATUS.get(indicator, _STATUS["unknown"])
        markers.append((end, f" {glyph}"))
    markers.sort(key=lambda x: -x[0])
    annotated = text
    for end, mark in markers:
        annotated = annotated[:end] + mark + annotated[end:]
    return annotated


async def run_cite_check(text: str, name: str | None, user_id: UUID):
    """Yield progress events, then a report and an annotated brief."""
    client = DescrybeClient(user_id=user_id)

    yield {"type": "log", "message": "Starting cite check…"}
    yield {"type": "log", "message": f"Document: {len(text):,} characters"}

    # 1. Descrybe extract_case_references — extract + resolve + treat.
    # Large documents are chunked so no single call risks the request timeout;
    # spans are shifted back to global offsets and duplicate cases merged.
    yield {"type": "log", "message": "Descrybe extract_case_references — extracting citations, resolving to case IDs, and checking good-law treatment…"}
    chunks = _chunk_text(text)
    if len(chunks) > 1:
        yield {"type": "log", "message": f"  Large document — extracting in {len(chunks)} chunks to stay under the request timeout."}

    refs: list[dict] = []
    seen: dict[str, dict] = {}
    for i, (offset, chunk) in enumerate(chunks):
        try:
            data = await client.extract_references(chunk, resolve=True)
        except Exception as e:
            detail = str(e) or repr(e)
            hint = ""
            if "timed out" in detail.lower() or "timeout" in type(e).__name__.lower():
                hint = " (raise DESCRYBE_TIMEOUT_SECONDS or lower _EXTRACT_CHUNK_CHARS)"
            yield {"type": "error", "message": f"Cite check failed on chunk {i + 1}/{len(chunks)}: {type(e).__name__}: {detail}{hint}"}
            yield {"type": "done"}
            return

        for ref in data.get("references", []):
            # Shift every span from chunk-local to document-global coordinates.
            span = ref.get("span")
            if isinstance(span, dict):
                if span.get("start") is not None:
                    span["start"] += offset
                if span.get("end") is not None:
                    span["end"] += offset
            for sp in ref.get("spans") or []:
                if isinstance(sp, dict):
                    if sp.get("start") is not None:
                        sp["start"] += offset
                    if sp.get("end") is not None:
                        sp["end"] += offset

            # Merge duplicate authorities across chunks (keep the first, richest
            # occurrence for annotation/attribution).
            key = ref.get("case_id") or ((ref.get("resolution") or {}).get("resolved") or {}).get("case_id") \
                or ref.get("case_name_hint") or ref.get("citation_text") or ref.get("raw_text")
            if key and key in seen:
                prior = seen[key]
                prior["occurrence_count"] = (prior.get("occurrence_count") or 1) + (ref.get("occurrence_count") or 1)
                continue
            if key:
                seen[key] = ref
            refs.append(ref)
    resolved = [r for r in refs if r.get("case_id") or (r.get("resolution") or {}).get("resolved")]
    yield {"type": "log", "message": f"Descrybe found {len(refs)} citation reference(s); {len(resolved)} resolved to case IDs."}

    for ref in refs:
        title = ((ref.get("resolution") or {}).get("resolved") or {}).get("title") or ref.get("case_name_hint") or ref.get("citation_text")
        indicator = ((ref.get("treatment") or {}).get("indicator")) or "unknown"
        status_label, glyph = _STATUS.get(indicator, _STATUS["unknown"])
        if ref.get("case_id") or (ref.get("resolution") or {}).get("resolved"):
            yield {"type": "log", "message": f"  {glyph} {title} — {status_label}"}
        else:
            yield {"type": "log", "message": f"  ✗ {title} — unresolved"}

    # 2. Descrybe verify_quote — word-for-word accuracy
    quotes = _extract_quotes(text)
    yield {"type": "log", "message": f"Descrybe verify_quote — checking {len(quotes)} quoted passage(s) word-for-word…"}

    quote_results = []
    for start, q in quotes:
        owner = _resolve_quote_owner(refs, start)
        if not owner:
            quote_results.append({"text": q, "attributed_to": None, "verified": None})
            yield {"type": "log", "message": f"  ? Could not attribute quote to a case: “{q[:60]}…”"}
            continue
        case_id = owner.get("case_id") or ((owner.get("resolution") or {}).get("resolved") or {}).get("case_id")
        title = ((owner.get("resolution") or {}).get("resolved") or {}).get("title") or owner.get("case_name_hint") or "case"
        if not case_id:
            quote_results.append({"text": q, "attributed_to": title, "verified": None})
            yield {"type": "log", "message": f"  ? {title} not resolved — skipping quote"}
            continue
        try:
            result = await client.verify_quote(case_id, q)
            found = bool(result.get("found"))
            quote_results.append({"text": q, "attributed_to": title, "verified": found, "case_id": case_id})
            mark = "✓" if found else "✗"
            yield {"type": "log", "message": f"  {mark} “{q[:60]}…” → {title} ({'exact match' if found else 'no match'})"}
        except Exception as e:
            quote_results.append({"text": q, "attributed_to": title, "verified": None})
            yield {"type": "log", "message": f"  ! quote check failed: {e}"}

    # 3. Build report
    report = {
        "provider": "Descrybe Legal Engine",
        "tools": ["extract_case_references", "verify_quote"],
        "total_references": len(refs),
        "resolved": sum(1 for r in refs if r.get("case_id") or (r.get("resolution") or {}).get("resolved")),
        "unresolved": sum(1 for r in refs if not r.get("case_id") and not (r.get("resolution") or {}).get("resolved")),
        "good_law": 0,
        "caution": 0,
        "bad_law": 0,
        "unknown": 0,
        "quotes_checked": len(quote_results),
        "quotes_verified": sum(1 for q in quote_results if q["verified"] is True),
        "quotes_failed": sum(1 for q in quote_results if q["verified"] is False),
        "references": [],
        "quotes": quote_results,
    }

    for ref in refs:
        indicator = ((ref.get("treatment") or {}).get("indicator")) or "unknown"
        status_label, glyph = _STATUS.get(indicator, _STATUS["unknown"])
        report[{"good": "good_law", "bad": "bad_law", "caution": "caution", "unknown": "unknown"}[status_label]] += 1
        resolved_info = (ref.get("resolution") or {}).get("resolved") or {}
        report["references"].append({
            "citation": ref.get("citation_text") or ref.get("raw_text"),
            "case_title": resolved_info.get("title") or ref.get("case_name_hint") or "Unknown",
            "case_id": ref.get("case_id") or resolved_info.get("case_id"),
            "status": status_label,
            "treatment_category": (ref.get("treatment") or {}).get("category"),
            "resolution_confidence": resolved_info.get("resolution_confidence"),
            "display_reference": ref.get("display_reference"),
        })

    yield {"type": "report", "report": report}

    # 4. Annotated new brief
    annotated = _annotate_brief(text, refs)
    appendix = _build_appendix(report)
    new_brief = annotated + "\n\n" + appendix
    new_name = _derive_name(name)

    yield {"type": "brief", "name": new_name, "content": new_brief}
    yield {"type": "done"}


def _build_appendix(report: dict) -> str:
    lines = [
        "---",
        "",
        "## Cite-Check Report",
        "",
        "_Validated with the Descrybe Legal Engine — `extract_case_references` and `verify_quote`._",
        "",
        f"- References found: {report['total_references']}",
        f"- Resolved: {report['resolved']}",
        f"- Good law: {report['good_law']}  ·  Caution: {report['caution']}  ·  Bad law: {report['bad_law']}  ·  Unknown: {report['unknown']}",
        f"- Quotes checked: {report['quotes_checked']}  ·  Verified: {report['quotes_verified']}  ·  Failed: {report['quotes_failed']}",
        "",
        "### Citations",
        "",
    ]
    for r in report["references"]:
        glyph = {"good": "✓", "bad": "✗", "caution": "⚠", "unknown": "?"}.get(r["status"], "?")
        lines.append(f"- {glyph} **{r['case_title']}** — {r['citation']} ({r['status']})")
    if report["quotes"]:
        lines.append("")
        lines.append("### Quotes")
        lines.append("")
        for q in report["quotes"]:
            mark = "✓" if q["verified"] is True else ("✗" if q["verified"] is False else "?")
            lines.append(f"- {mark} “{q['text']}” — {q['attributed_to'] or 'unattributed'}")
    return "\n".join(lines)
