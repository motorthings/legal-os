"""Milestone grader — grade the record, not the future.

`calibration.py` grades the forecaster: it replays the engine before a ruling landed and
asks whether the right fault line was already elevated. That test is honest and it is
slow. Its outcome variable is a brand-new ruling on a fault line, which the freeze
window expects to accrue at 0-2 per quarter, so a defensible verdict needs 6-12 months.
The ground truth is also thin: three order-2 rulings on the whole record.

This module grades something denser and, for a firm, more useful: **antecedents**.

Most binding events do not arrive unannounced. A rule has a proposal, a comment period, a
bar committee, a first court. Those are dated, tier-stamped facts already on the record.
The lead time a firm actually needs (12-18 months to stand up a competence program or a
data-governance regime) is usually available from the antecedent, which means it does not
require a forecast at all. It requires reading.

So there are two different numbers here, and they answer different questions:

  LEAD TIME      Of the binding events on record, how long before each one did its
                 antecedent appear? -> the size of the window you can act in.
  BLINDSIDE RATE Of the binding events on record, how many had NO antecedent on the
                 record at all? -> the share that genuinely requires a forecast.

The blindside rate is the honest measure of what the prediction engine is for. If it is
low, the forecast is a nice-to-have and the record is the product. If it is high, the
forecast earns its keep. Either way the number is a fact about history, not a claim about
the future, so it can be reported today instead of in December.

Additive by design: this module reads `score.py` and `fault_lines.py` and never writes
them, so `python radar/freeze.py` still prints the committed fingerprint.
"""
from __future__ import annotations
import json
import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from score import score, load_corpus, _parse_date          # noqa: E402
import fault_lines as K                                     # noqa: E402
from calibration import CALL_THRESHOLD, LEAD_DAYS           # noqa: E402

MILESTONES_FILE = HERE / "history" / "milestones.jsonl"
STANDING = {"T1", "T2"}


def load_milestones(path=MILESTONES_FILE):
    if not Path(path).exists():
        return []
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def _resolve(ref, corpus):
    """Resolve a {date, match} reference to the corpus row it names.

    The reference carries a date and a title substring rather than a copied title, so a
    transcription slip in this file cannot silently invent evidence: if the row is not in
    the corpus, resolution fails loudly instead of grading against a typo.
    """
    if ref is None:
        return None
    hits = [i for i in corpus
            if i["date"] == ref["date"] and ref["match"].lower() in i["title"].lower()]
    if not hits:
        raise ValueError(
            f"milestone reference not found in corpus: {ref['date']} / {ref['match']!r}. "
            f"Either the row was removed from the feed or the reference is wrong."
        )
    if len(hits) > 1:
        raise ValueError(f"ambiguous milestone reference: {ref['date']} / {ref['match']!r} "
                         f"matches {len(hits)} corpus rows")
    return hits[0]


def _flagged(fault_id, as_of, corpus):
    """Was the fault line's ruling meter at/above the call threshold on this date?"""
    data = score(feed=corpus, as_of=as_of)
    for fl in data["fault_lines"]:
        if fl["id"] == fault_id:
            return fl.get("pressure")
    return None


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else round((xs[m - 1] + xs[m]) / 2, 1)


def grade(corpus=None):
    """Grade every milestone on the record. Returns the lead-time and blindside report."""
    corpus = corpus if corpus is not None else load_corpus()
    rows = []
    for m in load_milestones():
        ant = _resolve(m.get("antecedent"), corpus)
        bind = _resolve(m.get("binding"), corpus)
        status = m.get("status", "landed")
        lead_days = None
        if ant and bind:
            lead_days = (_parse_date(bind["date"]) - _parse_date(ant["date"])).days

        # The residual forecast question: was the line already elevated 90 days before
        # the antecedent appeared? This is the only column here that grades the engine
        # rather than the record, and it is reported separately for that reason.
        called_early = None
        if ant:
            probe = (_parse_date(ant["date"]) - timedelta(days=LEAD_DAYS)).isoformat()
            reading = _flagged(m["fault_line"], probe, corpus)
            called_early = reading is not None and reading >= CALL_THRESHOLD

        rows.append({
            "fault_line": m["fault_line"],
            "status": status,
            "antecedent": ant["title"] if ant else None,
            "antecedent_date": ant["date"] if ant else None,
            "antecedent_tier": ant["tier"] if ant else None,
            "binding": bind["title"] if bind else None,
            "binding_date": bind["date"] if bind else None,
            "binding_tier": bind["tier"] if bind else None,
            "lead_days": lead_days,
            "called_before_antecedent": called_early,
            "note": m.get("note", ""),
        })

    landed = [r for r in rows if r["status"] == "landed" and r["lead_days"] is not None]
    pending = [r for r in rows if r["status"] == "pending"]
    superseded = [r for r in rows if r["status"] == "superseded"]
    graded = [r for r in rows if r["called_before_antecedent"] is not None]

    return {
        "milestones": rows,
        "n_milestones": len(rows),
        "n_landed": len(landed),
        "n_pending": len(pending),
        "n_superseded": len(superseded),
        "lead_time_days": {
            "median": _median([r["lead_days"] for r in landed]),
            "min": min((r["lead_days"] for r in landed), default=None),
            "max": max((r["lead_days"] for r in landed), default=None),
        },
        # Of the controls whose binding event has not landed yet, which already have a
        # precursor on the record? This is the actionable list, and it is a statement
        # about the record, not a forecast.
        "actionable_now": [{"fault_line": r["fault_line"], "precursor": r["antecedent"],
                            "precursor_date": r["antecedent_date"]} for r in pending if r["antecedent"]],
        "engine_grade": {
            "n": len(graded),
            "called": sum(1 for r in graded if r["called_before_antecedent"]),
            "hit_rate": (round(sum(1 for r in graded if r["called_before_antecedent"]) / len(graded), 2)
                         if graded else None),
            "question": f"was the line flagged {LEAD_DAYS}d before the antecedent appeared?",
        },
        "not_a_forecast": ("Lead time is measured from antecedent to binding event. It is a fact "
                           "about the past, verifiable by reading the record, and requires no "
                           "prediction to act on."),
    }


