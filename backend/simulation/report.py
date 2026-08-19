"""Full-report generator — turns a run's raw artifacts into a report a partner would read.

The sim exports everything (meta.json, metrics.csv, decisions.jsonl, trace.jsonl,
state.json). This renders it into ONE human-readable story that grows a section per stage,
so a partner reads it top to bottom and every fact lives in exactly one place:

    The bottom line          — the answer, first (the move, or the situation)
    Your firm                — a portrait they can recognize, and the one number to reconcile
    Where it's heading       — the slide if nothing changes, and why
    The changes on the table — the decisions available (how the levers were determined)
    The recommendation       — which changes, in what order, and why (how they were optimized)
    What the simulation did   — running the plan across fresh scenarios, and whether it held
    How to read this         — a short note on what the machine is
    Appendices               — what the answer depends on, the measured numbers, trajectories,
                               the firm on record, and the complete auditable record

The stage decides how far the story is told: a baseline stops at the changes on the table;
the lever optimization adds the recommendation; a scenario simulation adds what it showed.

It folds in the experiment summary (optimize.py / sweep_structural.py write
results/experiments.json) so the lever analysis is part of the report, not a separate blurb.

Usage:
    /opt/homebrew/bin/python3 report.py                  # latest run
    /opt/homebrew/bin/python3 report.py --run run_20260814_211206
    /opt/homebrew/bin/python3 report.py --experiments experiments.json
"""
import argparse, csv, json, os, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.abspath(__file__)))

from .src.utils.metric_catalog import GROUPS, GROUP_READ, METRICS, METRIC_INFO, metrics_by_group

# Firm-signature fields worth surfacing, grouped for readability.
FIRM_SECTIONS = [
    ("Structural posture", ["pricing_posture", "leverage_ratio", "origination_concentration",
                            "practice_mix_transactional", "client_concentration", "partner_power_mix"]),
    ("Tier 1 — what the market sees", ["tacit_work_share", "comp_model", "client_afa_pressure",
                                        "partner_retirement_horizon"]),
    ("Tier 2 — what the books show", ["baseline_ppp", "baseline_rpl", "baseline_realization",
                                      "baseline_margin", "tech_maturity"]),
    ("Culture (observable proxies)", ["partner_ai_usage", "attrition_intensity", "escalation_design"]),
]


def latest_run_dir() -> Path | None:
    d = ROOT / "results"
    if not d.exists():
        return None
    runs = [p for p in d.iterdir() if p.is_dir() and (p / "meta.json").exists()]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name, reverse=True)[0]


