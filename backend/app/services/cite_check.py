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


# Signals that a quoted string is NOT case-holding language and should not be
# verified against a case opinion. Checked against the quote plus a small window
# of text before it (the introductory clause carries the tell).
_STATUTE_RE = re.compile(r"§|\bU\.?S\.?C\.?\b|\bC\.?F\.?R\.?\b|\bC\.?R\.?S\.?\b|\bFed\.?\s*R\.?\s*(Civ|Crim|Evid|App)\b|\bRule\s+\d|\bSection\s+\d", re.IGNORECASE)
_SPEAKER_RE = re.compile(r"\b(testified|deposition|declar(ed|ation)|affidavit|stated in (his|her|their|the)|wrote(?: that)?|email|Dep\.|Decl\.|Tr\.)\b", re.IGNORECASE)
_CONTRACT_RE = re.compile(r"\b(agreement|contract|policy|handbook|the (offer|separation) )\b", re.IGNORECASE)
# Arbitration / filing-structure language: the document's own prose, not a case.
_ARBITRATION_RE = re.compile(r"\b(JAMS|arbitrat(or|ion)|Claimant|Respondent|Demand for Arbitration|Streamlined Rules|Comprehensive Rules|Employment (Arbitration )?Rules|prayer for relief|relief requested|WHEREFORE)\b", re.IGNORECASE)


def _classify_non_case_quote(context_before: str, quote: str) -> str | None:
    """Return a reason string if the quote is clearly not case-holding language.

    ``context_before`` is the ~120 chars preceding the quote (the introductory
    clause). Returns ``None`` when nothing rules it out as a case quote.
    """
    window = f"{context_before} {quote}"
    if _ARBITRATION_RE.search(window):
        return "arbitration filing language (JAMS rules / party terms) — part of the document, no case to verify"
    if _STATUTE_RE.search(window):
        return "statute or rule text — verify against the code (search_laws_and_rules), not a case opinion"
    if _SPEAKER_RE.search(context_before):
        return "testimony / party statement — quotes a person or document, not a court"
    if _CONTRACT_RE.search(context_before):
        return "contract or policy language — quotes an agreement, not a court"
    words = quote.split()
    if len(words) <= 4 and (quote.istitle() or quote.isupper()):
        return "short defined term — not a case holding"
    return None


def _extract_quotes(text: str) -> list[tuple[int, str]]:
    """Return (start_offset, quote_text) for each meaningful quoted passage."""
    quotes = []
    for m in QUOTE_RE.finditer(text):
        q = m.group(1) or m.group(2)
        if q:
            quotes.append((m.start(), q.strip()))
    return quotes


# A quote is only treated as belonging to a citation when the cite sits within
# this many characters of the quote (on either side). Legal writing puts the
# cite right before or right after the quoted passage; anything farther away is
# almost certainly a different source (statute, contract, party statement) and
# should not be scored as a failed *case* quote.
_QUOTE_PROXIMITY_CHARS = 400


def _resolve_quote_owner(refs: list[dict], quote_start: int, quote_end: int) -> dict | None:
    """Attribute a quote to the nearest citation within the proximity window.

    Legal style places a quote's supporting cite immediately before or after it,
    so we take the closest citation span in either direction and require it to be
    within ``_QUOTE_PROXIMITY_CHARS``. Returns ``None`` when no cite is close
    enough — i.e. the quote is probably not a case quotation at all.
    """
    best = None
    best_dist: int | None = None
    for ref in refs:
        span = ref.get("span") or {}
        s, e = span.get("start"), span.get("end")
        if s is None or e is None:
            continue
        if e <= quote_start:
            dist = quote_start - e          # cite before the quote
        elif s >= quote_end:
            dist = s - quote_end            # cite after the quote
        else:
            dist = 0                        # overlapping / inline
        if best_dist is None or dist < best_dist:
            best, best_dist = ref, dist
    if best is None or (best_dist is not None and best_dist > _QUOTE_PROXIMITY_CHARS):
        return None
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


