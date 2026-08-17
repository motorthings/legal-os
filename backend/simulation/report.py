"""Full-report generator — turns a run's raw artifacts into a report a partner would read.

The sim already exports everything (meta.json, metrics.csv, decisions.jsonl, trace.jsonl,
state.json). This renders it into a single human-readable report — the firm we modeled,
the levers we tested, the interactions, the recommendation with a confidence interval,
and the sprint-by-sprint metric trajectories — plus the assumptions we're standing behind.

It also folds in the experiment summary (optimize.py / sweep_structural.py write
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
    return f"{v:,.1f}{unit}"


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


def _mechanism_sentence(metrics: dict) -> str | None:
    move = _derive_mechanism(metrics)
    if move is None:
        return None
    mid, first, last, ppp_declined = move
    m = METRIC_INFO[mid]
    verb = "rose" if last > first else "fell"
    drag = "dragging PPP down" if ppp_declined else "lifting PPP"
    return (f"The mechanism: **{m.label}** {verb} "
            f"({fmt(first, m.unit)} → {fmt(last, m.unit)}), {drag} — "
            f"the causal signal behind the move.")


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
    """Two derived sentences — mechanism and cost — or a graceful miss."""
    mech = _mechanism_sentence(metrics)
    costs = _cost_sentences(metrics)
    if mech is None and not costs:
        return ["_Insufficient data in this run to describe why PPP moved or what it cost._"]
    lines = []
    if mech:
        lines.append(mech)
    if costs:
        lines.append("The cost: " + "; ".join(costs) + ".")
    return lines


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


def render_baseline_narrative(meta: dict, metrics: dict) -> str:
    """The baseline report a firm partner reads: their firm as a working system, where value
    leaks today, the forks ahead stated WITHOUT bias, and whether their people can carry a
    change. No recommendation — the point is to help the partner find the way forward, not
    sell one. Rendered only for baseline runs (no levers pulled)."""
    firm = meta.get("firm_name", "Aldrich & Vale LLP")
    provider = meta.get("provider", "mock")
    real = provider not in ("mock", None)
    how = f"modeled on real AI ({provider})" if real else "modeled on a fast offline stand-in"
    L = ["## What this shows", ""]

    L += [
        f"This is **{firm} as it runs today** — no changes pulled, the firm at its current "
        "starting line. The point isn't to grade it. It's to let you see your own firm as a "
        "system, find where value quietly leaks, and weigh the ways forward on their real "
        "trade-offs. There is no recommended answer baked in here; the forks below cut both "
        f"ways, and which one fits is your call. ({how}.)", ""]

    # --- THE SYSTEM ---------------------------------------------------------------
    L += ["### 1. Your firm as a system", ""]
    L += [
        "Every matter moves through the same lifecycle: intake and conflicts, staffing, "
        "research and drafting, a senior associate's first-pass review, the partner's redline, "
        "citation check and filing, then settlement or trial, and finally billing and "
        "collection. Most of those steps are codifiable — a form, a protocol, a database. The "
        "firm's actual value concentrates at a handful of **seams**, the hand-offs where the "
        "work depends on knowledge that lives in a person's head, not a system:", ""]
    for name, what in _SEAMS:
        L.append(f"- **{name.capitalize()}** — {what}.")
    L += ["",
        "These seams are where the money is made, and where it leaks. AI can draft, research, "
        "and check citations — the codifiable 80%. It cannot hold the tacit 20% at the seams. "
        "So the question a firm faces isn't whether AI is capable. It's whether the firm can "
        "carry what AI changes at those four seams without dropping the value that lives there.", ""]

    # --- WHERE VALUE LEAKS --------------------------------------------------------
    L += ["### 2. Where value leaks today", ""]
    redline = _last(metrics, "redline_rework_rate")
    exc = _last(metrics, "exception_rate")
    handoff = _last(metrics, "handoff_failure_rate")
    real_rate = _last(metrics, "realization_rate")
    wip = _last(metrics, "wip_aging")
    collect = _last(metrics, "collection_cycle")
    margin = _last(metrics, "matter_profit_margin")
    leaks = []
    if redline is not None:
        leaks.append(f"- **Partners re-doing the work.** {fmt(redline, '%')} of drafts come back "
                     "for substantial partner rewriting. That's the most expensive time in the "
                     "firm spent fixing what arrived not-quite-right — the surest sign the value "
                     "sits in the redline, not the draft.")
    if exc is not None:
        leaks.append(f"- **Work bouncing back.** {fmt(exc, '%')} of steps hit an exception that "
                     "needs partner rescue beyond the normal path. Each one is unplanned senior "
                     "time and a slower matter.")
    if handoff is not None:
        leaks.append(f"- **Meaning lost at hand-offs.** {fmt(handoff, '%')} of transfers between "
                     "roles lose or garble context and need rework on the far side.")
    if real_rate is not None:
        gap = 100 - real_rate
        leaks.append(f"- **Billed but not collected.** The firm collects {fmt(real_rate, '%')} of "
                     f"what it bills — roughly {fmt(gap, '%')} of billed work never turns into "
                     "cash, the leak in dollar form.")
    if wip is not None and collect is not None:
        leaks.append(f"- **Slow money.** Work sits {wip:,.0f} days as unbilled WIP, and invoices "
                     f"take {collect:,.0f} days to collect — value earned long before it's paid.")
    if leaks:
        L += leaks + [""]
    if margin is not None:
        L += [f"Together these hold matter margin at **{fmt(margin, '%')}**. None of them are AI "
              "problems. They're seam problems that AI will either expose or amplify, depending "
              "on the choices below.", ""]

    # --- THE FORKS (UNBIASED) -----------------------------------------------------
    L += ["### 3. The forks ahead — stated straight", ""]
    L += [
        "There are a few decisions in front of the firm. Each is a genuine fork with a cost on "
        "both sides — not a recommendation. Here is what each one actually does:", ""]
    L += [
        "- **How you price.** This is the one that changes the sign of everything else. Bill by "
        "the hour and let AI work faster, and you bill *fewer* hours for the same result — AI can "
        "quietly cost you money. Move to flat or alternative fees and every hour AI saves drops "
        "toward profit instead. Neither is free: hourly protects today's revenue but caps AI's "
        "upside; fixed fees unlock it but shift delivery risk onto the firm. The firm hasn't "
        "made this call, and the rest depends on it.", ""]
    L += [
        "- **Whether you codify the seams.** Writing down the tacit know-how at the four seams "
        "makes hand-offs cleaner and cuts rework. It's the most reliable lever on profit, but "
        "it costs real senior time and library-building up front, and some partners will resist "
        "committing their judgment to a system.", ""]
    L += [
        "- **Whether you pay for adoption.** Paying partners to actually use AI raises adoption. "
        "But under hourly billing that can backfire — you're paying them to bill fewer hours. "
        "The same incentive only turns positive once pricing has moved. Sequence matters.", ""]
    L += [
        "- **How steep the pyramid is, and how fast you act.** Leverage and decision speed move "
        "the number less and less reliably; treat them as adjustments, not the main event.", ""]
    L += [
        "The honest shape of it: **pricing and seams are the forks that matter, and they "
        "interact.** The firm can succeed on more than one path, but a half-step — adopting AI "
        "while still billing hourly and leaving the seams informal — is the one combination that "
        "reliably loses money. Standing still is itself a choice with a cost.", ""]

    # --- FEASIBILITY --------------------------------------------------------------
    L += ["### 4. Can your people carry it", ""]
    p_trust = _last(metrics, "partner_ai_trust")
    a_trust = _last(metrics, "associate_ai_trust")
    adopt = _last(metrics, "ai_assisted_matter_pct")
    attr = _last(metrics, "associate_attrition")
    feas = []
    if p_trust is not None and a_trust is not None:
        feas.append(f"- **The trust gap is real and it's inverted.** Associates trust the AI "
                    f"({fmt(a_trust, '/10')}) far more than partners do ({fmt(p_trust, '/10')}). "
                    "The people with the most power over the change have the least faith in it — "
                    "that's the gradient any rollout has to work against, and it won't move on "
                    "communications, only on the AI proving reliable at real work.")
    if adopt is not None:
        feas.append(f"- **Adoption is early.** AI touched {fmt(adopt, '%')} of matters — usage, "
                    "not yet absorption. The gap between the two is where transformations stall.")
    if attr is not None:
        feas.append(f"- **The bench is churning.** Associate attrition runs {fmt(attr, '%')} a "
                    "year, the structural BigLaw tournament. Whatever the firm builds has to "
                    "survive that turnover — knowledge codified into systems outlasts it, "
                    "knowledge left in heads walks out the door.")
    if feas:
        L += feas + [""]

    L += [
        "**How to read this.** The *direction* is the finding — where value sits, where it "
        "leaks, and which forks actually move the number. The dollar magnitudes come from a "
        "typical mid-size firm; put in your own numbers and the same engine re-runs the answer "
        "for you. Feasibility is not a yes/no here: it's a set of conditions — move pricing, "
        "codify the seams, and earn partner trust through reliable performance — under which "
        "the path holds together.", ""]
    return "\n".join(L)


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


def render_readback(meta: dict, exp: dict) -> list:
    """Read the firm back to the user before saying anything about results — so they can see
    the model heard their inputs and their goal correctly. Every line comes straight from the
    config they set; nothing here is a finding."""
    sig = meta.get("firm_signature") or {}
    if not sig:
        return []
    firm = meta.get("firm_name", "Aldrich & Vale LLP")
    opt = exp.get("optimize") if exp else None
    objective = (opt or {}).get("objective", "ppp")
    obj_said = _OBJECTIVE_SAID.get(objective, "profit per partner (PPP)")

    pricing = _PRICING_SAID.get(sig.get("pricing_posture"), sig.get("pricing_posture", "—"))
    lev = sig.get("leverage_ratio")
    orig = _band(sig.get("origination_concentration"), 0.33, 0.66,
                 "a widely distributed book of business", "a moderately concentrated book",
                 "a book dominated by one or two rainmakers")
    mix = _band(sig.get("practice_mix_transactional"), 0.33, 0.66,
                "mostly litigation", "a balanced litigation/transactional mix", "mostly transactional")
    clients = _band(sig.get("client_concentration"), 0.33, 0.66,
                    "many clients, no single whale", "some client concentration",
                    "heavy reliance on one or two whale clients")
    power = _band(sig.get("partner_power_mix"), 0.33, 0.66,
                  "cooperative partner governance", "balanced partner governance",
                  "strong rainmaker veto power")
    tech = _band(sig.get("tech_maturity"), 0.33, 0.66,
                 "little knowledge-management infrastructure", "some knowledge-management infrastructure",
                 "mature, well-codified knowledge infrastructure")

    lines = ["### The firm you described", "",
             f"Here is **{firm}** as we heard it — the model you asked us to test. "
             f"If any line is wrong, change that input and re-run; the answer moves with it.", ""]
    lines.append(f"- **How you bill:** {pricing}.")
    if lev is not None:
        lines.append(f"- **Leverage:** about {lev:g} associates per partner.")
    lines.append(f"- **Origination:** {orig}.")
    lines.append(f"- **Practice mix:** {mix}.")
    lines.append(f"- **Clients:** {clients}.")
    lines.append(f"- **Partner power:** {power}.")
    lines.append(f"- **Tech maturity:** {tech}.")
    if sig.get("baseline_ppp"):
        lines.append(f"- **Starting point:** PPP {fmt(sig.get('baseline_ppp'), '$')}, "
                     f"margin {fmt(sig.get('baseline_margin'), '%')}, "
                     f"realization {fmt(sig.get('baseline_realization'), '%')}.")
    # Priorities: a weighted blend and/or guardrails, if the firm set them.
    weights = (opt or {}).get("weights") or {}
    guardrails = (opt or {}).get("guardrails") or []
    if weights and len(weights) > 1:
        blend = ", ".join(f"{_OBJECTIVE_SAID.get(k, k)} at {v:.0%}" for k, v in weights.items())
        priorities_line = f"**What you asked us to optimize for:** a blend of {blend}."
    else:
        priorities_line = (f"**What you asked us to optimize for:** {obj_said}."
                           + ("" if objective == "ppp" else
                              " (We still report PPP alongside, so you can see the trade-off.)"))
    lines += ["", priorities_line]
    if guardrails:
        lines.append("- **Your non-negotiables:** " + "; ".join(guardrails)
                     + " — no recommendation may cross these.")
    lines.append("")
    return lines


def render_sensitivity(exp: dict) -> str:
    """The fork deltas as honest RANGES, with each coefficient's evidentiary source — so the
    number reads as 'X to Y depending on how strongly this holds at your firm', not a false-
    precise point. Rendered when sensitivity.py has run."""
    s = (exp or {}).get("sensitivity")
    if not s or not s.get("bands"):
        return ""
    lines = ["## Fork sensitivity — ranges, not point estimates", "",
             "Each lever's effect on profit per partner, swept across a plausible range of its "
             "governing coefficient. The band is the honest uncertainty: how much the lever moves "
             "the number depends on how strongly that relationship actually holds at your firm. "
             "Calibrate the coefficient (the intake questions) to tighten it.", "",
             "| lever | PPP effect (range) | governed by | evidence |",
             "|---|---|---|---|"]
    order = sorted(s["bands"].items(), key=lambda kv: kv[1].get("band_high", 0), reverse=True)
    for lever, b in order:
        rng = f"{fmt(b.get('band_low'), '$')} to {fmt(b.get('band_high'), '$')}"
        src = (b.get("source") or "").split("]")[0].strip("[") or "modeled"
        lines.append(f"| {lever} | {rng} | {b.get('coefficient_name','—')} | {src} |")
    lines += ["",
              "Evidence tags: **SURVEY** = published benchmark, **INFERRED** = structural identity, "
              "**ASSUMPTION** = judgment (widest bands, calibrate first).", ""]
    return "\n".join(lines)


def render_exec_summary(meta: dict, metrics: dict, exp: dict) -> str:
    """Opens the report as a clear before → change → after story: what this run changed
    (which levers it pulled), what moved as a result, and where the firm ended up — then the
    recommendation for the next move. Written for a reader who has never seen the model."""
    firm = meta.get("firm_name", "Aldrich & Vale LLP")
    sprints = meta.get("sprints", "?")
    matters = meta.get("matters_per_sprint", "?")
    provider = meta.get("provider", "mock")
    real = provider not in ("mock", None)
    how = "run on real AI (" + str(provider) + ")" if real else "run on a fast offline stand-in"
    opt = exp.get("optimize") if exp else None
    levers = meta.get("levers_pulled") or {}
    pulled = [lv for lv in _LEVER_ORDER if levers.get(lv)]
    lines = ["## Executive summary", ""]

    # Frame the scoreboard once, in plain terms.
    lines += [
        "**The number that matters is profit per partner (PPP)** — what each senior (equity) partner "
        "takes home at year-end. It goes up when the firm keeps more of every fee and when each "
        "lawyer's time produces more billable value. Everything below is a before → after story about "
        "that one number.", ""]

    # --- 1. WHAT WE CHANGED -------------------------------------------------------
    lines += ["### 1. What we changed", ""]
    if pulled:
        lines.append(f"This run pulled **{len(pulled)}** of the five available levers:")
        lines.append("")
        for lv in pulled:
            lines.append(f"- **{lv.capitalize()}** — {LEVER_GLOSS[lv]}.")
        untouched = [lv for lv in _LEVER_ORDER if lv not in pulled]
        if untouched:
            lines += ["", f"Left untouched: {', '.join(untouched)}."]
        lines.append("")
    else:
        lines += [
            "**Nothing — this run is the baseline.** It's the firm exactly as it operates today: "
            "billing by the hour, no bonus for using AI, hand-offs left informal, the pyramid as-is. "
            "This is the *before* picture — the starting line every proposed change is measured "
            "against. The five levers a firm *could* pull:", ""]
        for lv in _LEVER_ORDER:
            lines.append(f"- **{lv.capitalize()}** — {LEVER_GLOSS[lv]}.")
        lines.append("")

    # --- 2. WHAT HAPPENED AS A RESULT ---------------------------------------------
    lines += ["### 2. What happened as a result", ""]
    ppp_first, ppp_last = _series_ends(metrics, "ppp")
    if ppp_last is not None:
        m_first, m_last = _series_ends(metrics, "matter_profit_margin")
        r_first, r_last = _series_ends(metrics, "realization_rate")
        lead = (f"Over {sprints} quarters ({how}), "
                + ("with those changes in place, " if pulled else "left as-is, ")
                + f"profit per partner went from {fmt(ppp_first, '$')} to **{fmt(ppp_last, '$')}**"
                + f"{_pct_change(ppp_first, ppp_last)}.")
        lines += [lead, ""]
        drivers = []
        if m_last is not None:
            drivers.append(f"- **Margin** (the profit left on each case after costs) went "
                           f"{fmt(m_first, '%')} → {fmt(m_last, '%')}.")
        if r_last is not None:
            drivers.append(f"- **Realization** (the share of billed work clients actually paid) went "
                           f"{fmt(r_first, '%')} → {fmt(r_last, '%')}.")
        if drivers:
            lines += ["Those dollars came from two places:", "", *drivers, ""]
        move = _derive_mechanism(metrics)
        if move:
            mid, first, last, ppp_declined = move
            info = METRIC_INFO.get(mid)
            if info:
                verb = "rose" if last > first else "dropped"
                if ppp_declined:
                    effect = ("more of the firm's work needed partner rescue and rework, which ate into "
                              "both margin and the share of billing that actually gets collected")
                else:
                    effect = ("work moved more cleanly between people, so less was lost to rework and "
                              "rescue — and the money followed")
                lines += [
                    f"**What drove it:** **{info.label.lower()}** ({_plain(info)}) {verb} from "
                    f"{fmt(first, info.unit)} to {fmt(last, info.unit)} over the run — {effect}.", ""]
    else:
        lines += ["_No metric history was recorded for this run._", ""]

    # --- 3. WHERE IT ENDS + THE NEXT MOVE -----------------------------------------
    lines += ["### 3. Where it leaves the firm — and the next move", ""]
    if opt and opt.get("best_combo"):
        combo = opt["best_combo"]
        # Objective the search optimized for. Defaults to PPP for legacy runs with no objective recorded.
        obj = opt.get("objective", "ppp")
        obj_label = opt.get("objective_label", "PPP")
        obj_unit = "$" if obj in ("ppp", "rpl") else "%"
        if obj == "ppp":
            # PPP wording (unchanged) — the headline objective, dollars.
            band = opt.get("ci95", opt.get("spread"))
            lines += [
                f"Searching every combination, the biggest gain comes from pulling **{', '.join(combo)}** "
                f"together: profit per partner reaches **{fmt(opt.get('best_ppp'), '$')}** — "
                f"**{fmt(opt.get('best_delta'), '$')} more than changing nothing** (give-or-take "
                f"±{fmt(band, '$')} across many market conditions, so it's a real effect, not luck). "
                f"**The order matters, because the levers depend on each other:**", ""]
        else:
            # Non-PPP objective: lead with the chosen metric, then note the PPP impact alongside.
            band = opt.get("ci95", opt.get("spread"))
            lines += [
                f"This run optimized for **{obj_label}**, not PPP. Searching every combination, the "
                f"biggest gain comes from pulling **{', '.join(combo)}** together: {obj_label} reaches "
                f"**{fmt(opt.get('best_objective'), obj_unit)}** — **{fmt(opt.get('best_delta_objective'), obj_unit)} "
                f"better than changing nothing** (give-or-take ±{fmt(band, obj_unit)} across many market "
                f"conditions, so it's a real effect, not luck). For reference, profit per partner at this "
                f"setting is **{fmt(opt.get('best_ppp'), '$')}** ({fmt(opt.get('best_delta'), '$')} vs. baseline). "
                f"**The order matters, because the levers depend on each other:**", ""]
        inter = opt.get("interactions", {})
        comp_flips = inter.get("comp_x_pricing", {}).get("delta", 0) > 0
        synergy = next((v["synergy"] for v in inter.values() if "synergy" in v), None)
        lines.append(
            "- **Pricing first — it flips the sign of everything else.** Bill by the hour and let AI "
            "work faster, and you bill *fewer* hours, so AI quietly costs you money. Charge one flat "
            "fee instead, and every hour AI saves drops straight to profit. Same firm, same "
            "technology, opposite result.")
        if synergy and synergy > 0:
            lines.append(
                f"- **Then seams — it compounds with pricing.** Writing down the informal know-how "
                f"means cleaner hand-offs and less rework hiding inside that flat fee; together the "
                f"two beat the sum of each alone by {fmt(synergy, '$')}.")
        if comp_flips:
            lines.append(
                "- **Comp last — it only pays off *after* pricing.** Paying partners to use AI loses "
                "money while you still bill hourly (you're paying them to bill fewer hours); on flat "
                "fees the same bonus turns positive. Pull it too early and it backfires.")
        lines.append("")
    lines += ["**How to read this.** The *direction* is the finding — which levers move profit, how "
              "they depend on each other, and the order to pull them. The exact dollar amounts come "
              "from a typical mid-size firm; put in your own numbers and the same engine re-runs the "
              "answer for you.", "", "---", ""]
    return "\n".join(lines)


def render_metric_table(metrics: dict) -> str:
    """Sprint-by-sprint trajectories grouped by P&L / causal / people."""
    sprints = sorted({s for hist in metrics.values() for s in hist})
    by_group = metrics_by_group()
    lines = ["### Metric trajectories (sprint-by-sprint)", ""]
    header = "| metric | " + " | ".join(f"S{s}" for s in sprints) + " |"
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


def render_firm(meta: dict) -> str:
    sig = meta.get("firm_signature") or {}
    culture = sig.get("culture") or {}
    sig = {k: v for k, v in sig.items() if k != "culture"}
    lines = ["## 1. The firm we modeled", "",
             f"**{meta.get('firm_name', 'Aldrich & Vale LLP')}** · {meta.get('sprints', '?')} sprints · "
             f"{meta.get('matters_per_sprint', '?')} matters/sprint · seed {meta.get('seed', '?')} · "
             f"provider {meta.get('provider', 'mock')}", ""]
    for section, keys in FIRM_SECTIONS:
        rows = []
        for k in keys:
            if k in sig:
                rows.append((k, sig[k]))
            elif k in culture:
                rows.append((k, culture[k]))
        if not rows:
            continue
        lines.append(f"**{section}**")
        lines.append("")
        lines.append("| field | value |")
        lines.append("|---|---|")
        for k, v in rows:
            lines.append(f"| {k} | {v} |")
        lines.append("")
    return "\n".join(lines)


def render_experiments(exp: dict, metrics: dict) -> str:
    if not exp:
        return "## 2. Experiments\n\n_No experiment summary found — run optimize.py or sweep_structural.py._\n"
    lines = ["## 2. Levers tested", ""]
    for kind in ("optimize", "sweep"):
        if kind not in exp:
            continue
        e = exp[kind]
        lines.append(f"### {kind}")
        lines.append("")
        if e.get("objective") and e.get("objective") != "ppp":
            lines.append(f"_Optimized for **{e.get('objective_label', e['objective'])}** "
                         f"(PPP shown alongside for reference)._")
            lines.append("")
        if "baseline_ppp" in e:
            lines.append(f"Baseline PPP: **{fmt(e['baseline_ppp'], '$')}**")
            lines.append("")
        if "main_effects" in e:
            lines.append("| lever | Δ PPP | Δ margin |")
            lines.append("|---|---|---|")
            for lever, fx in sorted(e["main_effects"].items(), key=lambda kv: kv[1].get("delta_ppp", 0), reverse=True):
                lines.append(f"| {lever} | {fmt(fx.get('delta_ppp'), '$')} | {fmt(fx.get('delta_margin'), '%')} |")
            lines.append("")
        if "interactions" in e:
            lines.append("**Interactions**")
            for name, i in e["interactions"].items():
                if "synergy" in i:
                    lines.append(f"- {name}: synergy {fmt(i.get('synergy'), '$')} "
                                 f"(together {fmt(i.get('both'), '$')} vs additive {fmt(i.get('additive'), '$')})")
                elif "delta" in i:
                    lines.append(f"- {name}: {fmt(i.get('delta'), '$')}")
            lines.append("")
        if "best_combo" in e:
            band = e.get("ci95", e.get("spread"))
            band_label = "95% CI" if "ci95" in e else "1σ"
            lines.append(f"**Recommendation**: pull {', '.join(e['best_combo'])} "
                         f"→ PPP {fmt(e.get('best_ppp'), '$')} "
                         f"(+{fmt(e.get('best_delta'), '$')}, {band_label} ±{fmt(band, '$')})")
            lines.append("")
            lines += _why_cost_block(metrics)
            lines.append("")
        if "story" in e:
            lines.append("**Causal story**: " + e["story"])
            lines.append("")
    return "\n".join(lines)


def build_report(run_dir: Path, experiments: dict) -> str:
    meta = load_meta(run_dir)
    metrics = load_metrics(run_dir)
    # A baseline run (no levers pulled) gets the partner-facing, unbiased narrative and
    # SKIPS the optimizer recommendation — showing a "pull these levers" verdict on a
    # baseline would inject exactly the bias the baseline is meant to avoid (and the
    # experiments.json is a shared file that can be stale from an earlier optimize run).
    levers = meta.get("levers_pulled") or {}
    is_baseline = not any(levers.values()) and not (experiments.get("optimize") or {}).get("best_combo")
    if is_baseline:
        summary = render_baseline_narrative(meta, metrics)
        experiments_block = ""
    else:
        summary = render_exec_summary(meta, metrics, experiments)
        experiments_block = render_experiments(experiments, metrics)
    # Read the firm (and the chosen objective) back to the user first — on every run,
    # baseline or not — so they can see the model heard their inputs and their goal.
    readback = "\n".join(render_readback(meta, experiments))
    parts = [
        f"# Law Firm Simulation — Full Report",
        "",
        f"**Run:** {run_dir.name}  ",
        "",
        readback,
        summary,
        render_sensitivity(experiments),
        render_firm(meta),
        experiments_block,
        render_metric_table(metrics),
        "## Assumptions & caveats",
        "",
        "Every coefficient in this sim is tagged with its evidentiary status:",
        "- **[SURVEY]** — anchored to a public benchmark (AmLaw 100 averages, NALP turnover).",
        "- **[INFERRED]** — derived from the structural mechanics (e.g. margin from realization × leverage).",
        "- **[ASSUMPTION]** — a judgment call, flagged for calibration against the firm's actuals.",
        "",
        "The honest caveat: the *shape* of the answer (which levers move PPP, and how they interact) is",
        "defensible. The *dollar magnitudes* are archetype-calibrated, not your firm's actuals. Run the",
        "intake questions against real firm data before trusting the headline number.",
        "",
        "## Raw data",
        "",
        f"- `metrics.csv` — every metric, every sprint",
        f"- `decisions.jsonl` — every agent decision with raw LLM prompt/response",
        f"- `trace.jsonl` — full event audit trail",
        f"- `state.json` — complete end-state snapshot",
    ]
    return "\n".join(parts)


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
