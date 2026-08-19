"""Full-report generator — turns a run's raw artifacts into a report a partner would read.

The sim already exports everything (meta.json, metrics.csv, decisions.jsonl, trace.jsonl,
state.json). This renders it into a single human-readable report.

The report follows one spine, and every number is labeled with the phase that produced it:

    What this is                          — the model, the scale, what a scenario means
    1. What you told us                   — inputs, what each one drives, and the starting line
    2. What we ran                        — Phase 1 baseline / Phase 2 lever search / Phase 3 sensitivity
    3. What the baseline showed           — Phase 1 output only
    4. What the lever search added        — Phase 2 output only (omitted on baseline runs)
    5. What to do, and what it's worth    — the decision, and what would sharpen it
    Appendices                            — sensitivity, config, lever detail, trajectories, raw data

That labeling is the point. The trajectories are one firm under no changes; the
recommendation comes from a few hundred *other* simulations. Splicing them without a
seam is what made earlier versions read as self-contradictory.

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


def render_stage_summary(meta: dict, metrics: dict, exp: dict, searched: bool) -> str:
    stage = _stage_of(exp, searched)
    if stage == "scenario_simulation":
        return _summary_scenario(meta, metrics, exp)
    if stage == "lever_optimization":
        return _summary_optimization(meta, metrics, exp)
    return _summary_baseline(meta, metrics, exp)


def _summary_baseline(meta: dict, metrics: dict, exp: dict) -> str:
    """What the baseline establishes — no recommendation, just the starting line and the
    single biggest leak, so the reader knows what the next stage is measured against."""
    sprints = meta.get("sprints", "?")
    ppp_first, ppp_last = _series_ends(metrics, "ppp")
    L = ["## At a glance — Baseline", "",
         "This stage changes nothing. It sets the starting line the later stages measure "
         "against, and makes **no recommendation.**", ""]
    if ppp_last is not None:
        L.append(f"- **Where you land.** Left as-is, profit per partner goes "
                 f"{fmt(ppp_first, '$')} → **{fmt(ppp_last, '$')}**"
                 f"{_pct_change(ppp_first, ppp_last)} over {_scale_phrase(sprints)}.")
    # The single biggest leak, named — the thing the levers will have to fix.
    redline = _last(metrics, "redline_rework_rate")
    real_rate = _last(metrics, "realization_rate")
    if redline is not None:
        L.append(f"- **The biggest leak.** Partners substantially rewrite {fmt(redline, '%')} "
                 "of drafts — the value sits in the redline, not the draft.")
    elif real_rate is not None:
        L.append(f"- **The biggest leak.** The firm collects only {fmt(real_rate, '%')} of "
                 "what it bills.")
    L += ["", "> Next: **Lever Optimization** tests which changes move this number.", "", "---", ""]
    return "\n".join(L)


def _classify_levers(opt: dict) -> dict:
    """Group the five levers by what the search found: confirmed helpers, denied (negative
    alone), and negligible. Comp is called out separately because its sign flips with pricing."""
    effects = opt.get("main_effects") or {}
    combo = set(opt.get("best_combo") or [])
    out = {"confirmed": [], "denied": [], "negligible": []}
    for lv in _LEVER_ORDER:
        fx = effects.get(lv)
        if not fx:
            continue
        val, unit = _effect(fx, opt)
        if val is None or _is_zero(val, unit):
            out["negligible"].append((lv, val, unit))
        elif val > 0:
            out["confirmed"].append((lv, val, unit))
        else:
            out["denied"].append((lv, val, unit))
    return out


def _summary_optimization(meta: dict, metrics: dict, exp: dict) -> str:
    """The confirm/deny verdict for the lever search — the recommendation, its confidence,
    and a one-line judgement on every lever."""
    opt = (exp or {}).get("optimize") or {}
    combo = opt.get("best_combo") or []
    obj = opt.get("objective", "ppp")
    obj_label = opt.get("objective_label", "PPP")
    unit = _obj_unit(opt)
    interactions = opt.get("interactions") or {}
    pair, inter = _interaction_pair(interactions)
    comp_delta = (interactions.get("comp_x_pricing") or {}).get("delta")

    L = ["## At a glance — Lever Optimization", ""]

    if combo:
        delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
        band = opt.get("ci95", opt.get("spread"))
        holds = (delta is not None and band is not None and abs(delta) > abs(band))
        verdict = ("**Holds up** — the band does not reach zero." if holds
                   else "**Provisional** — the band is wide enough to touch zero.")
        L += [f"**Recommendation: pull {', '.join(combo)} — together.** {obj_label} "
              f"{_fmt_delta(delta, '$' if obj == 'ppp' else unit)} against changing nothing"
              + (f", give or take {fmt(band, '$' if obj == 'ppp' else (unit if unit != 'blend' else ''))} across scenarios" if band else "")
              + f". {verdict}", ""]
    else:
        L += ["**No lever combination reliably beats standing still for this firm.** "
              "The search ran; nothing cleared the bar.", ""]

    groups = _classify_levers(opt)
    L.append("**Lever by lever — what the search confirmed and denied:**")
    L.append("")
    for lv, val, u in groups["confirmed"]:
        picked = " — **in the recommendation**" if lv in combo else " — but not picked (others carried it)"
        L.append(f"- ✓ **{lv.capitalize()} confirmed.** {_fmt_delta(val, u)} on its own{picked}.")
    for lv, val, u in groups["denied"]:
        # Comp is the special case: negative alone, positive after pricing.
        if lv == "comp" and comp_delta is not None and comp_delta > 0:
            L.append(f"- ⚠ **Comp — it depends on sequence.** {_fmt_delta(val, u)} alone (it "
                     f"costs money while you bill hourly), but {_fmt_delta(comp_delta, unit)} "
                     "after the pricing change. "
                     + ("Pull it last." if 'comp' in combo else "Still not worth it here."))
        elif lv in combo:
            # Negative on its own, yet the search kept it on top of the leaders — the
            # "bad alone, good in context" case. Calling it plainly "denied" would read as a
            # contradiction next to its place in the recommendation.
            L.append(f"- ◐ **{lv.capitalize()} — negative alone, kept in the mix.** "
                     f"{_fmt_delta(val, u)} on its own, but it earns its place stacked on top of "
                     "the others. Treat it as an adjustment, and drop it first if it costs "
                     "anything to implement.")
        else:
            L.append(f"- ✗ **{lv.capitalize()} denied.** {_fmt_delta(val, u)} on its own — it "
                     "costs money. Left out.")
    for lv, val, u in groups["negligible"]:
        L.append(f"- — **{lv.capitalize()} negligible.** No measurable effect. Left out.")

    if pair and inter and _material(inter.get("synergy"), inter.get("both")):
        syn = inter.get("synergy")
        word = "compound each other" if syn > 0 else "work against each other"
        L += ["", f"**Interaction confirmed:** {' and '.join(pair)} {word} — "
              f"{_fmt_delta(syn, unit)} beyond simply adding their separate effects."]
    elif pair and inter:
        L += ["", f"**No material interaction** between {' and '.join(pair)} — they stack about "
              "as you'd expect, so you can sequence them for convenience."]

    L += ["", "> Next: **Scenario Simulation** re-runs this lever set across fresh scenarios to "
          "confirm it holds.", "", "---", ""]
    return "\n".join(L)


def _summary_scenario(meta: dict, metrics: dict, exp: dict) -> str:
    """The validation verdict — did the determined lever set hold up when the dice were
    re-rolled? This is the finding a scenario simulation exists to produce."""
    opt = (exp or {}).get("optimize") or {}
    combo = opt.get("best_combo") or []
    obj = opt.get("objective", "ppp")
    obj_label = opt.get("objective_label", "PPP")
    unit = _obj_unit(opt)
    mc_seeds = opt.get("mc_seeds")
    delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
    band = opt.get("ci95", opt.get("spread"))
    du = "$" if obj == "ppp" else unit
    bu = "$" if obj == "ppp" else (unit if unit != "blend" else "")

    holds = (delta is not None and band is not None and abs(delta) > abs(band))
    label = "✓ Confirmed" if holds else "△ Provisional"

    L = ["## At a glance — Scenario Simulation", "",
         f"Re-ran **{', '.join(combo) or 'no levers'}** across "
         f"**{mc_seeds} fresh scenarios**" + (" " if mc_seeds else "")
         + "to test whether the recommended lever set holds when the dice are re-rolled.", "",
         f"**Verdict: {label}.** {obj_label} {_fmt_delta(delta, du)} against changing nothing"
         + (f", give or take {fmt(band, bu)}" if band else "")
         + ". "
         + ("The band does not reach zero — this is a real effect, not a lucky draw."
            if holds else
            "The band is wide enough to touch zero — trust the direction, treat the size as "
            "provisional. More scenarios would narrow it.")]

    prior = (exp or {}).get("prior") or {}
    prior_delta = prior.get("best_delta") if obj == "ppp" else prior.get("best_delta_objective")
    if prior_delta is not None and delta is not None:
        moved = delta - prior_delta
        if _is_zero(moved, du):
            L += ["", f"It lands where the optimization estimated ({_fmt_delta(prior_delta, du)}) "
                  "— the recommendation is stable."]
        else:
            direction = "higher" if moved > 0 else "lower"
            L += ["", f"The optimization estimated {_fmt_delta(prior_delta, du)}; this re-run "
                  f"lands {_fmt_delta(moved, du)} {direction}, at {_fmt_delta(delta, du)}."]

    L += ["", "---", ""]
    return "\n".join(L)


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


def render_what_this_is(meta: dict, exp: dict) -> str:
    """Open by explaining the machine, before any number appears. A reader who doesn't
    know what was simulated cannot judge whether the output means anything."""
    firm = meta.get("firm_name", "Aldrich & Vale LLP")
    sprints = meta.get("sprints", "?")
    matters = meta.get("matters_per_sprint", "?")
    provider = meta.get("provider", "mock")
    real = provider not in ("mock", None)
    scenarios = ((exp.get("run") or {}).get("baseline_scenarios")
                 or (exp.get("optimize") or {}).get("mc_seeds"))

    L = ["## What this is", "",
         f"A working model of **{firm}** — not a spreadsheet projection, a simulation. Every "
         f"quarter, simulated partners, associates, and AI tools take on {matters} matters and "
         "work them: research, drafting, review, redlines, settlement, billing. Each hand-off "
         "between people can lose context. Each draft can come back for rewriting. The rework "
         "and exception rates that come out of that quarter are what set realization, margin, "
         "utilization, and profit per partner for that quarter. Nothing is assumed — the "
         "financials are a consequence of how the work actually went.", ""]

    L += ["**Why the model is built around hand-offs.** A matter's lifecycle is mostly "
          "codifiable: intake and conflicts, staffing, research, drafting, citation check, "
          "filing. A form, a protocol, a database. The firm's real value concentrates at four "
          "**seams** — the hand-offs where the work depends on knowledge that lives in a "
          "person's head, not a system:", ""]
    for name, what in _SEAMS:
        L.append(f"- **{name.capitalize()}** — {what}.")
    L += ["",
          "AI can draft, research, and check citations — the codifiable part. It cannot hold "
          "the tacit part at the seams. So the question isn't whether AI is capable. It's "
          "whether the firm can carry what AI changes at those four seams without dropping "
          "the value that lives there. That is what this simulation puts a number on.", ""]

    scale = f"**Scale.** {_scale_phrase(sprints)} × {matters} matters per quarter"
    if scenarios:
        scale += (f", run across **{scenarios} independent scenarios**. A scenario is the same "
                  "firm with a different roll of the dice — which matters land, which hand-offs "
                  "go wrong, who leaves. One scenario is an anecdote. The spread across all of "
                  "them is the confidence band on every figure below.")
    else:
        scale += "."
    L += [scale, ""]

    if real:
        L += [f"**The agents are real AI.** Decisions in this run were made by {provider}; the "
              "prompts and responses are in the audit trail at the end.", ""]
    else:
        L += ["**The agents are a stand-in.** This run used a deterministic offline model in "
              "place of a live LLM — same mechanics, same decision structure, no language "
              "model. That makes it free, instant, and reproducible: the same inputs give the "
              "same answer every time, which is what you want when comparing options. Validate "
              "the winner on real AI agents before betting on the exact magnitudes.", ""]

    L += ["**What this is not.** It is not a forecast of your P&L. It is a comparison engine: "
          "run the same firm down several different roads and see which one ends up further "
          "ahead, and why. Trust the direction and the ordering. Calibrate before trusting the "
          "decimal places.", "", "---", ""]
    return "\n".join(L)


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
            f"**One number to reconcile before you read on.** You reported PPP of "
            f"{fmt(stated, '$')}. The model starts you at **{fmt(simulated, '$')}**, "
            f"{fmt(abs(gap), '$')} {direction} that{because}. That is not a correction to your "
            "accounting. It is the same year priced by how the work actually moves through the "
            "firm, and the difference is the friction you are already paying for. Every figure "
            f"in this report moves from {fmt(simulated, '$')}, not from {fmt(stated, '$')}."]


def render_readback(meta: dict, exp: dict, metrics: dict) -> str:
    """Read the firm back before saying anything about results — and next to each input,
    what it actually changes inside the model. An input the reader can't connect to an
    outcome is a question they answered for nothing. Nothing here is a finding."""
    sig = meta.get("firm_signature") or {}
    if not sig:
        return ""
    culture = sig.get("culture") or {}
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

    def bullet(label: str, said: str, key: str) -> str:
        drives = INPUT_DRIVES.get(key)
        return f"- **{label}:** {said}." + (f" *Drives:* {drives}." if drives else "")

    L = ["## 1. What you told us — and what each input drives", "",
         f"Here is **{firm}** as we heard it, and next to each answer, what that answer "
         "actually changes in the model. If a line is wrong, change that input and re-run; "
         "the answer moves with it.", ""]
    L.append(bullet("How you bill", pricing, "pricing_posture"))
    if lev is not None:
        L.append(bullet("Leverage", f"about {lev:g} associates per partner", "leverage_ratio"))
    L.append(bullet("Origination", orig, "origination_concentration"))
    L.append(bullet("Practice mix", mix, "practice_mix_transactional"))
    L.append(bullet("Clients", clients, "client_concentration"))
    L.append(bullet("Partner power", power, "partner_power_mix"))
    L.append(bullet("Tech maturity", tech, "tech_maturity"))
    if sig.get("baseline_ppp"):
        L.append(bullet("Starting point",
                        f"PPP {fmt(sig.get('baseline_ppp'), '$')}, "
                        f"margin {fmt(sig.get('baseline_margin'), '%')}, "
                        f"realization {fmt(sig.get('baseline_realization'), '%')}",
                        "baseline_ppp"))
    if culture:
        parts = []
        if culture.get("partner_ai_usage") is not None:
            parts.append(_band(culture["partner_ai_usage"], 0.33, 0.66,
                               "partners barely touching AI today", "partners using AI occasionally",
                               "partners already using AI routinely"))
        if culture.get("attrition_intensity") is not None:
            parts.append(_band(culture["attrition_intensity"], 0.15, 0.25,
                               "a stable associate bench", "normal associate churn",
                               "heavy associate churn"))
        if parts:
            L.append(f"- **Culture:** {', '.join(parts)}. *Drives:* how fast adoption climbs, "
                     "and how much knowledge walks out the door before it can be written down.")

    L += _reconcile_baseline(sig, metrics)

    # Priorities: a weighted blend and/or guardrails, if the firm set them.
    weights = (opt or {}).get("weights") or {}
    guardrails = (opt or {}).get("guardrails") or []
    if weights and len(weights) > 1:
        blend = ", ".join(f"{_OBJECTIVE_SAID.get(k, k)} at {v:.0%}" for k, v in weights.items())
        priorities = f"**What you asked us to optimize for:** a blend of {blend}."
    else:
        priorities = (f"**What you asked us to optimize for:** {obj_said}."
                      + ("" if objective == "ppp" else
                         " (We still report PPP alongside, so you can see the trade-off.)"))
    L += ["", priorities]
    if guardrails:
        L.append(f"- **Your non-negotiables:** {'; '.join(guardrails)} — no recommendation may "
                 "cross these, however much profit it would add.")
    L += ["", "---", ""]
    return "\n".join(L)


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


def render_what_we_ran(meta: dict, exp: dict) -> str:
    """The work behind the numbers, phase by phase — so the reader can size the evidence
    and, crucially, tell which phase produced which figure. The trajectories later in this
    report are Phase 1 only; the recommendation comes entirely from Phase 2."""
    opt = (exp or {}).get("optimize") or {}
    run = (exp or {}).get("run") or {}
    bands = ((exp or {}).get("sensitivity") or {}).get("bands") or {}
    searched = bool(opt.get("best_combo"))
    sprints = meta.get("sprints", "?")
    matters = meta.get("matters_per_sprint", "?")
    scenarios = run.get("baseline_scenarios")

    L = ["## 2. What we ran", "",
         "Three separate pieces of work went into this report. They answer different "
         "questions and their numbers do not mix.", ""]

    # --- Phase 1 -----------------------------------------------------------------
    L += ["### Phase 1 — the baseline", "",
          (f"Your firm, {_scale_phrase(sprints)}, {matters} matters a quarter, "
           + (f"across {scenarios} independent scenarios, " if scenarios else "")
           + "with **no levers pulled**. Nothing changed, nothing recommended. This is the "
             "starting line, and the spread across scenarios is how much of the movement is "
             "real versus luck. Section 3 is this phase, and only this phase."), ""]

    # --- Phase 2 -----------------------------------------------------------------
    if searched:
        effects = opt.get("main_effects") or {}
        ranked = sorted(((lv, *_effect(fx, opt)) for lv, fx in effects.items()),
                        key=lambda t: (t[1] is None, -(t[1] or 0)))
        pair, inter = _interaction_pair(opt.get("interactions") or {})
        comp_delta = ((opt.get("interactions") or {}).get("comp_x_pricing") or {}).get("delta")
        rs, ms = opt.get("round_seeds"), opt.get("mc_seeds")
        sims = opt.get("sims_run")
        unit = _obj_unit(opt)
        obj_label = opt.get("objective_label", "PPP")

        L += ["### Phase 2 — the lever search", "",
              "Five levers can be pulled, alone or in combination — thirty-two possible firms. "
              "Testing all thirty-two at full confidence is wasteful, and testing them one at a "
              "time misses the way they interact. So the search runs in rounds, each one aimed "
              "by what the last round found:", ""]

        if ranked:
            top = ranked[0]
            worst = ranked[-1]
            line = (f"- **Round 1 — each lever alone.** All five levers, "
                    + (f"{rs} scenarios each. " if rs else "")
                    + f"**{top[0].capitalize()}** came out strongest at "
                      f"{_fmt_delta(top[1], top[2])} {obj_label}")
            if worst[1] is not None and worst[1] < 0:
                line += (f", and **{worst[0]}** came out *negative* at "
                         f"{_fmt_delta(worst[1], worst[2])} — pulled on its own, it costs money.")
            else:
                line += "."
            L.append(line)
        else:
            L.append("- **Round 1 — each lever alone.** All five levers ranked by effect.")

        if pair and inter:
            syn = inter.get("synergy")
            head = (f"- **Round 2 — do they interact?** The top two, "
                    f"**{' and '.join(pair)}**, pulled together rather than separately: "
                    f"{_fmt_delta(inter.get('both'), unit)} together versus "
                    f"{_fmt_delta(inter.get('additive'), unit)} if their effects simply added. ")
            # Only call a gap an interaction when it's big enough to survive the noise.
            # A 2% difference across a handful of scenarios is a rounding artifact, and
            # "more than the sum of its parts" is a strong claim to make about one.
            if _material(syn, inter.get("both")):
                verdict = ("more than the sum of its parts" if syn > 0
                           else "less than the sum of its parts")
                L.append(head + f"That gap of {_fmt_delta(syn, unit)} is real interaction — "
                                f"{verdict}. A one-lever-at-a-time sweep cannot see this.")
            else:
                L.append(head + f"The {_fmt_delta(syn, unit)} difference is too small to read as "
                                "interaction — these two stack about as you'd expect, which "
                                "means you can sequence them for convenience.")
        if comp_delta is not None:
            if _is_zero(comp_delta, unit):
                verdict = ("It makes no measurable difference either way — this incentive is "
                           "neither the problem nor the answer for this firm.")
            elif comp_delta > 0:
                verdict = ("It flips positive — the same incentive that loses money under hourly "
                           "billing makes money under fixed fees.")
            else:
                verdict = ("It stays negative — this incentive doesn't pay off even after the "
                           "pricing change.")
            L.append(f"- **Round 2, second probe — does the comp incentive change sign?** "
                     f"Paying partners to use AI, tested *after* the pricing change instead of "
                     f"before it: {_fmt_delta(comp_delta, unit)}. " + verdict)
        L.append("- **Round 3 — does anything else stack?** The remaining levers were added to "
                 "the leader one at a time and kept only if they cleared a materiality "
                 "threshold. Levers that merely nudged the number were dropped rather than "
                 "padded into the recommendation.")
        if ms:
            L.append(f"- **Final — is the winner real?** The winning combination re-run across "
                     f"{ms} fresh scenarios, to separate a genuine effect from a lucky draw. "
                     "That run is where the confidence interval comes from.")
        L.append("")
        if sims:
            L += [f"**{sims:,} simulations** in total for this phase. Sections 4 and 5 are "
                  "built entirely from them.", ""]
        L += ["> Worth being explicit: **none of Phase 2 appears in the trajectory charts.** "
              "Those charts are your firm under no changes — Phase 1. The lever results are "
              "separate firms, run separately.", ""]
    else:
        L += ["### Phase 2 — the lever search", "",
              "**Not run.** This report is the baseline only: where you stand, not what to "
              "change. Running the lever search adds the recommendation — which levers move "
              "your objective, in what order, and by how much.", ""]

    # --- Phase 3 -----------------------------------------------------------------
    if bands:
        sens_sims = run.get("sensitivity_sims")
        L += ["### Phase 3 — how much the answer depends on our assumptions", "",
              ("Each lever's effect rests on an assumption — how much codifying a seam "
               "actually cuts rework, how much of a saved hour survives as margin. Those are "
               "estimates, so each one was swept across its plausible low-to-high range and the "
               "lever re-run at every point"
               + (f". {sens_sims} simulations. " if sens_sims else ". ")
               + "The result is a *range* per lever instead of a false-precise number, and it "
                 "shows you which assumption is worth pinning down first."), ""]

    L += ["---", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------------
# 3. What the baseline showed
# ---------------------------------------------------------------------------------

def render_baseline_showed(meta: dict, metrics: dict, exp: dict) -> str:
    """Phase 1's output: the firm as it runs today, where value leaks, and whether the
    people could carry a change. No recommendation lives here — that's Phase 2's job."""
    sprints = meta.get("sprints", "?")
    ppp_first, ppp_last = _series_ends(metrics, "ppp")

    L = ["## 3. What the baseline showed", "",
         f"Your firm over {_scale_phrase(sprints)} with **nothing changed**. Read this as the "
         "starting line, not a prediction.", ""]

    if ppp_last is None:
        L += ["_No metric history was recorded for this run._", "", "---", ""]
        return "\n".join(L)

    L += ["### Where the number lands", "",
          "**Profit per partner** is the scoreboard — what each equity partner takes home at "
          "year-end. It rises when the firm keeps more of every fee and when each lawyer's "
          "time produces more billable value.", "",
          f"Over {_scale_phrase(sprints)}, left as-is, profit per partner goes from "
          f"{fmt(ppp_first, '$')} to **{fmt(ppp_last, '$')}**"
          f"{_pct_change(ppp_first, ppp_last)}.", ""]

    m_first, m_last = _series_ends(metrics, "matter_profit_margin")
    r_first, r_last = _series_ends(metrics, "realization_rate")
    drivers = []
    if m_last is not None:
        drivers.append(f"- **Margin** (what's left on each case after costs): "
                       f"{fmt(m_first, '%')} → {fmt(m_last, '%')}.")
    if r_last is not None:
        drivers.append(f"- **Realization** (the share of billed work clients actually paid): "
                       f"{fmt(r_first, '%')} → {fmt(r_last, '%')}.")
    if drivers:
        L += ["Those dollars move through two channels:", "", *drivers, ""]

    move = _derive_mechanism(metrics)
    if move:
        mid, first, last, declined = move
        info = METRIC_INFO.get(mid)
        if info:
            verb = "rose" if last > first else "dropped"
            effect = ("more of the firm's work needed partner rescue and rework, which ate into "
                      "both margin and the share of billing that actually gets collected"
                      if declined else
                      "work moved more cleanly between people, so less was lost to rework and "
                      "rescue — and the money followed")
            L += [f"**What drove it:** **{info.label.lower()}** ({_plain(info)}) {verb} from "
                  f"{fmt(first, info.unit)} to {fmt(last, info.unit)} — {effect}.", ""]
    cost = _why_cost_block(metrics)
    if cost:
        L += cost + [""]

    # --- Where value leaks today ---
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
        leaks.append(f"- **Billed but not collected.** The firm collects {fmt(real_rate, '%')} of "
                     f"what it bills — roughly {fmt(100 - real_rate, '%')} of billed work never "
                     "turns into cash, the leak in dollar form.")
    if wip is not None and collect is not None:
        leaks.append(f"- **Slow money.** Work sits {wip:,.0f} days as unbilled WIP, and invoices "
                     f"take {collect:,.0f} days to collect — value earned long before it's paid.")
    if leaks:
        L += ["### Where value leaks today", "", *leaks, ""]
        if margin is not None:
            L += [f"Together these hold matter margin at **{fmt(margin, '%')}**. None of them are "
                  "AI problems. They're seam problems that AI will either expose or amplify.", ""]

    # --- Feasibility ---
    p_trust = _last(metrics, "partner_ai_trust")
    a_trust = _last(metrics, "associate_ai_trust")
    adopt = _last(metrics, "ai_assisted_matter_pct")
    attr = _last(metrics, "associate_attrition")
    feas = []
    if p_trust is not None and a_trust is not None:
        gap_word = "inverted" if a_trust > p_trust else "aligned"
        feas.append(f"- **The trust gap is real and it's {gap_word}.** Associates rate the AI "
                    f"{fmt(a_trust, '/10')} against partners' {fmt(p_trust, '/10')}. "
                    + ("The people with the most power over the change have the least faith in "
                       "it — that's the gradient any rollout works against, and it won't move on "
                       "communications, only on the AI proving reliable at real work."
                       if a_trust > p_trust else
                       "Leadership is ahead of the bench here, which is the easier direction to "
                       "roll out but the harder one to sustain."))
    if adopt is not None:
        feas.append(f"- **Adoption is early.** AI touched {fmt(adopt, '%')} of matters — usage, "
                    "not yet absorption. The gap between the two is where transformations stall.")
    if attr is not None:
        feas.append(f"- **The bench is churning.** Associate attrition runs {fmt(attr, '%')} a "
                    "year. Whatever the firm builds has to survive that turnover — knowledge "
                    "codified into systems outlasts it, knowledge left in heads walks out.")
    if feas:
        L += ["### Can your people carry a change", "", *feas, ""]

    L += ["---", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------------
# 4. What the lever search added
# ---------------------------------------------------------------------------------

def render_search_added(meta: dict, metrics: dict, exp: dict) -> str:
    """Phase 2's output — and specifically, what it knows that Phase 1 could not. This is
    where the report earns its keep: the interaction findings a one-at-a-time comparison
    structurally cannot produce."""
    opt = (exp or {}).get("optimize") or {}
    combo = opt.get("best_combo")
    if not combo:
        return ""
    unit = _obj_unit(opt)
    obj = opt.get("objective", "ppp")
    obj_label = opt.get("objective_label", "PPP")
    effects = opt.get("main_effects") or {}
    interactions = opt.get("interactions") or {}
    pair, inter = _interaction_pair(interactions)
    comp_delta = (interactions.get("comp_x_pricing") or {}).get("delta")
    sims = opt.get("sims_run")

    L = ["## 4. What the lever search added", "",
         "Section 3 told you where you stand. It could not tell you what to do — the baseline "
         "is one road, and a firm doesn't get to drive several. "
         + (f"Phase 2 drove them all: {sims:,} simulations across combinations of the five "
            "levers, so the comparison is measured rather than argued." if sims else
            "Phase 2 ran those roads instead, so the comparison is measured rather than argued."),
         ""]

    # --- The levers themselves ---
    L += ["### The five levers", ""]
    for lv in _LEVER_ORDER:
        gloss = LEVER_GLOSS.get(lv)
        if not gloss:
            continue
        fx = effects.get(lv)
        val, u = _effect(fx, opt) if fx else (None, unit)
        tail = f" Alone: {_fmt_delta(val, u)}." if val is not None else ""
        picked = " **← in the recommendation**" if lv in combo else ""
        L.append(f"- **{lv.capitalize()}** — {gloss}.{tail}{picked}")
    L.append("")

    # --- The findings that need the search ---
    L += ["### What one-at-a-time testing would have missed", ""]
    findings = []
    comp_alone = (effects.get("comp") or {}).get("delta_ppp")
    if comp_delta is not None and comp_delta > 0 and not _is_zero(comp_alone, "$") and comp_alone < 0:
        findings.append(
            f"- **The comp incentive changes sign depending on how you bill.** On its own it "
            f"scores {_fmt_delta(comp_alone, '$')}. Tested after the pricing change, it scores "
            f"{_fmt_delta(comp_delta, unit)}. Same incentive, opposite result. Rank the levers "
            "one at a time and you drop comp from the list; the factorial says pull it, just "
            "not first. **This is a sequencing finding, and no single-lever comparison can "
            "produce it.**")
    if pair and inter and (inter.get("synergy") or 0) > 0 and _material(inter.get("synergy"),
                                                                        inter.get("both")):
        findings.append(
            f"- **{' and '.join(pair).capitalize()} compound each other.** Together they deliver "
            f"{_fmt_delta(inter.get('both'), unit)} where adding their separate effects predicts "
            f"{_fmt_delta(inter.get('additive'), unit)}. The extra {_fmt_delta(inter.get('synergy'), unit)} "
            "only exists when both are pulled — budget for one of them and you don't get half "
            "the benefit, you get less than half.")
    negatives = [lv for lv, fx in effects.items()
                 if lv in combo and (_effect(fx, opt)[0] or 0) < 0
                 and not _is_zero(_effect(fx, opt)[0], _effect(fx, opt)[1])]
    if negatives:
        names = ", ".join(n.capitalize() for n in negatives)
        verb = "scores" if len(negatives) == 1 else "score"
        findings.append(
            f"- **{names} {verb} negative alone and still {'belongs' if len(negatives) == 1 else 'belong'} "
            "in the recommendation.** Pulled by itself the lever costs money; pulled alongside "
            "the others it pays. That combination — bad in isolation, good in context — is "
            "exactly what a pilot-one-thing-at-a-time rollout cuts first.")
    if not findings:
        findings.append("- The levers in this run behaved close to additively: no strong "
                        "interaction showed up, so the ranking in Appendix B is a fair guide on "
                        "its own. That is itself a finding — it means you can sequence them for "
                        "convenience rather than dependency.")
    L += findings + [""]

    note = opt.get("guardrail_note")
    if note:
        L += [f"**Your guardrails changed the answer.** {note[0].upper() + note[1:]}. The "
              "higher-scoring combination was ruled out rather than recommended-with-an-asterisk.",
              ""]
    if obj != "ppp":
        L += [f"**A reminder on the objective.** The search ranked by {obj_label}, not profit per "
              "partner. PPP is reported alongside so you can see what the choice costs you.", ""]

    L += ["---", ""]
    return "\n".join(L)


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


def render_next_move(meta: dict, metrics: dict, exp: dict, num: int) -> str:
    """The decision. For a searched run: the combination, the order, the confidence, and the
    one question that would sharpen it. For a baseline run: the forks, stated without a
    thumb on the scale — the point is to help the partner find the way, not sell one.

    `num` is the section number, which shifts when there was no lever search to report."""
    opt = (exp or {}).get("optimize") or {}
    combo = opt.get("best_combo")
    L = [f"## {num}. What to do, and what it's worth", ""]

    if combo:
        obj = opt.get("objective", "ppp")
        obj_label = opt.get("objective_label", "PPP")
        unit = _obj_unit(opt)
        band = opt.get("ci95", opt.get("spread"))
        interactions = opt.get("interactions") or {}
        pair, inter = _interaction_pair(interactions)
        comp_flips = (interactions.get("comp_x_pricing") or {}).get("delta", 0) > 0

        # Whether the band clears zero is a claim to CHECK, not to assert. A wide band on
        # few scenarios can straddle zero, and saying "a real effect" over one would be the
        # exact overconfidence this report exists to avoid.
        delta = opt.get("best_delta") if obj == "ppp" else opt.get("best_delta_objective")
        if band is None or delta is None:
            band_note = ""
        elif abs(delta) > abs(band):
            band_note = (" The band matters more than the midpoint: it doesn't reach zero, so "
                         "this is an effect rather than a lucky draw.")
        else:
            band_note = (" Read that band carefully — it's wide enough to touch zero, so treat "
                         "the direction as the finding and the size as provisional. More "
                         "scenarios, or calibrated inputs, would narrow it.")

        if obj == "ppp" and len(opt.get("weights") or {}) <= 1:
            L += [f"**Pull {', '.join(combo)} — together.** Profit per partner reaches "
                  f"**{fmt(opt.get('best_ppp'), '$')}**, "
                  f"**{_fmt_delta(opt.get('best_delta'), '$')} against changing nothing**, "
                  f"give or take {fmt(band, '$')} across scenarios." + band_note, ""]
        else:
            L += [f"**Pull {', '.join(combo)} — together.** {obj_label.capitalize()} reaches "
                  f"**{fmt(opt.get('best_objective'), unit if unit != 'blend' else '')}**, "
                  f"{_fmt_delta(opt.get('best_delta_objective'), unit)} against changing nothing, "
                  f"give or take {fmt(band, unit if unit != 'blend' else '')} across scenarios."
                  + band_note +
                  f" Profit per partner at this setting is {fmt(opt.get('best_ppp'), '$')} "
                  f"({_fmt_delta(opt.get('best_delta'), '$')} versus baseline).", ""]

        L += ["**The order is part of the recommendation, not a detail.**", ""]
        # Numbered by a running counter, not by position — the steps that apply depend on
        # which levers won, and a list that reads 1, 2, 4 looks like a mistake.
        step = 0

        def numbered(text: str) -> str:
            nonlocal step
            step += 1
            return f"{step}. {text}"

        if "pricing" in combo:
            L.append(numbered(
                "**Pricing first — it sets the sign on everything after it.** Bill by the hour "
                "and let AI work faster, and you bill fewer hours: AI quietly costs you money. "
                "Charge a flat fee and every hour AI saves drops toward profit. Same firm, same "
                "technology, opposite result."))
        if "seams" in combo:
            syn = inter.get("synergy") if pair and "seams" in pair else None
            extra = (f" Together with pricing it beats the sum of the two alone by "
                     f"{_fmt_delta(syn, _obj_unit(opt))}."
                     if syn and syn > 0 and _material(syn, inter.get("both")) else "")
            L.append(numbered(
                "**Then the seams.** Writing down the informal know-how means cleaner hand-offs "
                "and less rework hiding inside that flat fee." + extra))
        if "comp" in combo and comp_flips:
            L.append(numbered(
                "**Comp last.** Paying partners to use AI loses money while you still bill "
                "hourly — you're paying them to bill fewer hours. After the pricing change the "
                "same bonus turns positive. Pull it early and it backfires."))
        rest = [lv for lv in combo if lv not in ("pricing", "seams") and not (lv == "comp" and comp_flips)]
        if rest:
            L.append(numbered(
                f"**{', '.join(r.capitalize() for r in rest)}** — kept because it cleared the "
                "materiality threshold on top of the others, not because it moves the number on "
                "its own. Treat it as an adjustment, and drop it first if it costs anything to "
                "implement."))
        skipped = [lv for lv in _LEVER_ORDER if lv not in combo]
        if skipped:
            L += ["", f"**Left out: {', '.join(skipped)}.** Not because they're wrong, but "
                  "because they didn't earn their place next to the others in this firm's "
                  "configuration. Change the inputs and that can change."]
        L += ["",
              "**What this number does not include.** The cost of getting there: the senior "
              "hours to codify a seam, the client conversations to move a fee arrangement, the "
              "partner politics. The simulation prices the destination, not the trip.", ""]
    else:
        L += ["No lever search has been run, so there is no recommendation here — and putting "
              "one in would be inventing it. What the baseline does support is a clear view of "
              "the forks in front of the firm. Each has a cost on both sides.", "",
              "- **How you price.** This one changes the sign of everything else. Hourly protects "
              "today's revenue but caps what AI can return; fixed fees unlock it but move "
              "delivery risk onto the firm.",
              "- **Whether you codify the seams.** Cleaner hand-offs and less rework, paid for in "
              "senior time up front — and some partners will resist committing their judgment to "
              "a system.",
              "- **Whether you pay for adoption.** It raises usage. Under hourly billing it can "
              "also mean paying partners to bill fewer hours. Sequence matters.",
              "- **How steep the pyramid is, and how fast you act.** Smaller and less reliable "
              "than the first three. Adjustments, not the main event.", "",
              "The honest shape of it: **pricing and seams are the forks that matter, and they "
              "interact.** More than one path can work. The half-step — adopting AI while still "
              "billing hourly and leaving the seams informal — is the one combination that "
              "reliably loses money. Standing still is itself a choice with a cost.", "",
              "**The next step is to run the lever search**, which tests those combinations "
              "against your numbers instead of leaving you to reason about them.", ""]

    # --- What would sharpen this ---
    L += ["### What would sharpen this", "",
          "The *direction* here is defensible: which levers move the number, how they depend on "
          "each other, and the order to pull them. The dollar magnitudes are calibrated to a "
          "firm like yours, not to your ledger.", ""]
    widest = _widest_calibration(exp)
    if widest:
        _, lever, b, question = widest
        L += [f"The single assumption costing you the most precision is **{b.get('coefficient_name', lever)}** "
              f"— it swings the {lever} lever's value across a "
              f"{fmt(b.get('band_low'), '$')} to {fmt(b.get('band_high'), '$')} range on its own. "
              "One question closes most of that gap:", "",
              f"> *{question}*", "",
              "Answer it from your own experience, re-run, and the band tightens.", ""]
    else:
        L += ["Put your own numbers through the intake and the same engine re-runs the answer "
              "against them.", ""]
    L += ["---", ""]
    return "\n".join(L)


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

def build_report(run_dir: Path, experiments: dict) -> str:
    meta = load_meta(run_dir)
    metrics = load_metrics(run_dir)
    experiments = experiments or {}
    firm = meta.get("firm_name", "Aldrich & Vale LLP")

    # A run without a lever search reports the baseline only and SKIPS the recommendation —
    # showing a "pull these levers" verdict without having run the search would invent it.
    # (experiments.json is a shared file that can be stale from an earlier optimize run, so
    # the presence of best_combo is what gates Phase 2, not the run's own lever settings.)
    searched = bool((experiments.get("optimize") or {}).get("best_combo"))

    # Section and appendix numbering are assigned here rather than baked into each renderer,
    # so a baseline run (no Phase 2, so no section 4 and no lever appendix) numbers 1-2-3-4
    # and A-B-C-… instead of leaving holes where the missing sections would have been.
    # Each renderer returns a self-contained markdown block (or "" when it has nothing to
    # say). Empty blocks are dropped whole — filtering line-by-line would strip the blank
    # lines that separate headings from prose, which markdown needs.
    appendices = _lettered_appendices(experiments, metrics, meta, searched)
    blocks = [
        f"# Firm Simulation — {firm}\n\n**Run:** {run_dir.name}\n",
        render_stage_summary(meta, metrics, experiments, searched),
        render_what_this_is(meta, experiments),
        render_readback(meta, experiments, metrics),
        render_what_we_ran(meta, experiments),
        render_baseline_showed(meta, metrics, experiments),
        render_search_added(meta, metrics, experiments) if searched else "",
        render_next_move(meta, metrics, experiments, 5 if searched else 4),
        *appendices,
    ]
    return "\n".join(b.rstrip() + "\n" for b in blocks if b.strip())


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