async def run_cite_check(text: str, name: str | None, user_id: UUID, deep: bool = False):
    """Yield progress events, then a report and an annotated brief.

    When ``deep`` is set, each flagged item is drilled for a concrete fix after
    the standard checks: misquotes get the correct passage, caution cites get
    the negative forward-citation, unknown cites get a summary confirmation.
    """
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

    # Each quote lands in one of three buckets:
    #   verified     — matched word-for-word in the resolved case (verified=True)
    #   misquote     — attributed to a RESOLVED case but not found (verified=False)
    #   unverifiable — no nearby case cite, or the nearby cite didn't resolve, so
    #                  it can't be a case-quote failure (verified=None + reason)
    # A quoted string is only a checkable CASE quote when it sits next to a
    # RESOLVED case citation. In a filing, most quotation marks wrap defined
    # terms, party names, statutes, and descriptive phrases — those are dropped
    # entirely (counted as skipped) rather than reported as "unverifiable".
    quote_results = []
    skipped = 0
    for start, q in quotes:
        end = start + len(q)
        # Obvious non-case language (statute, testimony, contract, defined term,
        # arbitration prose) — drop without a verification attempt.
        if _classify_non_case_quote(text[max(0, start - 120):start], q):
            skipped += 1
            continue
        owner = _resolve_quote_owner(refs, start, end)
        case_id = owner and (owner.get("case_id") or ((owner.get("resolution") or {}).get("resolved") or {}).get("case_id"))
        if not owner or not case_id:
            # No resolved case citation adjacent → not a case quotation. Skip.
            skipped += 1
            continue
        title = ((owner.get("resolution") or {}).get("resolved") or {}).get("title") or owner.get("case_name_hint") or "case"
        citation = owner.get("citation_text") or owner.get("raw_text")
        try:
            result = await client.verify_quote(case_id, q)
            found = bool(result.get("found"))
            quote_results.append({
                "text": q, "attributed_to": title, "citation": citation,
                "verified": found, "case_id": case_id,
                "category": "verified" if found else "misquote",
            })
            mark = "✓" if found else "✗"
            note = "exact match" if found else "NO MATCH — possible misquote"
            yield {"type": "log", "message": f"  {mark} “{q[:60]}…” → {title} ({note})"}
        except Exception as e:
            skipped += 1
            yield {"type": "log", "message": f"  ! quote check failed: {e}"}

    if skipped:
        yield {"type": "log", "message": f"  ({skipped} quoted passage(s) skipped — not case quotations)"}

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
        # Only quotes adjacent to a resolved case cite are checked and reported.
        "quotes_checked": len(quote_results),
        "quotes_verified": sum(1 for q in quote_results if q["verified"] is True),
        "quotes_failed": sum(1 for q in quote_results if q.get("category") == "misquote"),
        # Quoted passages that aren't case quotations (defined terms, party
        # names, statutes, filing prose) — dropped, shown only as a count.
        "quotes_skipped": skipped,
        "references": [],
        "quotes": quote_results,
    }

    for ref in refs:
        treatment = ref.get("treatment") or {}
        indicator = treatment.get("indicator") or "unknown"
        status_label, glyph = _STATUS.get(indicator, _STATUS["unknown"])
        report[{"good": "good_law", "bad": "bad_law", "caution": "caution", "unknown": "unknown"}[status_label]] += 1
        resolved_info = (ref.get("resolution") or {}).get("resolved") or {}
        category = treatment.get("category")
        weight = treatment.get("weight")
        report["references"].append({
            "citation": ref.get("citation_text") or ref.get("raw_text"),
            "case_title": resolved_info.get("title") or ref.get("case_name_hint") or "Unknown",
            "case_id": ref.get("case_id") or resolved_info.get("case_id"),
            "status": status_label,
            "treatment_category": category,
            "treatment_weight": weight,
            "resolution_confidence": resolved_info.get("resolution_confidence"),
            "display_reference": ref.get("display_reference"),
            # Plain-language 'why + is it dangerous', derived from the treatment
            # data Descrybe already returned — no extra call.
            "explanation": _explain_treatment(status_label, category, weight) if status_label in ("caution", "unknown") else None,
            # How the brief uses this authority — the sentence around the cite,
            # with Descrybe's span markers stripped.
            "usage_excerpt": _clean_excerpt(ref.get("first_excerpt") or ref.get("excerpt")),
        })

    # 3b. Deep pass — drill each flagged item for a concrete fix.
    if deep:
        async for ev in _deep_pass(client, report):
            if ev.get("type") == "fixes":
                report["fixes"] = ev["fixes"]
            else:
                yield ev

    yield {"type": "report", "report": report}

    # 4. Annotated new brief
    annotated = _annotate_brief(text, refs)
    appendix = _build_appendix(report)
    new_brief = annotated + "\n\n" + appendix
    new_name = _derive_name(name)

    yield {"type": "brief", "name": new_name, "content": new_brief}
    yield {"type": "done"}


