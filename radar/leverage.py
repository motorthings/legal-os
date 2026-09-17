"""Leverage layer — who can withhold what, and did they actually require it.

The adoption meter measures how much market evidence a control has. That is not the same
question as whether the control is table stakes, and `EXPECTED_ADOPTION = 7.0` was trying to
bridge the two with a number. It could not, for three reasons measured on 2026-09-17:

  - the threshold was nearly inert: with leverage gating in place it could reach only two
    lines (`insurance` 8.1, `fees` 5.3) and sweeping it 0-10 moved at most two verdicts;
  - there was nothing to fit to: three order-3 rows exist, one of which is a court broadening
    a duty (pressure wearing an adoption label) and one of which the feed itself describes as
    a proposal. One clean event;
  - the meter it thresholded rested on three items across eleven lines, two of them the same
    carrier.

So the number is retired from the decision and this layer replaces it. A control is table
stakes when a NAMED ACTOR who can withhold something requires it: the insurer withholds
coverage, the client withholds the engagement, the court withholds the docket. That is a
countable fact about the record, not a threshold.

This is a LABELING layer, like `history/resolutions.jsonl` and `history/milestones.jsonl`.
It never writes a frozen input, so editing it cannot void the freeze. Rows are keyed to feed
items by date + title substring and resolved against the corpus at load time, so a
transcription slip fails loudly instead of inventing evidence.

A row with `"requirement": null` is a REVIEWED-AND-EXCLUDED case. It is kept, and counted
separately, because "this looked like leverage and is not" is a finding — the same reason
`milestones.jsonl` keeps the Colorado direction-shift.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from score import load_corpus                                  # noqa: E402
from milestones import _resolve                                # noqa: E402  (one integrity guard)
import fault_lines as K                                        # noqa: E402

LEVERAGE_FILE = HERE / "history" / "leverage.jsonl"


def load_leverage(path=LEVERAGE_FILE):
    if not Path(path).exists():
        return []
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def default_corpus():
    """The live corpus when one exists, else the frozen curated feed.

    The advisory reads the refreshable landscape, so a leverage row should be able to name a
    live-only item. Falling back to the frozen corpus keeps this working before the first
    live build, and a row naming an item in NEITHER raises rather than silently dropping.
    """
    try:
        import live
        return live.live_corpus()
    except Exception:
        return load_corpus()


def rows(corpus=None):
    """Resolve every leverage row against the corpus. Raises on an unresolvable reference."""
    corpus = corpus if corpus is not None else default_corpus()
    out = []
    for r in load_leverage():
        item = _resolve({"date": r["date"], "match": r["match"]}, corpus)
        out.append({**r, "tier": item["tier"], "title": item["title"]})
    return out


def requirements(corpus=None):
    """Only the rows that name an actor who actually requires the control."""
    return [r for r in rows(corpus) if r.get("requirement") and r.get("actor")]


def excluded(corpus=None):
    """Rows reviewed and rejected as leverage. Surfaced, not dropped."""
    return [r for r in rows(corpus) if not (r.get("requirement") and r.get("actor"))]


def by_fault_line(corpus=None):
    """{fault_line: [requirement, ...]} — what the gate reads."""
    out = {}
    for r in requirements(corpus):
        out.setdefault(r["fault_line"], []).append(r)
    return out


def facts(corpus=None):
    """The full picture, memoized by the caller. Actors are de-duplicated so a carrier that
    says the same thing twice counts once — the bug that made `insurance` look like it had
    two independent signals when it had one."""
    reqs = requirements(corpus)
    by_line = {}
    for r in reqs:
        by_line.setdefault(r["fault_line"], {})
        by_line[r["fault_line"]].setdefault(r["actor"], []).append(r)
    return {
        "requirements": reqs,
        "excluded": excluded(corpus),
        "by_fault_line": by_line,
        "actors_by_line": {k: sorted(v) for k, v in by_line.items()},
    }


def actor_match(actor, named):
    """Is `actor` one of the actors the firm named as having leverage over it?
    Case-insensitive substring, so 'CNA' matches 'CNA Financial'.

    Both sides are guarded against empty: `"" in "cna"` is True, so an unguarded check would
    let a row with no actor match EVERY named carrier, quietly upgrading a generic market
    signal to "your own carrier requires this."
    """
    a = (actor or "").strip().lower()
    if not a or not named:
        return False
    return any(n and n.strip() and (n.strip().lower() in a or a in n.strip().lower())
               for n in named)


def render_text(f):
    L = []
    L.append(f"Leverage layer — {len(f['requirements'])} requirement(s), "
             f"{len(f['excluded'])} reviewed and excluded")
    L.append("")
    for fid, actors in sorted(f["by_fault_line"].items()):
        for actor, rs in sorted(actors.items()):
            L.append(f"  {fid:<15} {actor:<10} withholds {rs[0].get('withheld') or '—':<10} "
                     f"{rs[0]['requirement'][:56]}")
    if f["excluded"]:
        L.append("")
        L.append("  reviewed, NOT leverage:")
        for r in f["excluded"]:
            L.append(f"    {r['fault_line']:<15} {r['title'][:64]}")
    return "\n".join(L)


if __name__ == "__main__":
    print(render_text(facts()))
    print()
    print("Actor classes that count:", sorted(K.LEVERAGE_CLASSES))
