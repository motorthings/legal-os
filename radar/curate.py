"""Descrybe-driven case-law curation — turn Descrybe search results into feed candidates.

The automated harvester (`fetchers.py`) covers RSS legal-tech news. Court opinions are
discovered semantically with Descrybe (`search_cases_by_concept` in the Claude session),
then transformed here into feed-schema rows, flagged for dedup against the KB, and
hand-attributed to fault lines before admission to feed.jsonl. Humans decide (backlog #5)
— Descrybe surfaces the candidates, a human vets and attributes them.

Usage:
    python radar/curate.py fault_line_id < descrybe-results.json   # emit candidates
    python radar/curate.py --all                                   # report KB overlap

The Descrybe results JSON is the `results` array from `search_cases_by_concept`
(one object per case: title, citation, court, decision_date, body, case_id, url, ...).
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from score import load_corpus, load_reviewed, REVIEWED_PATH, FEED_PATH
import ledger


def _tier(result):
    """Descrybe court -> radar tier. Court rulings are binding primary (T1); a trial-court
    order is still a ruling/sanction order (T1) but a human may downgrade a district
    order to T2. Conservative default: T1, and flag trial-court for review."""
    return "T1"


def _flag_trial_court(result):
    ot = (result.get("opinion_type") or "").lower()
    return "trialcourt" in ot


def descrybe_to_items(results, fault_lines):
    """Transform Descrybe search results into feed-schema items for the given fault lines.

    Each item carries the `fault_lines` it was surfaced for and an `in_kb` flag when the
    case (title or citation) already appears in the KB. A human reviews and adjusts the
    fault-line attribution before admitting."""
    corpus = load_corpus()
    items = []
    for r in results:
        date = (r.get("decision_date") or "")[:10]
        title = (r.get("title") or "").strip()
        if not title or not date:
            continue
        citation = (r.get("citation") or "").strip()
        item = {
            "date": date,
            "tier": _tier(r),
            "title": title,
            "source": (r.get("court") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "text": (r.get("body") or "").strip(),
            "citation": citation,
            "fault_lines": list(fault_lines),
            "empirical": False,
            "conflict": False,
            "case_id": r.get("case_id", ""),
        }
        item["in_kb"] = _already_in_kb(item, corpus)
        item["review"] = "trial court — confirm tier" if _flag_trial_court(r) else ""
        items.append(item)
    return items


def _already_in_kb(item, corpus):
    """Rough dedup signal: same case or authority already in the KB.

    Citation is the authoritative unique key: when both sides carry one and they differ,
    the two are distinct authorities (e.g. two "Colorado AI Act —" sections) and the
    title fallback is skipped. Otherwise fall back to title base-name matching (ignoring
    '— description' and 'Inc.' suffixes)."""
    title = item["title"].lower().strip().rstrip(".")
    cite = (item.get("citation", "") or "").lower()
    for kb in corpus:
        kb_title = (kb.get("title", "") or "").lower().strip()
        kb_base = kb_title.split("—")[0].split("–")[0].strip().rstrip(".")
        kb_text = (kb.get("text", "") or "").lower()
        kb_cite = (kb.get("citation", "") or "").lower()
        # Both carry a citation and they disagree -> different authorities.
        if cite and kb_cite and cite != kb_cite:
            continue
        if cite and (cite == kb_cite or cite in (kb_text + " " + kb_title)):
            return True
        if title and (title == kb_base or title == kb_title
                      or title.startswith(kb_base) or kb_base.startswith(title)):
            return True
    return False


def _feed_row(item):
    """A curated item -> the feed schema, in the same field order as the curated feed."""
    row = {
        "date": item["date"],
        "tier": item["tier"],
        "title": item["title"],
        "source": item["source"],
        "url": item["url"],
        "empirical": bool(item.get("empirical")),
        "conflict": bool(item.get("conflict")),
        "text": item.get("text", ""),
        "fault_lines": item.get("fault_lines", []),
    }
    if item.get("citation"):
        row["citation"] = item["citation"]
    return row


def admit(items, feed_path=FEED_PATH, dry_run=False):
    """Append reviewed, human-attributed items to the hand-curated feed.

    Skips anything already in the KB (by title/citation) and writes the rest in the
    curated feed schema. This is the deliberate, human-vouched path — distinct from the
    automated `ingest.admit()` that feeds the harvested store.

    Run-to-run memory: every curation decision is ALSO recorded to the admission ledger
    (decision="curated", reason="descrybe_discovery") so the ruling is traceable (who/
    when/why) and future runs can see it was already decided — not just via the KB's
    title/citation match, but via the append-only audit log. Returns the rows written."""
    corpus = load_corpus()
    written = []
    for it in items:
        if _already_in_kb(it, corpus):
            continue
        row = _feed_row(it)
        if not dry_run:
            with open(feed_path, "a") as f:
                f.write(json.dumps(row) + "\n")
            ledger.record_decision(row, "curated", "descrybe_discovery", scores={
                "fault_lines": row.get("fault_lines", []),
                "case_id": it.get("case_id", ""),
            })
        written.append(row)
        corpus.append(row)   # so a duplicate later in THIS batch is skipped too
    return written


def mark_reviewed(fault_line_ids):
    """Record that a human reviewed these fault lines today (history/reviewed.json).

    This is the fix for "stale but genuinely dormant": re-curation found nothing new, so
    mark the line reviewed. The scorer then reports reviewed_on/reviewed_days alongside
    stale_days, so the app can distinguish "stale + checked (dormant)" from "stale +
    unchecked (neglected)" — and the CI nudge stops re-flagging a dormant line every week.
    """
    reviewed = load_reviewed()
    today = date.today().isoformat()
    for fid in fault_line_ids:
        reviewed[fid] = today
    REVIEWED_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEWED_PATH.write_text(json.dumps(reviewed, indent=2, sort_keys=True) + "\n")
    return reviewed


def render(items):
    """Human-readable candidate list for review."""
    print(f"{len(items)} candidate items:\n")
    for it in items:
        mark = "IN-KB" if it["in_kb"] else "new  "
        cite = f" ({it['citation']})" if it.get("citation") else ""
        review = f"  [{it['review']}]" if it.get("review") else ""
        print(f"  {mark} {it['date']}  {it['tier']}  {it['title']}{cite}")
        print(f"      lines={it['fault_lines']}  court={it['source']}{review}")
        print(f"      {(it['text'] or '')[:160]}")
        print()


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: curate.py FAULT_LINE_ID [FAULT_LINE_ID ...] < descrybe-results.json")
        return 2
    fault_lines = [a for a in args if not a.startswith("--")]
    raw = sys.stdin.read()
    results = json.loads(raw) if raw.strip() else []
    if isinstance(results, dict):
        results = results.get("results", [])
    items = descrybe_to_items(results, fault_lines)
    render(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