def _passage_text(data: dict) -> str | None:
    """Pull the best human-readable passage text out of a get_case_passages result."""
    passages = data.get("passages") or data.get("results") or []
    for p in passages:
        if isinstance(p, dict):
            t = p.get("text") or p.get("passage") or p.get("body")
            if t:
                return t.strip()
        elif isinstance(p, str) and p.strip():
            return p.strip()
    return None


# Plain-language meaning + danger level for each treatment category Descrybe
# returns. danger: low = keep, medium = check it touches your point, high = fix.
_TREATMENT_MEANING = {
    "distinguished":     ("A later court distinguished this case — applied a different rule on different facts.", "medium",
                          "Distinguishing limits a case to its facts; it does not overrule it. Safe to keep unless the distinguished point is the one you rely on."),
    "limited":           ("A later court limited this holding to narrower circumstances.", "medium",
                          "Keep it only if your proposition falls inside the narrowed scope."),
    "criticized":        ("A later court criticized this case's reasoning without overruling it.", "medium",
                          "Still citable, but expect pushback; consider a stronger parallel authority."),
    "questioned":        ("A later court questioned this case's continued validity.", "medium",
                          "Confirm no controlling authority has since rejected it."),
    "declined to follow":("Another court declined to follow this case (often out-of-jurisdiction).", "medium",
                          "Usually fine in your own jurisdiction; note the split if relevant."),
    "called into doubt": ("A later court called this case into doubt.", "medium",
                          "Verify it still holds on your point before relying on it."),
    "superseded":        ("Superseded by statute or rule.", "high",
                          "The statutory change likely controls — replace or reframe."),
    "overruled":         ("Overruled by a later decision.", "high",
                          "No longer good law — remove or replace."),
}


def _explain_treatment(status: str, category: str | None, weight: str | None) -> dict:
    """Explain WHY a cite is caution/unknown and whether it's safe to keep."""
    wlabel = f" ({weight} authority)" if weight else ""
    if status == "unknown":
        return {
            "why": "No treatment signal — Descrybe found no later cases treating this authority (typically recent or rarely-cited).",
            "danger": "low",
            "safe_to_keep": True,
            "recommendation": "Absence of treatment is not negative. Confirm the case still supports your proposition; if it's very recent, note that.",
        }
    cat = (category or "").lower()
    meaning, danger, rec = _TREATMENT_MEANING.get(
        cat,
        (f"Flagged caution ({category or 'unspecified'}).", "medium",
         "Drill the forward citations to see what point drew the treatment."),
    )
    return {
        "why": meaning + wlabel,
        "danger": danger,
        "safe_to_keep": danger != "high",
        "recommendation": rec,
    }


_MARKER_RE = re.compile(r"\[\[(?:TARGET|OTHER)_CITATION_(?:START|END)\]\]")


def _clean_excerpt(excerpt: str | None, limit: int = 400) -> str | None:
    """Strip Descrybe span markers and collapse whitespace from a usage excerpt."""
    if not excerpt:
        return None
    cleaned = _MARKER_RE.sub("", excerpt)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit] or None