def blindside_scan(corpus=None, as_of=None):
    """How many binding events had no precursor on the record at all?

    A first-order proxy, stated as one: for every standing-authority (T1/T2) item on a
    fault line, we ask whether any earlier standing-authority item existed on the SAME
    fault line. If not, the event arrived with nothing on the record to read ahead of it.
    That is a blindside, and it is the share of the problem a forecast would have to
    solve on its own.

    An earlier item on the same line is not proof of a precursor relationship, so treat
    this as a floor on the blindside rate, not an exact figure.

    CIRCULARITY WARNING. This scan runs over the curated feed, and the feed was assembled
    knowing how these events turned out. A curator who knows a rule was coming tends to
    include the committee report that preceded it, which makes the blindside rate read
    LOW by construction. This is the same hindsight problem `FREEZE.md` describes for the
    backtest, and it lands the same way: the number is a lower bound on blindness, useful
    for comparing lines against each other, and not a claim about how often a firm would
    actually have been blindsided in real time.
    """
    corpus = corpus if corpus is not None else load_corpus()
    as_of = as_of or max(i["date"] for i in corpus)
    standing = [i for i in corpus if i.get("tier") in STANDING and i["date"] <= as_of]

    earlier_by_line = {}
    blinded = []
    for item in sorted(standing, key=lambda i: i["date"]):
        lines = item.get("fault_lines") or []
        for fid in lines:
            if not earlier_by_line.get(fid):
                blinded.append({"date": item["date"], "tier": item["tier"],
                                "fault_line": fid, "title": item["title"]})
            earlier_by_line.setdefault(fid, []).append(item["title"])

    n_events = sum(1 for i in standing for _ in (i.get("fault_lines") or []))
    return {
        "n_standing_events": n_events,
        "n_no_precursor": len(blinded),
        "blindside_rate": round(len(blinded) / n_events, 2) if n_events else None,
        "blindside_events": blinded,
        "method": ("floor, not an exact rate: 'precursor' = any earlier T1/T2 item on the "
                   "same fault line, which is a proxy for a real antecedent relationship"),
    }


def render_text(report, blindside=None):
    L = []
    lt = report["lead_time_days"]
    L.append(f"Milestone grader — {report['n_landed']} landed · "
             f"{report['n_pending']} pending · {report['n_superseded']} superseded")
    if lt["median"] is not None:
        L.append(f"  lead time antecedent -> binding: median {lt['median']}d "
                 f"(min {lt['min']}d, max {lt['max']}d)")
    L.append("")
    L.append(f"{'FAULT LINE':<20}{'STATUS':<12}{'LEAD':>7}  ANTECEDENT")
    L.append("-" * 88)
    for r in report["milestones"]:
        lead = f"{r['lead_days']}d" if r["lead_days"] is not None else "—"
        ant = (r["antecedent"] or "")[:44]
        L.append(f"{r['fault_line']:<20}{r['status']:<12}{lead:>7}  {ant}")
    L.append("")
    if report["actionable_now"]:
        L.append("Actionable now (precursor on the record, no binding event yet):")
        for a in report["actionable_now"]:
            L.append(f"  {a['fault_line']:<20} {a['precursor_date']}  {a['precursor'][:52]}")
        L.append("")
    eg = report["engine_grade"]
    L.append(f"Engine: {eg['called']}/{eg['n']} flagged {LEAD_DAYS}d before the antecedent "
             f"({eg['question']})")
    if blindside:
        L.append(f"Blindside: {blindside['n_no_precursor']}/{blindside['n_standing_events']} "
                 f"standing events had no earlier item on their line "
                 f"(rate {blindside['blindside_rate']})")
    return "\n".join(L)


def main():
    report = grade()
    print(render_text(report, blindside_scan()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
