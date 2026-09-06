"""Compose the radar's Knowledge Base: every source doc the radar holds, what it is,
and a deterministic, auto-derived 'why it's in the KB' string.

The KB is the source library itself (radar/sources/feed.jsonl). score.py scores
fault lines but drops each doc's `text` summary and never exposes the whole feed as
an inventory. This module emits that inventory so the app can show it.

Deterministic pure function of (feed, fault_lines config): no timestamps, no
randomness — replay stays byte-identical, matching the radar's ethos. The per-doc
"why" is composed here from tier authority, the doc's lane role, and the fault
line(s) it evidences, so both the static docs page and the in-app page read the same
authoritative string instead of re-deriving the language in two places.
"""
import json
from pathlib import Path

import fault_lines as K
from score import _matches, load_feed, FEED_PATH

# Lane verbs mirror the page copy: L1 = a demonstration AI can now do the thing,
# L2 = a court/bar/regulator acting, L3 = the market making the fix table stakes.
ROLE_CLAUSE = {
    "L1 capability": "It is an L1 capability signal — a demonstration that AI can now do the thing.",
    "L2 ruling": "It is L2 ruling evidence — a court, bar, or regulator acting.",
    "L3 adoption": "It is an L3 adoption signal — evidence the control is becoming table stakes, court or no court.",
}

# Preferred display order for the role pills.
_ROLE_RANK = {"L1 capability": 1, "L2 ruling": 2, "L3 adoption": 3}

_EMPIRICAL_BOOST = K.EMPIRICAL_BOOST
_CONFLICT_DISCOUNT = K.CONFLICT_DISCOUNT


def _authority(tier):
    """Tier authority phrasing, e.g. 'Binding / primary authority (weight 1.00)'."""
    info = K.SOURCE_TIERS[tier]
    return f"{info['label']} authority (weight {info['weight']:.2f})"


def _matched_fault_lines(item):
    """Fault lines this doc evidences. Curated `fault_lines` (where present) wins;
    otherwise reuse the same signal match that drives the meters. Resolves to
    [{id, title}]."""
    curated = item.get("fault_lines")
    if curated:
        return [
            {"id": fid, "title": (K.fault_line_by_id(fid) or {}).get("title", fid)}
            for fid in curated
        ]
    return [
        {"id": fl["id"], "title": fl["title"]}
        for fl in K.FAULT_LINES if _matches(item, fl)
    ]


def _role(item, matched):
    """Deterministic lane(s) the doc feeds. Capability/market classes name their own
    lanes. A doc is ALSO L2 ruling evidence when it is standing authority (a court,
    bar, or regulator — T1/T2) or when it is an un-laned signal sitting on a fault
    line. A T3 capability demo or pure market signal is never called a 'ruling.'"""
    role = []
    if item.get("capability") in K.CAPABILITY_WEIGHTS:
        role.append("L1 capability")
    if item.get("market") in K.MARKET_WEIGHTS:
        role.append("L3 adoption")
    is_standing = item["tier"] in K.STANDING_TIERS  # T1/T2 never decay; they are authority
    has_lane_key = bool(item.get("capability")) or bool(item.get("market"))
    if matched and (is_standing or not has_lane_key):
        role.append("L2 ruling")
    if not role:
        role = ["tracked"] if not matched else ["L2 ruling"]
    return sorted(role, key=lambda r: _ROLE_RANK.get(r, 99))


def _flag_note(item):
    """Empirical / conflict note appended when the source carries one of the flags."""
    bits = []
    if item.get("empirical"):
        bits.append(f"it carries hard data (weight ×{_EMPIRICAL_BOOST:.2f})")
    if item.get("conflict"):
        bits.append(f"the source sells what it comments on (weight ×{_CONFLICT_DISCOUNT:.1f})")
    return ("Note: " + " and ".join(bits) + ".") if bits else ""


def _why(item, matched, role):
    names = ", ".join(f['title'] for f in matched)
    evidence_phrase = (
        f"It evidences the {names}." if names
        else "It is not yet tied to a specific fault line."
    )
    lines = [f"{_authority(item['tier'])}. {evidence_phrase}"]
    lines.extend(ROLE_CLAUSE[r] for r in role if r in ROLE_CLAUSE)
    note = _flag_note(item)
    if note:
        lines.append(note)
    return " ".join(lines)


def compose(feed=None):
    """Return the full KB inventory as a dict (written to kb.json by build.py)."""
    if feed is None:
        feed = load_feed()
    items = []
    for item in feed:
        matched = _matched_fault_lines(item)
        role = _role(item, matched)
        items.append({
            "date": item["date"],
            "tier": item["tier"],
            "tier_label": K.SOURCE_TIERS[item["tier"]]["label"],
            "tier_weight": K.SOURCE_TIERS[item["tier"]]["weight"],
            "title": item["title"],
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "empirical": bool(item.get("empirical")),
            "conflict": bool(item.get("conflict")),
            "capability": item.get("capability"),
            "market": item.get("market"),
            "order": item.get("order"),
            "what": item.get("text", ""),
            "role": role,
            "fault_lines": matched,
            "why": _why(item, matched, role),
        })
    return {"n_items": len(items), "items": items}


if __name__ == "__main__":
    kbd = compose()
    print(f"{kbd['n_items']} source docs in the KB.")
    for it in kbd["items"]:
        print(f"\n- {it['tier']} {it['date']} {it['title']}")
        print(f"  role={it['role']} lines={[f['id'] for f in it['fault_lines']]}")
        print(f"  WHY: {it['why']}")