def _corpus_verdict(cited_case_id: str, data: dict) -> dict:
    """Interpret a search_case_text result for a quote's exact language.

    Returns a verdict that distinguishes a verify_quote false-negative from a
    misattribution from a genuinely-absent (fabricated / non-case) quote.
    """
    results = [r for r in (data.get("results") or []) if isinstance(r, dict)]
    ids = [r.get("case_id") for r in results]
    if cited_case_id in ids:
        return {"verdict": "found_in_cited_case",
                "note": "exact language exists in the cited case — verify_quote was a false negative; the quote is likely fine"}
    if results:
        top = results[0]
        return {"verdict": "found_in_other_case",
                "note": f"language appears in a DIFFERENT case: {top.get('title') or top.get('case_id')} — likely misattributed",
                "correct_case": {"case_id": top.get("case_id"), "title": top.get("title"), "citation": top.get("citation")}}
    return {"verdict": "found_nowhere",
            "note": "exact language found in no case — fabricated, materially altered, or not a case quote; correct or remove"}


async def _deep_pass(client, report: dict):
    """Drill each flagged item for a concrete fix; yield log events + a fixes payload.

    - misquote  -> get_case_passages(case_id, focus=quote)  => correct language
    - caution   -> find_cases_that_cite(case_id)            => who/what gave treatment
    - unknown   -> get_case_summary(case_id)                => confirm it exists/holds
    """
    fixes = {"misquotes": [], "caution": [], "unknown": []}

    misquotes = [q for q in (report.get("quotes") or []) if q.get("category") == "misquote"]
    caution_refs = [r for r in report["references"] if r["status"] == "caution" and r.get("case_id")]
    unknown_refs = [r for r in report["references"] if r["status"] == "unknown" and r.get("case_id")]

    total = len(misquotes) + len(caution_refs) + len(unknown_refs)
    yield {"type": "log", "message": f"Deep pass — drilling {total} flagged item(s) for fixes…"}

    for q in misquotes:
        entry = {"quote": q["text"], "case": q.get("attributed_to"), "citation": q.get("citation")}
        try:
            data = await client.get_case_passages(q["case_id"], q["text"])
            entry["correct_passage"] = _passage_text(data)
            yield {"type": "log", "message": f"  ✎ misquote → pulled real passage for {q.get('attributed_to')}: " + (f"“{entry['correct_passage'][:70]}…”" if entry["correct_passage"] else "no passage returned")}
        except Exception as e:
            entry["error"] = str(e)
            yield {"type": "log", "message": f"  ! passage lookup failed: {e}"}

        # Corpus-wide search: is this exact language anywhere in case law?
        # Distinguishes a false negative / misattribution / truly-absent quote.
        try:
            phrase = q["text"][:200]
            found = await client.search_case_text(phrase)
            verdict = _corpus_verdict(q["case_id"], found)
            entry["corpus_verdict"] = verdict["verdict"]
            entry["corpus_note"] = verdict["note"]
            if verdict.get("correct_case"):
                entry["correct_case"] = verdict["correct_case"]
            yield {"type": "log", "message": f"    ⌕ corpus search → {verdict['verdict']}: {verdict['note']}"}
        except Exception as e:
            entry["corpus_error"] = str(e)
            yield {"type": "log", "message": f"    ! corpus search failed: {e}"}

        fixes["misquotes"].append(entry)

    for r in caution_refs:
        try:
            data = await client.find_cases_that_cite(r["case_id"])
            citing = data.get("results") or data.get("citing_cases") or []
            negatives = [c for c in citing if isinstance(c, dict)
                         and (c.get("treatment") or {}).get("indicator") in ("negative", "caution")]
            fixes["caution"].append({"case": r["case_title"], "citation": r["citation"],
                                     "treatment_category": r.get("treatment_category"),
                                     "negative_citing": negatives[:5]})
            yield {"type": "log", "message": f"  ⚠ caution → {r['case_title']}: {len(negatives)} case(s) gave negative/caution treatment"}
        except Exception as e:
            fixes["caution"].append({"case": r["case_title"], "citation": r["citation"], "error": str(e)})
            yield {"type": "log", "message": f"  ! forward-citation drill failed: {e}"}

    for r in unknown_refs:
        try:
            data = await client.get_case_summary(r["case_id"], simplified=True)
            summary = data.get("summary") or data.get("holding") or data.get("text")
            fixes["unknown"].append({"case": r["case_title"], "citation": r["citation"],
                                     "confirmed": bool(summary), "summary": (summary or "")[:400]})
            yield {"type": "log", "message": f"  ? unknown → {r['case_title']}: " + ("confirmed via summary" if summary else "no summary — verify manually")}
        except Exception as e:
            fixes["unknown"].append({"case": r["case_title"], "citation": r["citation"], "error": str(e)})
            yield {"type": "log", "message": f"  ! summary check failed: {e}"}

    yield {"type": "fixes", "fixes": fixes}


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
        f"- Case quotes checked: {report['quotes_checked']}  ·  Verified: {report['quotes_verified']}  ·  Misquoted: {report['quotes_failed']}  ·  Non-case passages skipped: {report.get('quotes_skipped', 0)}",
        "",
        "### Citations",
        "",
    ]
    for r in report["references"]:
        glyph = {"good": "✓", "bad": "✗", "caution": "⚠", "unknown": "?"}.get(r["status"], "?")
        lines.append(f"- {glyph} **{r['case_title']}** — {r['citation']} ({r['status']})")
        exp = r.get("explanation")
        if exp and exp.get("why"):
            keep = "safe to keep" if exp.get("safe_to_keep") else "needs a fix"
            lines.append(f"  - _Why ({exp.get('danger')} risk — {keep}):_ {exp['why']}")
            if exp.get("recommendation"):
                lines.append(f"  - {exp['recommendation']}")
    quotes = report.get("quotes") or []
    misquotes = [q for q in quotes if q.get("category") == "misquote"]
    verified = [q for q in quotes if q.get("category") == "verified"]

    if misquotes:
        lines += ["", "### ⚠ Misquotes to fix (attributed case resolved, text not found)", ""]
        for q in misquotes:
            cite = f" — {q['citation']}" if q.get("citation") else ""
            lines.append(f"- ✗ “{q['text']}” → **{q.get('attributed_to') or 'case'}**{cite}")
    if verified:
        lines += ["", f"### ✓ Verified quotes ({len(verified)})", ""]
        for q in verified:
            lines.append(f"- ✓ “{q['text']}” → {q.get('attributed_to') or 'case'}")

    fixes = report.get("fixes")
    if fixes:
        lines += ["", "---", "", "## Suggested Fixes (deep pass)", ""]
        if fixes.get("misquotes"):
            lines += ["### Misquotes — correct language pulled from the opinion", ""]
            for f in fixes["misquotes"]:
                lines.append(f"- **{f.get('case') or 'case'}** — your quote: “{f['quote']}”")
                if f.get("correct_passage"):
                    lines.append(f"  - Opinion says: “{f['correct_passage']}”")
                elif f.get("error"):
                    lines.append(f"  - _passage lookup failed: {f['error']}_")
                if f.get("corpus_note"):
                    lines.append(f"  - Corpus search: **{f.get('corpus_verdict')}** — {f['corpus_note']}")
                elif f.get("corpus_error"):
                    lines.append(f"  - _corpus search failed: {f['corpus_error']}_")
        if fixes.get("caution"):
            lines += ["", "### Caution cites — who gave the negative treatment", ""]
            for f in fixes["caution"]:
                neg = f.get("negative_citing") or []
                lines.append(f"- **{f.get('case')}** — {f.get('citation')} ({f.get('treatment_category') or 'caution'})")
                if neg:
                    for c in neg:
                        lines.append(f"  - {c.get('title') or c.get('case_id')} — {(c.get('treatment') or {}).get('category') or 'negative'}")
                    lines.append("  - _Check whether the point above touches your proposition; if not, the caution is noise._")
                elif f.get("error"):
                    lines.append(f"  - _drill failed: {f['error']}_")
                else:
                    lines.append("  - _no negative citing case surfaced — caution is likely on an unrelated sub-issue._")
        if fixes.get("unknown"):
            lines += ["", "### Unknown-treatment cites — existence/holding confirmation", ""]
            for f in fixes["unknown"]:
                status = "confirmed" if f.get("confirmed") else "NOT confirmed — verify against a primary source"
                lines.append(f"- **{f.get('case')}** — {f.get('citation')}: {status}")
                if f.get("summary"):
                    lines.append(f"  - {f['summary']}")
    return "\n".join(lines)