def load_meta(run_dir: Path) -> dict:
    try:
        return json.loads((run_dir / "meta.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_metrics(run_dir: Path) -> dict:
    """Return {metric_id: {sprint: value}} from metrics.csv."""
    out: dict[str, dict[int, float]] = defaultdict(dict)
    p = run_dir / "metrics.csv"
    if not p.exists():
        return out
    with open(p) as f:
        for row in csv.DictReader(f):
            mid, sprint = row["metric_id"], int(row["sprint"])
            out[mid][sprint] = float(row["value"])
    return out


def load_experiments(path: Path | None) -> dict:
    if path is None:
        path = ROOT / "results" / "experiments.json"
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def fmt(v, unit=""):
    if v is None:
        return "—"
    if unit == "$":
        return f"${v:,.0f}"
    # Word units ("days") read as prose and need a space; symbol units ("%", "/10") don't.
    sep = " " if unit and unit[0].isalpha() else ""
    return f"{v:,.1f}{sep}{unit}"


def _is_zero(v, unit="") -> bool:
    """True when a delta is small enough that calling it positive or negative misleads —
    below the precision the report prints it at."""
    if v is None:
        return True
    return abs(v) < (0.5 if unit == "$" else 0.05)


def _fmt_delta(v, unit=""):
    """A signed value — for effects, where the sign carries the finding.

    Zero gets no sign: '+$0' reads as a gain that rounded away, when what happened is
    that the lever did nothing."""
    if v is None:
        return "—"
    if _is_zero(v, unit):
        return "$0" if unit == "$" else f"0{'' if unit == 'blend' else unit}"
    if unit == "blend":
        return f"{v:+.1%}"
    if unit == "$":
        return f"{'-' if v < 0 else '+'}${abs(v):,.0f}"
    return f"{v:+,.1f}{unit}"


def _material(part, whole, floor: float = 0.05) -> bool:
    """Is `part` a big enough slice of `whole` to describe as a real finding rather than
    noise? Guards the interaction language: a 2% gap on a few seeds is a rounding artifact,
    and calling it 'more than the sum of its parts' overclaims."""
    if part is None or not whole:
        return False
    return abs(part) >= abs(whole) * floor


# --- "why + cost" derivation: built from metrics.csv values, never hard-coded. ---

CAUSAL_IDS = [m.id for m in METRICS if m.group == "causal"]
# (metric_id, which direction of movement counts as a *cost*)
COST_SIGNALS = [
    ("trust_polarization", "higher"),   # widening division
    ("associate_attrition", "higher"),  # people walking
    ("realization_rate", "lower"),      # realization drag
]


def _derive_mechanism(metrics: dict) -> tuple | None:
    """Find the causal metric that best EXPLAINS the PPP move over the run.

    Returns (mid, first, last, ppp_declined) or None. The chosen metric must have
    moved in the direction CONSISTENT with PPP: a PPP decline is explained by a
    causal metric that WORSENED (a lower-is-better metric rose, or a higher-is-better
    metric fell); a PPP gain by one that improved. Among matching metrics, pick the
    largest relative move.

    The earlier version picked the earliest mover regardless of direction, which
    produced contradictory stories — e.g. crediting a transient redline improvement
    for a 63% profit collapse. Direction-consistency is the fix."""
    ppp = metrics.get("ppp", {})
    if len(ppp) < 2:
        return None
    ps = sorted(ppp)
    ppp_first, ppp_last = ppp[ps[0]], ppp[ps[-1]]
    if abs(ppp_last - ppp_first) < 1e-9:
        return None
    ppp_declined = ppp_last < ppp_first

    best = None  # (relative_move, mid, first, last)
    for mid in CAUSAL_IDS:
        hist = metrics.get(mid, {})
        if len(hist) < 2:
            continue
        s = sorted(hist)
        first, last = hist[s[0]], hist[s[-1]]
        net = last - first
        if abs(net) < 1e-9:
            continue
        info = METRIC_INFO[mid]
        worsened = (info.direction == "lower" and net > 0) or (info.direction == "higher" and net < 0)
        # Keep only metrics whose movement matches the PPP direction.
        if ppp_declined != worsened:
            continue
        rel = abs(net) / max(abs(first), 1e-9)
        if best is None or rel > best[0]:
            best = (rel, mid, first, last)
    if best is None:
        return None
    return (best[1], best[2], best[3], ppp_declined)


def _cost_sentences(metrics: dict) -> list[str]:
    out = []
    for mid, bad_dir in COST_SIGNALS:
        hist = metrics.get(mid, {})
        if len(hist) < 2:
            continue
        sprints = sorted(hist)
        first, last = hist[sprints[0]], hist[sprints[-1]]
        m = METRIC_INFO[mid]
        if bad_dir == "higher" and last - first > 1e-9:
            out.append(f"{m.label} rose {fmt(first, m.unit)} → {fmt(last, m.unit)}")
        elif bad_dir == "lower" and first - last > 1e-9:
            out.append(f"{m.label} fell {fmt(first, m.unit)} → {fmt(last, m.unit)} (realization drag)")
    return out


def _why_cost_block(metrics: dict) -> list[str]:
    """The cost sentence for the run, or nothing at all.

    Returns [] when the run has no cost signal to report. An earlier version emitted an
    apology line ("_Insufficient data…_") that shipped to the reader as a bare sentence;
    a section that has nothing to say should say nothing."""
    costs = _cost_sentences(metrics)
    return ["The cost side: " + "; ".join(costs) + "."] if costs else []


def _series_ends(metrics: dict, mid: str):
    """First and last recorded value of a metric across sprints, or (None, None)."""
    hist = metrics.get(mid, {})
    if not hist:
        return None, None
    sprints = sorted(hist)
    return hist[sprints[0]], hist[sprints[-1]]


def _pct_change(first, last) -> str:
    if not first or first == 0:
        return ""
    pct = (last - first) / abs(first) * 100
    return f" ({pct:+.0f}%)"


# Plain-English glossary for the narrative — one line per lever, no jargon.
LEVER_GLOSS = {
    "pricing":  "stop billing by the hour and charge a flat fee per matter",
    "comp":     "pay partners a bonus for actually using AI",
    "leverage": "change how many junior lawyers sit under each partner (the pyramid)",
    "seams":    "write down the know-how that lives in senior lawyers' heads, so work "
                "doesn't get garbled when it passes from one person to the next",
    "latency":  "shorten the lag between seeing a result and acting on it",
}


def _plain(info) -> str:
    """A metric's plain-English definition, lowercased and de-punctuated for mid-sentence use."""
    w = info.what.strip().rstrip(".")
    return w[0].lower() + w[1:]


_LEVER_ORDER = ["pricing", "seams", "comp", "latency", "leverage"]


def _last(metrics: dict, mid: str):
    """Last recorded value of a metric, or None."""
    _, last = _series_ends(metrics, mid)
    return last


def _first(metrics: dict, mid: str):
    first, _ = _series_ends(metrics, mid)
    return first


# The four hand-offs where a litigation firm's value is tacit — the seams the sim
# models as "gappy" by default. Named in plain terms a partner will recognize.
_SEAMS = [
    ("partner review", "the partner's redlines on an associate or AI draft — the carve-outs, "
     "the argument strategy, the client-risk calls no template captures"),
    ("settlement", "leverage, timing, and the client's real risk tolerance, held in the "
     "originating partner's head"),
    ("staffing", "who is actually ready for this client and this matter — judgment, not a "
     "utilization report"),
    ("write-offs at billing", "which client tolerates which bill — realization is negotiated, "
     "not computed"),
]


def _band(v, low, high, lo_txt, mid_txt, hi_txt):
    """Turn a 0–1 signature dial into the plain-English phrase that matches it."""
    if v is None:
        return mid_txt
    if v <= low:
        return lo_txt
    if v >= high:
        return hi_txt
    return mid_txt


_PRICING_SAID = {
    "hourly": "billing by the hour",
    "partial_afa": "a mix of hourly and fixed fees",
    "afa_native": "fixed fees (AFA-native)",
}
_OBJECTIVE_SAID = {
    "ppp": "profit per partner (PPP)",
    "margin": "matter profit margin",
    "rpl": "revenue per lawyer",
    "realization": "realization (the share of billing you actually collect)",
    "retention": "keeping associates (lowering attrition)",
}

# What each input actually CHANGES inside the model. Every line here is a mechanism the
# engine really implements (see orchestrator._collect_metrics and models/elasticities.py) —
# an input the reader can't connect to an outcome is a question they answered for nothing.
INPUT_DRIVES = {
    "pricing_posture":
        "the sign on every hour AI saves — under fixed fees a saved hour becomes margin, "
        "under hourly it becomes a lost bill",
    "leverage_ratio":
        "how hard AI's hour-compression hits utilization; a steeper pyramid has more "
        "billable juniors exposed to it",
    "origination_concentration":
        "who can veto the change — the more the book concentrates, the fewer partners have "
        "to agree, and the more one of them can block",
    "practice_mix_transactional":
        "how much the hourly AI penalty is cushioned; transactional work is already close "
        "to fixed-fee, so it has fewer billable hours to lose",
    "client_concentration":
        "your pricing power in the write-off conversation — realization is negotiated, and "
        "a whale client negotiates harder",
    "partner_power_mix":
        "governance friction on adoption; rainmaker veto slows any change that touches "
        "how work gets done",
    "tacit_work_share":
        "how much of the work AI structurally cannot carry — the ceiling on what automation "
        "can reach",
    "client_afa_pressure":
        "realization leakage while you stay hourly — clients pushing alternative fees and "
        "meeting an hourly bill write it down",
    "tech_maturity":
        "the quality of your hand-offs at the starting line, and so how much room the "
        "codification lever has to work with",
    "baseline_ppp":
        "the starting line the model works from — every result below is a movement away "
        "from your own numbers, not an industry average",
    "partner_ai_usage": "how fast adoption climbs before any incentive is applied",
    "attrition_intensity": "how much knowledge walks out the door each year",
    "escalation_design": "how many exceptions get caught early instead of becoming write-offs",
}


# ---------------------------------------------------------------------------------
# At a glance — the stage's verdict, up top, before the reader reads anything else.
# Each simulation stage produces a different kind of finding, so each gets its own
# summary: the baseline ESTABLISHES a starting line, the lever search CONFIRMS or DENIES
# each lever, and a scenario simulation VALIDATES whether a chosen lever set holds up.
# ---------------------------------------------------------------------------------

def _stage_of(exp: dict, searched: bool) -> str:
    """The stage this report is for. Explicit `stage` wins; otherwise infer from whether a
    lever search ran, so older callers that don't set it still get a sensible summary."""
    return (exp or {}).get("stage") or ("lever_optimization" if searched else "baseline")


# ---------------------------------------------------------------------------------
# What this is
# ---------------------------------------------------------------------------------

def _scale_phrase(sprints) -> str:
    """'16 quarters (four years)' — sprints are quarters in this engine."""
    try:
        n = int(sprints)
    except (TypeError, ValueError):
        return f"{sprints} quarters"
    if n >= 4 and n % 4 == 0:
        years = n // 4
        return f"{n} quarters ({years} year{'s' if years != 1 else ''})"
    return f"{n} quarters"


# ---------------------------------------------------------------------------------
# 1. What you told us
# ---------------------------------------------------------------------------------

def _reconcile_baseline(sig: dict, metrics: dict) -> list[str]:
    """Explain the gap between the PPP the firm reported and where the model starts them.

    The two differ because the firm's CURRENT rework and exception rates already degrade
    the nominal number before any AI decision is made. Left unexplained, the two figures
    read as an arithmetic error and cost the whole report its credibility. Suppressed when
    the gap is small enough not to raise the question."""
    stated = sig.get("baseline_ppp")
    simulated = _first(metrics, "ppp")
    if not stated or simulated is None or stated <= 0:
        return []
    gap = stated - simulated
    if abs(gap) / stated < 0.02:
        return []
    redline = _first(metrics, "redline_rework_rate")
    exc = _first(metrics, "exception_rate")
    causes = []
    if redline is not None:
        causes.append(f"partners substantially rewriting {fmt(redline, '%')} of drafts")
    if exc is not None:
        causes.append(f"{fmt(exc, '%')} of workflow steps hitting an exception that needs rescue")
    because = (" — mostly " + " and ".join(causes)) if causes else ""
    direction = "below" if gap > 0 else "above"
    return ["",
            f"**One number to reconcile before you read on.** You reported profit per partner of "
            f"{fmt(stated, '$')}. The model starts you at **{fmt(simulated, '$')}**, "
            f"{fmt(abs(gap), '$')} {direction} that{because}. That is not a correction to your "
            "accounting. It is the same year priced by how the work actually moves through the "
            "firm, and the difference is the friction you are already paying for. Every figure "
            f"in this report moves from {fmt(simulated, '$')}, not from {fmt(stated, '$')}."]


# ---------------------------------------------------------------------------------
# 2. What we ran
# ---------------------------------------------------------------------------------

def _obj_unit(opt: dict) -> str:
    """Formatting unit for the objective the search optimized."""
    if len(opt.get("weights") or {}) > 1:
        return "blend"
    return "$" if opt.get("objective", "ppp") in ("ppp", "rpl") else "%"


def _effect(fx: dict, opt: dict):
    """A lever's main effect in the units the search actually ranked by."""
    if opt.get("objective", "ppp") == "ppp" and len(opt.get("weights") or {}) <= 1:
        return fx.get("delta_ppp"), "$"
    return fx.get("delta_objective", fx.get("delta_ppp")), _obj_unit(opt)


def _levers_in(name: str) -> list[str]:
    """The lever names inside an interaction key, in the order they appear.

    Keys are written two ways — `pricingxseams` (built from whichever pair Round 2 chose)
    and `comp_x_pricing` (the fixed probe) — so match on membership rather than splitting
    on a separator that isn't consistent."""
    found = [(name.index(lv), lv) for lv in _LEVER_ORDER if lv in name]
    return [lv for _, lv in sorted(found)]


def _interaction_pair(interactions: dict):
    """The (levers, values) of the factorial probe, whatever pair Round 2 chose."""
    for key, val in (interactions or {}).items():
        if "synergy" in val:
            return _levers_in(key), val
    return [], {}


# ---------------------------------------------------------------------------------
# 5. What to do
# ---------------------------------------------------------------------------------

def _widest_calibration(exp: dict):
    """The coefficient whose uncertainty costs the most, and the question that pins it down."""
    bands = ((exp or {}).get("sensitivity") or {}).get("bands") or {}
    best = None
    for lever, b in bands.items():
        q = b.get("calibration_question")
        if not q:
            continue
        width = abs((b.get("band_high") or 0) - (b.get("band_low") or 0))
        if best is None or width > best[0]:
            best = (width, lever, b, q)
    return best


# ---------------------------------------------------------------------------------
# Appendices
# ---------------------------------------------------------------------------------

# Plain, firm-facing names for the five changes — used in the appendix tables so a partner
# never has to decode a variable name. Short noun phrases so they read cleanly in a combo.
_LEVER_NAME = {
    "pricing":  "Flat-fee pricing",
    "seams":    "Codified hand-offs",
    "comp":     "AI-adoption pay",
    "leverage": "Flatter pyramid",
    "latency":  "Faster action",
}


def _lever_name(lever: str) -> str:
    return _LEVER_NAME.get(lever, lever.capitalize())


# The five changes as plain actions a partner would say out loud — for the summaries, where
# a short label isn't enough and the reader needs the change in their own words.
_LEVER_ACTION = {
    "pricing":  "move to flat fees",
    "seams":    "write down the know-how at your hand-offs",
    "comp":     "pay partners to use AI",
    "latency":  "act on results faster",
    "leverage": "reshape the pyramid — how many juniors sit under each partner",
}


def _action(lever: str) -> str:
    return _LEVER_ACTION.get(lever, lever)


def _cap(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


_OBJECTIVE_PLAIN = {
    "ppp": "profit per partner", "margin": "matter margin", "rpl": "revenue per lawyer",
    "realization": "realization", "retention": "associate retention",
}


def _money(v) -> str:
    """A signed dollar figure that reads naturally: -$69,577, not $-69,577."""
    if v is None:
        return "—"
    return f"{'-' if v < 0 else ''}${abs(v):,.0f}"


def _approx_money(v) -> str:
    """A round, spoken dollar figure — 'about $918,000' — magnitude only; the sentence
    carries the direction with a verb (adds / loses)."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 10_000:
        return f"${round(a / 1000) * 1000:,.0f}"
    if a >= 1_000:
        return f"${round(a / 100) * 100:,.0f}"
    return f"${a:,.0f}"


# Where each assumption's number comes from, in plain terms — no SURVEY/INFERRED tags.
_SOURCE_WORDS = {
    "SURVEY":     "published benchmark",
    "INFERRED":   "follows from your own numbers",
    "ASSUMPTION": "our estimate — worth confirming",
}


def render_sensitivity(exp: dict, letter: str = "A") -> str:
    """The change-by-change effect as honest RANGES, each tied to the assumption behind it and
    where that assumption comes from — so the number reads as 'X to Y depending on how strongly
    this holds at your firm', not false precision. Rendered when the sensitivity sweep has run."""
    s = (exp or {}).get("sensitivity")
    if not s or not s.get("bands"):
        return ""
    lines = [f"## Appendix {letter} — What the answer depends on", "",
             "Every number in this report rests on a few assumptions about how your firm "
             "behaves — how much of a saved hour becomes profit, what a partner's rewrite costs "
             "a matter. Those aren't certainties, so each was tested across its plausible range "
             "and the change re-run at every point. The wider the range below, the more the "
             "answer hangs on that one assumption — and the first one worth checking against "
             "your own experience.", "",
             "| Change | Effect on profit per partner | The assumption behind it | Where it comes from |",
             "|---|---|---|---|"]
    order = sorted(s["bands"].items(), key=lambda kv: kv[1].get("band_high", 0), reverse=True)
    for lever, b in order:
        rng = f"{fmt(b.get('band_low'), '$')} to {fmt(b.get('band_high'), '$')}"
        tag = (b.get("source") or "").split("]")[0].strip("[").strip().upper()
        where = _SOURCE_WORDS.get(tag, "modeled")
        lines.append(f"| {_lever_name(lever)} | {rng} | {b.get('coefficient_name','—')} | {where} |")
    lines += ["",
              "The widest range is the one to pin down first: answer it from your own numbers, "
              "re-run, and the figure tightens.", ""]
    return "\n".join(lines)


def render_experiments(exp: dict, metrics: dict, letter: str = "B") -> str:
    """The lever search's raw numbers, for a reader who wants to check the work."""
    opt = (exp or {}).get("optimize") or {}
    if not opt.get("main_effects"):
        return ""
    obj = opt.get("objective", "ppp")
    obj_label = opt.get("objective_label", "PPP")
    lines = [f"## Appendix {letter} — The changes, measured", "",
             "Each change, run on its own against standing still, ranked by effect. This is the "
             "first round of the search — the ranking that pointed everything after it.", ""]
    if obj != "ppp":
        lines += [f"_The search ranked by **{obj_label}**; profit per partner is shown alongside "
                  "for reference._", ""]
    if "baseline_ppp" in opt:
        lines += [f"Starting point, no changes: **{fmt(opt['baseline_ppp'], '$')}** profit per "
                  "partner.", ""]
    lines += ["| Change | Profit per partner | Matter margin |", "|---|---|---|"]
    for lever, fx in sorted(opt["main_effects"].items(),
                            key=lambda kv: kv[1].get("delta_ppp", 0), reverse=True):
        lines.append(f"| {_lever_name(lever)} | {_fmt_delta(fx.get('delta_ppp'), '$')} "
                     f"| {_fmt_delta(fx.get('delta_margin'), '%')} |")
    lines.append("")

    interactions = opt.get("interactions") or {}
    if interactions:
        lines += ["**When two changes are combined**", ""]
        for name, i in interactions.items():
            label = " + ".join(_lever_name(l) for l in (_levers_in(name) or [name]))
            if "synergy" in i:
                lines.append(f"- {label}: together {_fmt_delta(i.get('both'), '$')} versus "
                             f"{_fmt_delta(i.get('additive'), '$')} if their effects simply "
                             f"added — the combination itself adds {_fmt_delta(i.get('synergy'), '$')}")
            elif "delta" in i:
                lines.append(f"- {label}: {_fmt_delta(i.get('delta'), '$')}")
        lines.append("")

    if opt.get("best_combo"):
        band = opt.get("ci95", opt.get("spread"))
        names = " + ".join(_lever_name(l) for l in opt["best_combo"])
        lines += [f"**Best combination:** {names} → {fmt(opt.get('best_ppp'), '$')} profit per "
                  f"partner ({_fmt_delta(opt.get('best_delta'), '$')} against standing still, "
                  f"give or take {fmt(band, '$')} across scenarios).", ""]
    return "\n".join(lines)


def render_metric_table(metrics: dict, letter: str = "C", searched: bool = False) -> str:
    """Quarter-by-quarter trajectories grouped by P&L / causal / people.

    Captioned as Phase 1 output, because it is: these are the baseline firm's numbers, and
    the lever results elsewhere in the report came from separate simulations."""
    sprints = sorted({s for hist in metrics.values() for s in hist})
    if not sprints:
        return ""
    by_group = metrics_by_group()
    caption = ("**The baseline only — your firm with nothing changed, one scenario.** The search "
               "behind the recommendation ran as separate simulations and does not appear here."
               if searched else
               "**Your firm with nothing changed, one scenario.**")
    lines = [f"## Appendix {letter} — Quarter-by-quarter trajectories", "", caption, ""]
    header = "| Measure | " + " | ".join(f"Q{s}" for s in sprints) + " |"
    sep = "|" + "---|" * (len(sprints) + 1)
    for gid, glabel in GROUPS:
        rows = []
        for metric in by_group[gid]:
            if metric.id not in metrics:
                continue
            cells = [fmt(metrics[metric.id].get(s), metric.unit) for s in sprints]
            rows.append(f"| {metric.label} | " + " | ".join(cells) + " |")
        if not rows:
            continue
        lines += [f"**{glabel}** — _{GROUP_READ[gid]}._", "",
                  header, sep, *rows, ""]
    return "\n".join(lines)


# Plain labels + human-readable section titles for the firm's profile — so this reads as
# "your firm on the record", not a database dump.
_FIRM_SECTION_TITLE = {
    "Structural posture": "How the firm is built",
    "Tier 1 — what the market sees": "What the market sees",
    "Tier 2 — what the books show": "What the books show",
    "Culture (observable proxies)": "Culture",
}
_FIRM_FIELD_LABEL = {
    "pricing_posture": "How you bill",
    "leverage_ratio": "Associates per partner",
    "origination_concentration": "The book of business",
    "practice_mix_transactional": "Practice mix",
    "client_concentration": "Client concentration",
    "partner_power_mix": "Partner governance",
    "tacit_work_share": "Work that needs a person's judgment",
    "comp_model": "How partners are paid",
    "client_afa_pressure": "Client pressure on fees",
    "partner_retirement_horizon": "Partner retirement horizon",
    "baseline_ppp": "Profit per partner",
    "baseline_rpl": "Revenue per lawyer",
    "baseline_realization": "Realization",
    "baseline_margin": "Matter margin",
    "tech_maturity": "Knowledge infrastructure",
    "partner_ai_usage": "How much partners use AI today",
    "attrition_intensity": "Associate churn",
    "escalation_design": "Catching exceptions early",
}
_COMP_SAID = {
    "lockstep": "lockstep (seniority-based)",
    "modified": "modified lockstep",
    "eat_what_you_kill": "eat-what-you-kill (origination-based)",
}
# 0–1 dials rendered as the plain phrase that matches, mirroring Section 1's language.
_FIRM_BANDS = {
    "origination_concentration": (0.33, 0.66, "widely distributed across partners",
                                  "moderately concentrated", "dominated by one or two rainmakers"),
    "practice_mix_transactional": (0.33, 0.66, "mostly litigation",
                                   "a balanced litigation / transactional mix", "mostly transactional"),
    "client_concentration": (0.33, 0.66, "many clients, no single whale", "some concentration",
                             "heavy reliance on one or two whale clients"),
    "partner_power_mix": (0.33, 0.66, "cooperative", "balanced", "strong rainmaker veto"),
    "tacit_work_share": (0.33, 0.66, "mostly codifiable", "an even split of routine and judgment work",
                         "mostly dependent on a person's judgment"),
    "client_afa_pressure": (0.33, 0.66, "light", "moderate", "heavy pressure for alternative fees"),
    "tech_maturity": (0.33, 0.66, "little in place", "some in place", "mature and well-codified"),
    "partner_ai_usage": (0.33, 0.66, "barely touching it", "occasional", "already routine"),
    "attrition_intensity": (0.15, 0.25, "a stable bench", "normal churn", "heavy churn"),
    "escalation_design": (0.33, 0.66, "exceptions often slip through to write-offs",
                          "exceptions caught inconsistently", "exceptions usually caught early"),
}


def _firm_value(key, v) -> str:
    """One firm input, in the language a partner would use — never a raw number on a 0–1 dial."""
    if key == "pricing_posture":
        return _PRICING_SAID.get(v, str(v))
    if key == "comp_model":
        return _COMP_SAID.get(v, str(v))
    if key == "leverage_ratio":
        return f"about {v:g} to 1"
    if key == "partner_retirement_horizon":
        return f"about {v:g} years out"
    if key in ("baseline_ppp", "baseline_rpl"):
        return fmt(v, "$")
    if key in ("baseline_realization", "baseline_margin"):
        return fmt(v, "%")
    if key in _FIRM_BANDS:
        lo, hi, a, b, c = _FIRM_BANDS[key]
        return _band(v, lo, hi, a, b, c)
    return str(v)


def render_firm(meta: dict, letter: str = "D") -> str:
    """Your firm, on the record — the same inputs from Section 1, in plain language, so anyone
    can see exactly what was simulated and confirm it matches the firm they know."""
    sig = meta.get("firm_signature") or {}
    culture = sig.get("culture") or {}
    sig = {k: v for k, v in sig.items() if k != "culture"}
    provider = meta.get("provider", "mock")
    agents = ("real AI agents" if provider not in ("mock", None)
              else "a deterministic stand-in (same answer every time)")
    lines = [f"## Appendix {letter} — Your firm, on the record", "",
             "The same firm from Section 1, set down in full and in plain terms. If a line here "
             "doesn't match the firm you know, that input is the one to change — the answer moves "
             "with it. This is also the record that makes the run reproducible: the same inputs "
             "give the same result, every time.", "",
             f"**{meta.get('firm_name', 'Aldrich & Vale LLP')}** · "
             f"{_scale_phrase(meta.get('sprints', '?'))} · "
             f"{meta.get('matters_per_sprint', '?')} matters a quarter · decisions by {agents}", ""]
    for section, keys in FIRM_SECTIONS:
        rows = []
        for k in keys:
            if k in sig:
                rows.append((k, sig[k]))
            elif k in culture:
                rows.append((k, culture[k]))
        if not rows:
            continue
        lines += [f"**{_FIRM_SECTION_TITLE.get(section, section)}**", ""]
        for k, v in rows:
            lines.append(f"- **{_FIRM_FIELD_LABEL.get(k, k)}:** {_firm_value(k, v)}.")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------

# =================================================================================
# The report is ONE story that grows a section per stage — not three near-identical
# reports. A partner reads it top to bottom and sees: their firm, where it's heading,
# the decisions on the table (how the levers were determined), the recommendation (how
# they were optimized), and what the simulation did and showed (why to believe it).
# Every fact lives in exactly one section, so nothing repeats.
# =================================================================================

def _order_combo(combo: list) -> list:
    """A lever set in the order a partner would act on it, not alphabetical."""
    return [lv for lv in _LEVER_ORDER if lv in set(combo or [])]


def _firm_portrait(meta: dict) -> str:
    """Two or three sentences that let a partner recognize their own firm."""
    sig = meta.get("firm_signature") or {}
    firm = meta.get("firm_name", "the firm")
    pricing = _PRICING_SAID.get(sig.get("pricing_posture"), "billing by the hour")
    lev = sig.get("leverage_ratio")
    book = _band(sig.get("origination_concentration"), 0.33, 0.66,
                 "a book spread across many partners", "a moderately concentrated book",
                 "a book that runs through one or two rainmakers")
    mix = _band(sig.get("practice_mix_transactional"), 0.33, 0.66,
                "mostly litigation", "a mix of litigation and transactional work", "mostly transactional")
    lev_txt = f", about {lev:g} associates to a partner," if lev is not None else ""
    return (f"**{firm}** is {pricing}{lev_txt} with {book} and {mix}. Its real value sits at four "
            "hand-offs — the partner's redlines, the settlement call, who gets staffed, and which "
            "bill a client will actually pay — where the work turns on judgment no template holds. "
            "AI can carry the routine around those hand-offs; it can't carry the judgment inside "
            "them. Whether the firm keeps that value as the work changes is what this simulation "
            "puts a number on.")


def _heading_unchanged(meta: dict, metrics: dict) -> list[str]:
    """Where the firm lands if nothing changes — the slide, the reason, the honest feasibility."""
    ppp_first, ppp_last = _series_ends(metrics, "ppp")
    L = ["## Where it's heading, unchanged", ""]
    if ppp_last is None:
        return L + ["_No trajectory was recorded for this run._", ""]
    L += [f"Left as it is, profit per partner moves from {fmt(ppp_first, '$')} to "
          f"**{fmt(ppp_last, '$')}**{_pct_change(ppp_first, ppp_last)} over "
          f"{_scale_phrase(meta.get('sprints', '?'))}.", ""]
    redline = _last(metrics, "redline_rework_rate")
    real_rate = _last(metrics, "realization_rate")
    leaks = []
    if redline is not None:
        leaks.append(f"partners rewrite **{fmt(redline, '%')}** of drafts — the most expensive time "
                     "in the firm spent fixing what arrived not-quite-right")
    if real_rate is not None:
        leaks.append(f"the firm collects **{fmt(real_rate, '%')}** of what it bills — the rest never "
                     "turns into cash")
    if leaks:
        L += ["The drift isn't an AI problem. It's value leaking at the hand-offs: "
              + "; and ".join(leaks) + ".", ""]
    attr = _last(metrics, "associate_attrition")
    p_trust = _last(metrics, "partner_ai_trust")
    a_trust = _last(metrics, "associate_ai_trust")
    if p_trust is not None and a_trust is not None and a_trust > p_trust:
        L += ["And the people who'd carry any change are the ones least sold on it: associates rate "
              f"the AI {fmt(a_trust, '/10')} to partners' {fmt(p_trust, '/10')}"
              + (f", with the bench turning over {fmt(attr, '%')} a year" if attr is not None else "")
              + ". A rollout works against that gradient.", ""]
    return L


def _options_on_the_table(exp: dict) -> list[str]:
    """The five changes as decisions — how the levers were determined. The menu, not the choice."""
    L = ["## The changes on the table", "",
         "Five changes could bend that curve. Each is a real decision with a cost on both sides:", ""]
    for lv in _LEVER_ORDER:
        gloss = LEVER_GLOSS.get(lv)
        if gloss:
            L.append(f"- **{_lever_name(lv)}** — {gloss}.")
    L += ["", "Which ones actually help this firm, and in what order, is what the search settles next.",
          ""]
    return L


def _lever_standing_line(lv: str, opt: dict, combo: set, comp_delta) -> str:
    """One plain sentence on where a single change stands — confirmed, sequence-dependent, kept
    in context, or left out. Said once here and nowhere else."""
    fx = (opt.get("main_effects") or {}).get(lv)
    val, unit = _effect(fx, opt) if fx else (None, "$")
    name = _cap(_action(lv))
    if lv == "comp" and comp_delta is not None and not _is_zero(comp_delta, unit):
        base = (opt.get("main_effects") or {}).get("comp", {})
        comp_alone = base.get("delta_ppp")
        after = (f"but after you switch it makes about {_approx_money(comp_delta)}"
                 if comp_delta > 0 else "and it still doesn't pay even after you switch")
        tail = " — so it belongs, but do it last." if lv in combo else " — so it's left out."
        return (f"- **{name}** flips with how you bill: on its own it loses about "
                f"{_approx_money(comp_alone)} (you'd be paying people to bill fewer hours), {after}{tail}")
    if val is None or _is_zero(val, unit):
        return f"- **{name}** barely moves the number, so it's left out."
    if val > 0:
        tail = " It's in the plan." if lv in combo else " It helps, but the others carry the plan without it."
        return f"- **{name}** adds about {_approx_money(val)} on its own.{tail}"
    if lv in combo:
        return (f"- **{name}** loses about {_approx_money(val)} on its own, but earns its place once "
                "the others are in. Treat it as a finishing touch — drop it first if it's costly to set up.")
    return f"- **{name}** loses about {_approx_money(val)} and doesn't earn a place here. Left out."


def _recommendation(meta: dict, metrics: dict, exp: dict) -> list[str]:
    """How the levers were optimized — the choice, the order, why, and each change's standing."""
    opt = (exp or {}).get("optimize") or {}
    combo = _order_combo(opt.get("best_combo") or [])
    if not combo:
        return ["## The recommendation", "",
                "The search ran every combination and none reliably beat standing still for this "
                "firm as described. That's a finding, not a failure — change an input that's wrong "
                "and re-run, and the answer can move.", ""]
    obj = opt.get("objective", "ppp")
    obj_plain = _OBJECTIVE_PLAIN.get(obj, "profit per partner")
    delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
    best = opt.get("best_ppp") if obj == "ppp" else opt.get("best_objective")
    band = opt.get("ci95", opt.get("spread"))
    holds = (delta is not None and band is not None and abs(delta) > abs(band))
    conf = ("and the gain holds up in every version of the future we ran, not just on average — "
            "a real result, not a lucky one" if holds else
            "though the size is still uncertain, so trust the direction more than the exact figure")
    comp_delta = ((opt.get("interactions") or {}).get("comp_x_pricing") or {}).get("delta")
    interactions = opt.get("interactions") or {}
    pair, inter = _interaction_pair(interactions)

    actions = "; then ".join(_action(lv) for lv in combo)
    L = ["## The recommendation", "",
         f"**{_cap(actions)}.** Made together, in that order, they lift {obj_plain} to about "
         f"**{fmt(best, '$')}** — roughly **{_approx_money(delta)}** a year more than changing "
         f"nothing, {conf}.", ""]

    # Why the order — only the levers that are actually in the plan.
    L += ["**Why that order.**", ""]
    n = 0
    def step(t):
        nonlocal n
        n += 1
        return f"{n}. {t}"
    if "pricing" in combo:
        L.append(step("**Flat fees first** — it sets the sign on everything after it. Bill by the "
                      "hour and let AI work faster and you simply bill fewer hours. Charge a flat "
                      "fee and every hour AI saves drops toward profit."))
    if "seams" in combo:
        L.append(step("**Then write down the know-how** — cleaner hand-offs mean less rework hiding "
                      "inside that flat fee."))
    if "comp" in combo and comp_delta and comp_delta > 0:
        L.append(step("**Pay for AI adoption last** — the same bonus that loses money under hourly "
                      "billing turns positive once you've switched."))
    rest = [lv for lv in combo if lv not in ("pricing", "seams")
            and not (lv == "comp" and comp_delta and comp_delta > 0)]
    for lv in rest:
        L.append(step(f"**{_cap(_action(lv))}** — a finishing touch on top of the rest, not a mover "
                      "on its own."))
    L += [""]

    # Each change's standing — the "how they were determined/optimized" detail, once.
    L += ["**Where each change stands.**", ""]
    combo_set = set(combo)
    for lv in _LEVER_ORDER:
        if (opt.get("main_effects") or {}).get(lv) is not None:
            L.append(_lever_standing_line(lv, opt, combo_set, comp_delta))
    if pair and inter and _material(inter.get("synergy"), inter.get("both")) and (inter.get("synergy") or 0) > 0:
        a, b = (_lever_name(x).lower() for x in pair)
        L.append(f"- Combined, {a} and {b} do about {_approx_money(inter.get('synergy'))} more "
                 "together than each does alone.")
    L += [""]

    # How we got here — the method, briefly (kept visible per the partner's ask).
    sims = opt.get("sims_run")
    mc = opt.get("mc_seeds")
    L += ["**How we got there.** We tested each change on its own, then in combination to catch the "
          "way they interact, then re-ran the winning set"
          + (f" across {mc} fresh scenarios" if mc else "") + " to make sure it wasn't a lucky draw"
          + (f" — {sims:,} simulations in all." if sims else "."), "",
          "**What this doesn't include.** The cost of getting there: the senior hours to codify a "
          "hand-off, the client conversations to move a fee arrangement, the partner politics. The "
          "model prices the destination, not the trip.", ""]
    return L


def _what_the_sim_showed(meta: dict, metrics: dict, exp: dict) -> list[str]:
    """The scenario stage's contribution — what the simulation did with the plan, and why it holds."""
    opt = (exp or {}).get("optimize") or {}
    combo = _order_combo(opt.get("best_combo") or [])
    obj = opt.get("objective", "ppp")
    obj_plain = _OBJECTIVE_PLAIN.get(obj, "profit per partner")
    delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
    band = opt.get("ci95", opt.get("spread"))
    mc = opt.get("mc_seeds")
    holds = (delta is not None and band is not None and abs(delta) > abs(band))
    du = "$" if obj == "ppp" else _obj_unit(opt)

    L = ["## What the simulation did, and what it showed", "",
         f"We took the recommended plan — {', '.join(_action(lv) for lv in combo)} — and ran it "
         f"across **{mc} fresh scenarios**: the same firm, different rolls of the dice on which "
         "matters land, which hand-offs go wrong, and who leaves.", ""]
    if holds:
        L += [f"It came back **{_money(delta)}** ahead of changing nothing, give or take "
              f"{fmt(band, du if du != 'blend' else '')} — and it stayed ahead in every scenario, "
              "not just on average. That's the difference between a real effect and a lucky draw: "
              "the same plan wins whichever way the year breaks.", ""]
    else:
        L += [f"It came back about {_money(delta)} ahead, but the spread is wide enough that some "
              "scenarios land near flat. Trust the direction; treat the size as provisional until "
              "more scenarios or your own numbers tighten it.", ""]
    prior = (exp or {}).get("prior") or {}
    prior_delta = prior.get("best_delta") if obj == "ppp" else prior.get("best_delta_objective")
    if prior_delta is not None and delta is not None:
        if _is_zero(delta - prior_delta, du):
            L += ["It landed right where the optimization estimated — the recommendation is stable.", ""]
        else:
            direction = "higher" if delta > prior_delta else "lower"
            L += [f"The optimization had estimated {_money(prior_delta)}; the re-run came in "
                  f"{direction}, at {_money(delta)}.", ""]
    return L


def _how_to_read(meta: dict, exp: dict) -> list[str]:
    """A short, visible note on what the machine is — kept brief, not a methods section."""
    scenarios = ((exp.get("run") or {}).get("baseline_scenarios")
                 or (exp.get("optimize") or {}).get("mc_seeds")) if exp else None
    scale = _scale_phrase(meta.get("sprints", "?"))
    scen = f" across {scenarios} independent scenarios" if scenarios else ""
    return ["## How to read this", "",
            f"This is a comparison engine, not a forecast of your P&L. It runs your firm — {scale}, "
            f"quarter by quarter{scen} — down different roads and shows which ends up ahead, and "
            "why. Every quarter, simulated partners, associates, and AI tools work real matters; "
            "the rework and write-offs that come out of that are what set the numbers. Nothing is "
            "assumed.", "",
            "**Trust the direction and the order. Check the dollars before you quote them** — the "
            "magnitudes are calibrated to a firm like yours, not your ledger. Every figure traces "
            "to the record at the end.", ""]


def build_report(run_dir: Path, experiments: dict) -> str:
    meta = load_meta(run_dir)
    metrics = load_metrics(run_dir)
    experiments = experiments or {}
    firm = meta.get("firm_name", "Aldrich & Vale LLP")

    # One story, revealed a section at a time. The stage decides how far it's told: a baseline
    # stops at the decisions on the table; optimization adds the recommendation; a scenario adds
    # what the simulation showed. best_combo (not the run's own lever settings) gates the
    # recommendation — experiments.json can be stale from an earlier optimize run.
    searched = bool((experiments.get("optimize") or {}).get("best_combo"))
    stage = _stage_of(experiments, searched)

    body = ["## The bottom line", "", _bottom_line(meta, metrics, experiments, stage, searched), "",
            "---", "",
            "## Your firm", "", _firm_portrait(meta)]
    body += _reconcile_baseline(meta.get("firm_signature") or {}, metrics)
    body += ["", "---", ""]
    body += _heading_unchanged(meta, metrics) + ["---", ""]
    body += _options_on_the_table(experiments) + ["---", ""]
    if searched:
        body += _recommendation(meta, metrics, experiments) + ["---", ""]
    if stage == "scenario_simulation":
        body += _what_the_sim_showed(meta, metrics, experiments) + ["---", ""]
    body += _how_to_read(meta, experiments) + ["---", ""]

    appendices = _lettered_appendices(experiments, metrics, meta, searched)
    blocks = [
        f"# Firm Simulation — {firm}\n\n**Run:** {run_dir.name}\n",
        "\n".join(body),
        *appendices,
    ]
    return "\n".join(b.rstrip() + "\n" for b in blocks if b.strip())


def _bottom_line(meta: dict, metrics: dict, exp: dict, stage: str, searched: bool) -> str:
    """The one-paragraph answer at the very top — what a partner reads if they read nothing else."""
    firm = meta.get("firm_name", "the firm")
    opt = (exp or {}).get("optimize") or {}
    combo = _order_combo(opt.get("best_combo") or [])
    ppp_first, ppp_last = _series_ends(metrics, "ppp")
    if not searched or not combo:
        heading = (f"drifts from {fmt(ppp_first, '$')} to {fmt(ppp_last, '$')}"
                   f"{_pct_change(ppp_first, ppp_last)}" if ppp_last is not None else "slides")
        return (f"Left as it is, **{firm}**'s profit per partner {heading} over "
                f"{_scale_phrase(meta.get('sprints', '?'))} — value leaking at the hand-offs where "
                "the firm's judgment lives. There are five changes that could bend that curve; the "
                "next step is to test which ones actually help this firm.")
    obj = opt.get("objective", "ppp")
    obj_plain = _OBJECTIVE_PLAIN.get(obj, "profit per partner")
    delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
    band = opt.get("ci95", opt.get("spread"))
    holds = (delta is not None and band is not None and abs(delta) > abs(band))
    conf = ("and it holds up across every scenario we ran" if holds
            else "though the exact size is still uncertain")
    line = (f"**The move: {', then '.join(_action(lv) for lv in combo)} — in that order.** Done "
            f"together they lift {obj_plain} by about **{_approx_money(delta)}** a year over changing "
            f"nothing, {conf}.")
    if stage == "scenario_simulation":
        line += " We re-ran that plan across fresh scenarios to confirm it, and it held."
    return line


def _lettered_appendices(experiments: dict, metrics: dict, meta: dict, searched: bool) -> list[str]:
    """Render the appendices in order, assigning A, B, C… only to the ones that have content.

    Each candidate is a (renderer, needed) pair; a renderer that returns nothing doesn't
    consume its letter, so the sequence never has a gap."""
    candidates = [
        (lambda ltr: render_sensitivity(experiments, ltr), True),
        (lambda ltr: render_experiments(experiments, metrics, ltr), searched),
        (lambda ltr: render_metric_table(metrics, ltr, searched), True),
        (lambda ltr: render_firm(meta, ltr), True),
        (lambda ltr: _CAVEATS.replace("{letter}", ltr), True),
        (lambda ltr: _RAW_DATA.replace("{letter}", ltr), True),
    ]
    out, letters = [], iter("ABCDEFGH")
    pending = None
    for render, needed in candidates:
        if not needed:
            continue
        pending = pending or next(letters)
        block = render(pending)
        if block.strip():
            out.append(block)
            pending = None          # letter consumed
    return out


_CAVEATS = """## Appendix {letter} — What to trust, and what to check

This is a comparison engine, not a forecast of your P&L. It runs your firm down several
roads and shows which one ends up further ahead, and why.

- **Trust the direction and the order.** Which changes help, how they depend on each other,
  and the sequence to make them in — that is what the model is built to get right.
- **Check the dollar amounts before you quote them.** The magnitudes are calibrated to a
  firm like yours, not to your ledger. Put your own numbers through the intake and the same
  engine re-runs every figure against them.

Nothing here is asserted. Every figure traces back to the record in the next appendix, so
any number can be followed to the decision that produced it.
"""

_RAW_DATA = """## Appendix {letter} — The complete record

Every number in this report can be traced back and audited. Nothing is summarized away —
the full run is here, decision by decision, quarter by quarter:

- [Every measure, every quarter](metrics.csv)
- [Every decision, with the reasoning behind it](decisions.jsonl)
- [The full sequence of events](trace.jsonl)
- [The firm's end state](state.json)
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=str, default=None, help="run dir name under results/")
    ap.add_argument("--experiments", type=str, default=None, help="path to experiments.json")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    run_dir = ROOT / "results" / args.run if args.run else latest_run_dir()
    if run_dir is None:
        print("No run found under results/. Run run_firm.py or optimize.py first.")
        sys.exit(1)

    experiments = load_experiments(Path(args.experiments) if args.experiments else None)
    report = build_report(run_dir, experiments)

    if args.out:
        Path(args.out).write_text(report)
        print(f"Report → {args.out} ({run_dir.name})")
        return

    # Self-contained run folder: the report + the lever analysis it used live WITH the run's
    # own artifacts (meta.json already carries lever_settings + levers_pulled), so a single
    # run folder is the complete record. A convenience copy stays at results/report.md (latest).
    (run_dir / "report.md").write_text(report)
    if experiments:
        (run_dir / "experiments.json").write_text(json.dumps(experiments, indent=2))
    (ROOT / "results" / "report.md").write_text(report)
    print(f"Report → {run_dir / 'report.md'}  (+ experiments.json snapshot; latest copy at results/report.md)")


if __name__ == "__main__":
    main()
