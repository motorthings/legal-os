"""
Adaptive lever optimization — try a few, learn, try the promising next.

Instead of brute-force Monte Carlo over every combination, this runs a few ROUNDS,
each chosen from the previous round's results:

  Round 1 — main effects (each lever alone)        -> rank levers
  Round 2 — 2x2 factorial on the top levers        -> find interactions (the "causal" part)
  Round 3 — refinement (add the next lever)        -> does it stack?
  Final  — small Monte Carlo on the winner(s)      -> confidence interval

The output is a causal story — which levers interact, and the best combination in
what order — not just a ranking. It's "adaptive," not Bayesian: there's no posterior
or acquisition function, just a fixed 3-round schedule where each round's experiments
are chosen from the last round's results instead of testing everything blindly.
"""
import argparse, asyncio, contextlib, io, json, math, os, sys, statistics, threading
from pathlib import Path

from .src.orchestrator import Orchestrator, SimulationConfig, FirmSignature

EXP_PATH = Path("results/experiments.json")


def persist_experiment(new: dict):
    """Merge a script's results into results/experiments.json (shared with the report/dashboard)."""
    EXP_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if EXP_PATH.exists():
        try:
            data = json.loads(EXP_PATH.read_text())
        except json.JSONDecodeError:
            data = {}
    data.update(new)
    EXP_PATH.write_text(json.dumps(data, indent=2))

# Each lever: a name, what it means, and the config fields it flips when "pulled".
LEVERS = {
    "pricing":  "convert hourly -> AFA",
    "comp":     "pay partners for AI",
    "leverage": "flatten the pyramid",
    "seams":    "codify the tacit handoffs",
    "latency":  "close the loop faster",
}

# What the firm is optimizing FOR. PPP is the AmLaw default, but it isn't every
# firm's goal — a growth-stage firm cares about revenue/lawyer, an aging partnership
# about retention. Each objective maps to a recorded metric, a direction (+1 =
# higher is better, -1 = lower is better, so ranking stays "bigger delta = better"),
# a human label, and whether it's a dollar figure (for formatting).
OBJECTIVES = {
    "ppp":         ("ppp",                 1, "PPP",              True),
    "margin":      ("matter_profit_margin", 1, "margin",          False),
    "rpl":         ("rpl",                 1, "revenue/lawyer",   True),
    "realization": ("realization_rate",    1, "realization",     False),
    "retention":   ("associate_attrition", -1, "retention (attrition↓)", False),
}


def parse_weights(spec: str | None, default_objective: str) -> dict:
    """Parse "ppp=0.6,retention=0.4" into {objective: weight}, normalized to sum 1.

    A firm's priorities are rarely a single metric. Weights let the partnership say
    "we care about profit, but retention matters half as much" and have the lever
    ranking optimize that blend instead of PPP alone. No --weights => the single
    --objective at weight 1.0 (backwards-compatible)."""
    if not spec:
        return {default_objective: 1.0}
    weights = {}
    for part in spec.split(","):
        key, _, val = part.partition("=")
        key = key.strip()
        if key not in OBJECTIVES:
            raise SystemExit(f"unknown objective in --weights: {key!r} (choose from {list(OBJECTIVES)})")
        weights[key] = float(val)
    total = sum(weights.values())
    if total <= 0:
        raise SystemExit("--weights must sum to a positive number")
    return {k: v / total for k, v in weights.items()}


def parse_guardrails(specs: list[str]) -> list[tuple]:
    """Parse ["associate_attrition<=25", "realization>=70"] into (metric, op, value).

    Guardrails are the firm's non-negotiables: keep PPP the goal, but rule out any
    path that pushes attrition above 25% or realization below 70%. They FILTER the
    recommendation rather than change the ranking — the best FEASIBLE combo wins."""
    valid = {k for k, *_ in (OBJECTIVES[o] for o in OBJECTIVES)}
    metric_keys = {OBJECTIVES[o][0] for o in OBJECTIVES}
    out = []
    for spec in specs or []:
        for op in ("<=", ">=", "<", ">"):
            if op in spec:
                metric, _, val = spec.partition(op)
                metric = metric.strip()
                if metric not in metric_keys:
                    raise SystemExit(f"guardrail metric {metric!r} must be one of {sorted(metric_keys)}")
                out.append((metric, "<=" if op in ("<=", "<") else ">=", float(val)))
                break
        else:
            raise SystemExit(f"guardrail {spec!r} needs an operator (<=, >=)")
    return out


def blended_score(pulled: set, seeds, sprints, matters, weights: dict,
                  phasing: dict | None = None) -> float:
    """Weighted, unit-normalized objective score. Each component is expressed as
    percentage improvement over the no-lever baseline (direction-signed so bigger is
    always better), then weighted. Normalizing to % makes dollars and percentage-point
    metrics comparable in one blend."""
    total = 0.0
    for obj_key, w in weights.items():
        metric, direction, _, _ = OBJECTIVES[obj_key]
        base = run_metric(set(), seeds, sprints, matters, metric)
        val = run_metric(pulled, seeds, sprints, matters, metric, phasing)
        denom = abs(base) if abs(base) > 1e-9 else 1.0
        total += w * direction * (val - base) / denom
    return total


def guardrails_ok(pulled: set, seeds, sprints, matters, guardrails: list,
                  phasing: dict | None = None) -> bool:
    """True if the pulled-lever combo satisfies every guardrail (on the seed-mean)."""
    for metric, op, bound in guardrails:
        val = run_metric(pulled, seeds, sprints, matters, metric, phasing)
        if op == "<=" and val > bound:
            return False
        if op == ">=" and val < bound:
            return False
    return True


# The firm to test levers against. None => the archetype. Set from --config so the
# optimizer runs the FIRM's numbers (and their calibrated elasticities), not a generic one.
_BASE_FIRM = None            # a FirmSignature, or None
_BASE_ELASTICITIES = None    # an ElasticityProfile, or None


def set_base_firm(firm_signature=None, elasticities=None):
    """Point the optimizer at a specific firm's signature + calibrated elasticities. Clears
    the trial cache, since results are firm-specific."""
    global _BASE_FIRM, _BASE_ELASTICITIES
    _BASE_FIRM, _BASE_ELASTICITIES = firm_signature, elasticities
    _TRIAL_CACHE.clear()
    reset_sims_run()


def build_overrides(pulled: set, phasing: dict | None = None) -> dict:
    """Merge the config for a set of pulled levers, starting from the base firm (or archetype).

    `phasing` (optional) maps lever -> 1-indexed start sprint. A phased lever holds the firm at
    its PRE-CHANGE posture until its start quarter (captured below as pre_lever_*), so it doesn't
    snap to the lever target from quarter 1. Levers with no phasing entry start at quarter 1 — the
    pre-phasing behavior."""
    import copy
    sig = copy.deepcopy(_BASE_FIRM) if _BASE_FIRM is not None else FirmSignature()
    # The firm's posture BEFORE any lever override, so a phased pricing/leverage lever can hold
    # the firm at its starting state (e.g. hourly billing, leverage 3.5) until it activates.
    pre_pricing = sig.pricing_posture
    pre_leverage = sig.leverage_ratio
    if "pricing" in pulled:
        sig.pricing_posture = "afa_native"
    if "leverage" in pulled:
        sig.leverage_ratio = 5.0
    overrides = {"firm_signature": sig,
                 "pre_lever_pricing": pre_pricing, "pre_lever_leverage": pre_leverage}
    if _BASE_ELASTICITIES is not None:
        overrides["elasticities"] = _BASE_ELASTICITIES
    overrides["comp_lever_strength"] = 0.9 if "comp" in pulled else 0.0
    overrides["decision_latency_sprints"] = 1 if "latency" in pulled else 5
    overrides["codify_seams"] = "seams" in pulled
    if phasing:
        overrides["lever_start_sprints"] = dict(phasing)
    return overrides


_TRIAL_CACHE: dict = {}

# How many simulations the search actually executed (cache hits excluded). The report
# quotes this to show the reader the size of the search behind the recommendation.
_SIMS_RUN = [0]


def sims_run() -> int:
    return _SIMS_RUN[0]


def reset_sims_run() -> None:
    _SIMS_RUN[0] = 0

# Metrics collected on every trial, so switching --objective never needs a re-run
# (all objectives read from the same cached simulation).
_COLLECT = ("ppp", "matter_profit_margin", "rpl", "realization_rate", "associate_attrition")


# The lever search normally runs on the deterministic mock (fast, free). To run it on a real
# model (e.g. deepseek) for comparison, `run_optimization`/`run_scenario_mc` set the current
# provider/model on a THREAD-LOCAL — each `asyncio.to_thread` optimize has its own state, so
# concurrent optimizes on different providers don't clash. `_simulate` reads it.
_provider_state = threading.local()


def _current_provider() -> tuple[str, object]:
    return (getattr(_provider_state, "provider", "mock"),
            getattr(_provider_state, "model", None))


def _phasing_key(phasing: dict | None) -> tuple:
    """A stable cache-key component for a phasing plan. A lever at start<=1 is quarter-1 — no
    delay — so it's dropped, letting an all-from-Q1 plan share the plain optimization's cache."""
    return tuple(sorted((lv, s) for lv, s in (phasing or {}).items() if s > 1))


def _simulate(pulled: set, seeds, sprints, matters, phasing: dict | None = None):
    """Run each seed once; cache and return {metric: [[per-sprint values] per seed]}.

    The cache keeps full quarter-by-quarter histories, not just finals, so `run_trials`
    (finals) and `run_trajectory` (mean per-sprint curve) both derive from the same runs
    without re-simulating. Provider/model and the phasing plan are part of the cache key,
    because a mock result is not interchangeable with a real one, and a different start
    quarter is a different run."""
    provider, model = _current_provider()
    phasing = {lv: s for lv, s in (phasing or {}).items() if s > 1} or None
    key = (frozenset(pulled), _phasing_key(phasing), tuple(seeds), sprints, matters, provider, model)
    if key in _TRIAL_CACHE:
        return _TRIAL_CACHE[key]
    overrides = build_overrides(pulled, phasing)
    out = {m: [] for m in _COLLECT}
    _SIMS_RUN[0] += len(seeds)
    for seed in seeds:
        cfg = SimulationConfig(sprints=sprints, matters_per_sprint=matters,
                               llm_provider=provider, llm_model=model, seed=seed,
                               output_dir="results/_opt", run_id="OPT", **overrides)
        o = Orchestrator(cfg)
        o.initialize()
        with contextlib.redirect_stdout(io.StringIO()):
            r = asyncio.run(o.run())
        for m in _COLLECT:
            h = r.company.metric_history.get(m)
            out[m].append([snap.value for snap in h.values] if h else [])
    _TRIAL_CACHE[key] = out
    return out


def run_trials(pulled: set, seeds, sprints, matters, phasing: dict | None = None):
    """Return {metric: [per-seed final values]}, derived from the cached full histories."""
    histories = _simulate(pulled, seeds, sprints, matters, phasing)
    return {m: [series[-1] if series else 0.0 for series in histories[m]]
            for m in _COLLECT}


def run_trajectory(pulled: set, seeds, sprints, matters, key: str = "ppp",
                   phasing: dict | None = None) -> list[float]:
    """Mean per-sprint trajectory of `key`, aligned across seeds by sprint index.

    Returns [q1, q2, …, qN] — the average value at each quarter, across seeds. Reads the
    cached histories, so it's free after the trials run."""
    histories = _simulate(pulled, seeds, sprints, matters, phasing)[key]
    n = max((len(s) for s in histories), default=0)
    if n == 0:
        return []
    return [statistics.mean([s[i] for s in histories if i < len(s)]) for i in range(n)]


def run_metric(pulled: set, seeds, sprints, matters, key: str,
               phasing: dict | None = None) -> float:
    return statistics.mean(run_trials(pulled, seeds, sprints, matters, phasing)[key])


def run_ppp(pulled: set, seeds, sprints, matters) -> float:
    return run_metric(pulled, seeds, sprints, matters, "ppp")


def run_margin(pulled: set, seeds, sprints, matters) -> float:
    return run_metric(pulled, seeds, sprints, matters, "matter_profit_margin")


# === The "when" (timing) search ======================================================
#
# The lever search answers WHICH changes to make and in what ORDER. This answers WHEN each
# one pays. Timing is judged on CUMULATIVE profit (the mean across every quarter), not the
# endpoint: the lever ranking asks how much a change lifts the final number, but timing asks
# how much of that lift you capture by acting now vs later — and a change made earlier pays
# for more quarters. On the endpoint alone, the engine is (correctly) almost silent about
# timing; on the cumulative measure it can separate "act now" from "act later," which is the
# honest, coarse signal the report can defend. It is a LOCAL search (coordinate ascent), not a
# proven global optimum — the report says as much.

TIMING_CANDIDATES = (1, 2, 3, 4, 5, 7)   # start quarters worth distinguishing on a ~16-q runway


def _cum_mean(histories: list[list[float]]) -> float:
    """Mean value across ALL quarters and seeds — the cumulative/average-profit measure the
    timing search ranks by (vs run_metric, which reads only the last quarter)."""
    flat = [v for series in histories for v in series]
    return statistics.mean(flat) if flat else 0.0


def _simulate_phased(phasing: dict, seeds, sprints, matters):
    """Simulate a phasing plan: the levers in `phasing` are pulled, each starting at its quarter."""
    return _simulate(set(phasing), seeds, sprints, matters, phasing)


def timing_score(phasing: dict, seeds, sprints, matters, weights: dict) -> float:
    """A phasing plan's objective on the CUMULATIVE measure — same weights/direction as the
    lever search, but each metric read as its mean across all quarters instead of the endpoint."""
    if len(weights) > 1:                       # blend: weighted, unit-normalized cumulative deltas
        total = 0.0
        for obj, w in weights.items():
            metric, direction, *_ = OBJECTIVES[obj]
            base = _cum_mean(_simulate(set(), seeds, sprints, matters, None)[metric])
            val = _cum_mean(_simulate_phased(phasing, seeds, sprints, matters)[metric])
            denom = abs(base) if abs(base) > 1e-9 else 1.0
            total += w * direction * (val - base) / denom
        return total
    obj_key, obj_dir, *_ = OBJECTIVES[next(iter(weights))]
    return obj_dir * _cum_mean(_simulate_phased(phasing, seeds, sprints, matters)[obj_key])


def run_timing_search(best_combo: list, *, seeds, sprints, matters, weights: dict,
                      guardrails: list, progress=None) -> dict | None:
    """Find WHEN to make each lever change, judged on CUMULATIVE profit.

    Each lever's best start quarter is found INDEPENDENTLY — hold every other chosen lever at
    quarter 1 and sweep this one's start. (A joint coordinate-ascent is not used: the levers
    interact too strongly — comp's sign flips with pricing — so joint ascent finds misleading
    local optima, e.g. "delay flat fees," which the model does not support.) Each lever's answer
    is therefore: "if everything else starts now, when does THIS one pay best?" — a clean, honest
    per-change call that can't conspire with the other levers to delay the foundation.

    Returns a `timing` dict (or None when there's nothing to time): per-lever best start quarter,
    the dollar cost of waiting on it (cumulative PPP), and whether that cost is inside the model's
    own seed-to-seed spread (in which case the exact quarter is a range, not a sharp call)."""
    if not best_combo:
        return None
    if progress:
        progress("timing search — when to make each change", 1, 1)

    # "Everything now" = the lever search's winner, all from quarter 1. `timing_score` reads the
    # start>=1 as quarter-1 (normalized in _simulate), so this is the all-at-once plan.
    all_q1 = {lv: 1 for lv in best_combo}
    base_score = timing_score(all_q1, seeds, sprints, matters, weights)
    base_ppp = _cum_ppp(all_q1, seeds, sprints, matters)
    latest = TIMING_CANDIDATES[-1]          # the "left it too late" reference quarter

    # Noise floor: the seed-to-seed spread of cumulative PPP — what a quarter call has to beat.
    per_seed_cum = [statistics.mean(s) for s in _simulate_phased(all_q1, seeds, sprints, matters)["ppp"] if s]
    spread_ppp = statistics.pstdev(per_seed_cum) if len(per_seed_cum) > 1 else 0.0

    levers = {}
    for lv in best_combo:
        # Others at quarter 1; sweep this lever's start on the objective (weights) ranking.
        best_q, best_obj = 1, base_score
        for q in TIMING_CANDIDATES:
            s = timing_score({**all_q1, lv: q}, seeds, sprints, matters, weights)
            if s > best_obj + 1e-9:
                best_q, best_obj = q, s
        # The dollar cost of leaving this lever until the latest candidate, in cumulative PPP.
        ppp_now = _cum_ppp({**all_q1, lv: 1}, seeds, sprints, matters)
        ppp_late = _cum_ppp({**all_q1, lv: latest}, seeds, sprints, matters)
        cost_of_waiting = ppp_now - ppp_late        # >0: waiting to the end loses money
        levers[lv] = {
            "start": best_q,
            "cost_of_waiting": cost_of_waiting,     # cumulative PPP lost by waiting until the last quarter
            "within_noise": abs(cost_of_waiting) < abs(spread_ppp),
        }

    # The joint schedule (each lever at its independent best) and what sequencing captures on the
    # cumulative measure versus doing it all at once. Informational — per-lever claims are each
    # guarded by their own within_noise, not this aggregate.
    schedule = {lv: levers[lv]["start"] for lv in best_combo}
    schedule_ppp = _cum_ppp(schedule, seeds, sprints, matters)
    # A lever whose best start is quarter 1 with a clear cost of waiting reads as "act now"; the
    # schedule line is just the sequencing delta.
    gain = schedule_ppp - base_ppp

    return {
        "objective": _objective_label(weights),
        "metric": "profit earned across all quarters (not just the end)",
        "horizon_sprints": sprints,
        "candidates": list(TIMING_CANDIDATES),
        "spread_ppp": spread_ppp,
        "gain": gain,
        "all_q1_ppp": base_ppp,
        "schedule_ppp": schedule_ppp,
        "levers": levers,
    }


def _cum_ppp(phasing: dict, seeds, sprints, matters) -> float:
    """Cumulative (mean-across-quarters, mean-across-seeds) PPP — the dollar measure the report
    quotes for timing, consistent with the noise floor (also in cumulative PPP)."""
    return _cum_mean(_simulate_phased(phasing, seeds, sprints, matters)["ppp"])


def _objective_label(weights: dict) -> str:
    """A short human label for the (single or blended) objective."""
    primary = max(weights, key=weights.get)
    if len(weights) > 1:
        return "priority blend"
    return OBJECTIVES[primary][2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=None,
                    help="run-config JSON (docs/PRD.md contract): firm signature, calibrated "
                         "elasticities, and objective (weights + guardrails). CLI flags below "
                         "override the file.")
    ap.add_argument("--sprints", type=int, default=16)
    ap.add_argument("--matters", type=int, default=50)
    ap.add_argument("--objective", choices=list(OBJECTIVES), default="ppp",
                    help="single metric the lever ranking optimizes for (default: ppp). "
                         "ppp | margin | rpl | realization | retention")
    ap.add_argument("--weights", type=str, default=None,
                    help="firm-priority blend, e.g. 'ppp=0.6,retention=0.4'. Overrides "
                         "--objective. Ranks levers against the weighted, unit-normalized "
                         "improvement instead of a single metric.")
    ap.add_argument("--guardrail", action="append", default=[],
                    help="constraint the recommendation must satisfy, e.g. "
                         "'associate_attrition<=25' or 'realization_rate>=70'. Repeatable. "
                         "Filters out any lever combo that violates it.")
    ap.add_argument("--round-seeds", type=int, default=8)   # seeds during optimization rounds
                                                            # (3 was too noisy — Round-1 ranking flipped
                                                            #  seams<->pricing vs the 20-seed sweep)
    ap.add_argument("--mc-seeds", type=int, default=20)     # seeds for the final confidence
    args = ap.parse_args()
    opt_seeds = list(range(42, 42 + args.round_seeds))
    mc_seeds = list(range(100, 100 + args.mc_seeds))

    # If a config file is given, it sets the firm to optimize (its signature + calibrated
    # elasticities) and its priorities. Explicit CLI --weights/--guardrail still override.
    cfg_objective = None
    if args.config:
        from .run_config import load_run_config, build_firm, build_elasticities, build_objective
        rc = load_run_config(args.config)
        set_base_firm(build_firm(rc.get("firm") or {}), build_elasticities(rc))
        cfg_objective = build_objective(rc)
        print(f"Loaded config: {rc.get('name', '(unnamed)')}  [{args.config}]")

    # Firm priorities: a weighted blend (default = the single --objective at weight 1.0)
    # and optional guardrail constraints. CLI wins over the config file; the config file
    # wins over the plain default.
    if args.weights:
        weights = parse_weights(args.weights, args.objective)
    elif cfg_objective:
        weights = cfg_objective["weights"]
    else:
        weights = parse_weights(None, args.objective)
    guardrails = parse_guardrails(args.guardrail) if args.guardrail else (
        cfg_objective["guardrails"] if cfg_objective else [])
    use_blend = len(weights) > 1
    # The primary objective (highest weight) drives the human-facing raw/label reporting.
    primary = max(weights, key=weights.get)
    obj_key, obj_dir, obj_label, obj_is_dollar = OBJECTIVES[primary]
    if use_blend:
        obj_label = "priority blend (" + ", ".join(f"{k} {v:.0%}" for k, v in weights.items()) + ")"

    # Ranking is done in "score" space: bigger = better for the firm's objective. For a
    # single objective that's direction*metric (raw units); for a blend it's the weighted,
    # unit-normalized improvement over baseline (comparable across dollars and percentages).
    def score(pulled, seeds):
        if use_blend:
            return blended_score(pulled, seeds, args.sprints, args.matters, weights)
        return obj_dir * run_metric(pulled, seeds, args.sprints, args.matters, obj_key)
    def raw(pulled, seeds):   return run_metric(pulled, seeds, args.sprints, args.matters, obj_key)
    def fmt(v):     return (f"{v:+,.3f}" if use_blend else (f"{v:+,.0f}" if obj_is_dollar else f"{v:+,.1f}"))
    def fmt_abs(v): return (f"{v:,.3f}"  if use_blend else (f"{v:,.0f}"  if obj_is_dollar else f"{v:,.1f}"))
    # Keep/synergy thresholds scale with the score space: normalized fraction for a blend,
    # raw units (dollars vs percentage points) for a single objective.
    if use_blend:
        KEEP_THRESH, SYN_THRESH = 0.01, 0.02          # 1% / 2% blended improvement
    else:
        KEEP_THRESH = 20_000 if obj_is_dollar else 0.3
        SYN_THRESH  = 50_000 if obj_is_dollar else 0.5

    gr_note = (" | guardrails: " + ", ".join(f"{m}{op}{v:g}" for m, op, v in guardrails)) if guardrails else ""
    print(f"\n=== Adaptive lever optimization ({args.sprints} sprints, objective: {obj_label}{gr_note}) ===\n")

    # --- Round 1: main effects (in score space) ---
    baseline = score(set(), opt_seeds)
    baseline_margin = run_margin(set(), opt_seeds, args.sprints, args.matters)
    effects = {}
    margin_effects = {}
    for lever in LEVERS:
        effects[lever] = score({lever}, opt_seeds) - baseline
        margin_effects[lever] = run_margin({lever}, opt_seeds, args.sprints, args.matters) - baseline_margin
    print(f"Round 1 — main effect of each lever (Δ {obj_label}, alone):")
    ranked = sorted(effects.items(), key=lambda kv: kv[1], reverse=True)
    for lever, d in ranked:
        print(f"  {lever:10s} {fmt(d):>12s}")
    print(f"  baseline {obj_label} = {fmt_abs(obj_dir * baseline)}")

    # --- Round 2: 2x2 factorial on the top-2 levers + comp x pricing ---
    # The "causal" round: does A+B exceed A + B alone? Does comp flip sign under pricing?
    positives = [lever for lever, d in ranked if d > 0]        # levers that actually help THIS objective
    # Interaction probe needs a pair: prefer the top-2 helpers; if fewer than two levers
    # help, fall back to the top-2 by effect so the causal probe still runs.
    pair = positives[:2] if len(positives) >= 2 else [lever for lever, _ in ranked[:2]]
    top2 = positives[:2]                                        # what we'll actually seed the winner from
    print(f"\nRound 2 — interactions (factorial on: {', '.join(pair)})")
    a, b = pair[0], pair[1]
    alone = {x: effects[x] for x in (a, b)}
    both = score({a, b}, opt_seeds) - baseline
    additive = alone[a] + alone[b]
    synergy = both - additive
    print(f"  {a} alone: {fmt(alone[a])} | {b} alone: {fmt(alone[b])}")
    print(f"  {a}+{b} together: {fmt(both)}  (additive would be {fmt(additive)})")
    print(f"  interaction: {fmt(synergy)}  -> {'synergistic' if synergy > SYN_THRESH else 'sub-additive' if synergy < -SYN_THRESH else 'additive'}")

    # comp x pricing interaction — comp's main effect is negative, but should flip under AFA.
    print(f"\n  comp x pricing interaction (does comp flip sign under AFA?)")
    comp_alone = effects["comp"]
    comp_under_afa = score({"comp", "pricing"}, opt_seeds) - score({"pricing"}, opt_seeds)
    print(f"  comp alone (hourly): {fmt(comp_alone)}  |  comp under AFA: {fmt(comp_under_afa)}  -> {'flips: comp helps under AFA' if comp_under_afa > 0 else 'does not flip'}")

    # --- Round 3: refinement — stack the next-best lever onto the best combo ---
    best = set(top2)
    if comp_under_afa > 0:
        best.add("comp")
    remaining = [l for l in LEVERS if l not in best]
    print(f"\nRound 3 — refinement (best so far: {', '.join(sorted(best))})")
    best_score = score(best, opt_seeds)
    for lever in remaining:
        candidate = best | {lever}
        gain = score(candidate, opt_seeds) - best_score
        print(f"  +{lever:10s} -> {fmt(gain):>12s}  {'(keep)' if gain > KEEP_THRESH else '(skip)'}")
        if gain > KEEP_THRESH:
            best.add(lever)

    # --- Guardrails: the adaptive winner must satisfy the firm's non-negotiables. If it
    # doesn't, search all 32 combos for the best-scoring FEASIBLE one (cheap — cached). ---
    guardrail_note = None
    if guardrails and not guardrails_ok(best, opt_seeds, args.sprints, args.matters, guardrails):
        from itertools import combinations
        all_combos = [set(c) for r in range(len(LEVERS) + 1) for c in combinations(LEVERS, r)]
        feasible = [c for c in all_combos
                    if guardrails_ok(c, opt_seeds, args.sprints, args.matters, guardrails)]
        if feasible:
            prev = ", ".join(sorted(best)) or "none"
            best = max(feasible, key=lambda c: score(c, opt_seeds))
            guardrail_note = (f"adaptive winner ({prev}) violated a guardrail; best FEASIBLE "
                              f"combo is {', '.join(sorted(best)) or 'none'}")
        else:
            best = set()
            guardrail_note = "no lever combination satisfies the guardrails — reporting baseline"
        print(f"\n[guardrail] {guardrail_note}")

    # --- Final: Monte Carlo on the winner vs baseline (raw objective units) ---
    print(f"\nFinal — Monte Carlo confidence (winner: {', '.join(sorted(best)) or 'none'})")
    win_vals = run_trials(best, mc_seeds, args.sprints, args.matters)[obj_key]   # one pass, all seeds
    win_mean = statistics.mean(win_vals)
    n = len(win_vals)
    spread = statistics.pstdev(win_vals)                                   # 1σ across seeds
    ci95 = 1.96 * statistics.stdev(win_vals) / math.sqrt(n) if n > 1 else 0.0  # 95% CI half-width
    base_mc = raw(set(), mc_seeds)
    improvement = obj_dir * (win_mean - base_mc)   # signed so "+" = better for this objective
    ppp_win = run_metric(best, mc_seeds, args.sprints, args.matters, "ppp")   # headline PPP, always reported
    print(f"  best combination: {', '.join(sorted(best)) or '(no lever helps)'}")
    print(f"  {obj_label} {fmt_abs(win_mean)}  vs baseline {fmt_abs(base_mc)}")
    print(f"  = {fmt(improvement)} better  (95% CI ±{fmt_abs(ci95)}, 1σ {fmt_abs(spread)})")
    if args.objective != "ppp":
        print(f"  (PPP at this setting: {ppp_win:,.0f})")

    # --- The causal story ---
    movers = ", ".join(sorted(best)) or "(no lever reliably helps this objective)"
    print("\n=== Causal story ===")
    print(f"  For {obj_label}: pull {movers} — the reliable movers.")
    if comp_under_afa > 0:
        print(f"  Then comp — it only helps AFTER you've converted to AFA (under hourly it costs you).")
    else:
        print(f"  Skip comp — it doesn't help even under AFA.")
    print(f"  The interaction that matters: comp's sign depends on pricing. That's the causal relationship the one-at-a-time sweep missed.")

    # --- Persist for the report / dashboard ---
    story = f"[objective: {obj_label}] Pull {movers} (reliable movers). " + (
        "Then comp — it only helps AFTER AFA (under hourly it costs you)."
        if comp_under_afa > 0 else "Skip comp — it doesn't help even under AFA.")
    # PPP-space values kept for the report/dashboard (which are PPP-centric); all cached, so cheap.
    ppp_base_opt = run_metric(set(), opt_seeds, args.sprints, args.matters, "ppp")
    ppp_trials = {lv: run_trials({lv}, opt_seeds, args.sprints, args.matters)["ppp"]
                  for lv in LEVERS}
    ppp_effects = {lv: statistics.mean(ppp_trials[lv]) - ppp_base_opt for lv in LEVERS}
    ppp_spreads = {lv: statistics.stdev(ppp_trials[lv]) if len(ppp_trials[lv]) > 1 else 0.0
                   for lv in LEVERS}
    ppp_base_mc = run_metric(set(), mc_seeds, args.sprints, args.matters, "ppp")
    timing = run_timing_search(sorted(best), seeds=opt_seeds, sprints=args.sprints,
                               matters=args.matters, weights=weights, guardrails=guardrails)
    persist_experiment({
        "optimize": {
            "objective": args.objective,
            "objective_label": obj_label,
            "weights": weights,
            "guardrails": [f"{m}{op}{v:g}" for m, op, v in guardrails],
            "guardrail_note": guardrail_note,
            "baseline_ppp": ppp_base_opt,
            "baseline_objective": obj_dir * baseline,
            "main_effects": {lv: {"delta_ppp": ppp_effects[lv],
                                  "delta_objective": effects[lv],
                                  "delta_margin": margin_effects[lv],
                                  "spread_ppp": ppp_spreads[lv]}
                             for lv in LEVERS},
            "interactions": {
                f"{a}x{b}": {"both": both, "additive": additive, "synergy": synergy},
                "comp_x_pricing": {"delta": comp_under_afa},
            },
            "best_combo": sorted(best),
            "best_objective": win_mean,
            "best_delta_objective": improvement,
            "best_ppp": ppp_win,
            "best_delta": ppp_win - ppp_base_mc,   # PPP-space, for the report/dashboard
            "spread": spread,
            "ci95": ci95,
            "story": story,
            "timing": timing,
            # The two chart lines (decline vs recovery) so the report's chart renders both.
            "ppp_trajectory": run_trajectory(best, mc_seeds, args.sprints, args.matters, "ppp"),
            "baseline_trajectory": run_trajectory(set(), mc_seeds, args.sprints, args.matters, "ppp"),
        }
    })

    # --- Deterministic phase complete → write the winner as a config, hand off to the LLM phase ---
    combo = sorted(best)
    rc = {
        "name": f"from-optimize [{obj_label}] — " + (", ".join(combo) if combo else "baseline"),
        "run": {"sprints": args.sprints, "matters_per_sprint": 10, "seed": 42,
                "max_cost": 5.0, "model": "deepseek-chat", "legal_tool": "mock"},
        "firm": {"pricing_posture": "afa_native" if "pricing" in best else "hourly",
                 "leverage_ratio": 5.0 if "leverage" in best else 3.5},
        "levers": {"comp_lever_strength": 0.9 if "comp" in best else 0.3,
                   "codify_seams": "seams" in best,
                   "decision_latency_sprints": 1 if "latency" in best else 2},
    }
    cfg_path = Path("configs/from_optimize.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(rc, indent=2))

    bar = "=" * 72
    print(f"\n{bar}")
    print("DETERMINISTIC PHASE COMPLETE  (mock engine — free, reproducible)")
    print("This found the SHAPE of the answer: which levers, in what order, with a CI.")
    print(f"\nWinning combo written to: {cfg_path}")
    print("\nNEXT PHASE — validate the winner on real LLM agents (costs money, cost-capped):")
    print(f"  python3 run_deepseek.py --config {cfg_path} --name \"{'-'.join(combo) or 'baseline'}\"")
    print(bar)


def run_optimization(rc: dict, *, sprints: int, matters: int, round_seeds: int = 8,
                     mc_seeds: int = 20, progress=None, provider: str = "mock",
                     model=None) -> dict:
    """Run the adaptive 3-round lever optimization for a firm config and return the
    `experiments` dict (the `optimize` key) the report consumes. Synchronous — the runner
    `provider`/`model` set which LLM drives the search simulations (default mock; pass
    e.g. provider="deepseek", model="deepseek-v4-flash" for a real-model search).
    calls it off the event loop (asyncio.to_thread) because run_trials spins its own loop."""
    _provider_state.provider = provider
    _provider_state.model = model
    from .run_config import build_firm, build_elasticities, build_objective
    set_base_firm(build_firm(rc.get("firm") or {}), build_elasticities(rc))
    cfg_objective = build_objective(rc)
    weights = cfg_objective["weights"]
    guardrails = cfg_objective["guardrails"]
    use_blend = len(weights) > 1
    primary = max(weights, key=weights.get)
    obj_key, obj_dir, obj_label, obj_is_dollar = OBJECTIVES[primary]

    opt_seeds = list(range(42, 42 + round_seeds))
    mc_list = list(range(100, 100 + mc_seeds))

    def make_stage(total: int):
        n = [0]

        def step(message: str) -> None:
            n[0] += 1
            if progress:
                progress(message, n[0], total)

        return step

    def score(pulled, seeds):
        if use_blend:
            return blended_score(pulled, seeds, sprints, matters, weights)
        return obj_dir * run_metric(pulled, seeds, sprints, matters, obj_key)

    KEEP_THRESH, SYN_THRESH = (0.01, 0.02) if use_blend else (
        (20_000, 50_000) if obj_is_dollar else (0.3, 0.5))

    # Round 1 — main effects (baseline + one score per lever)
    r1 = make_stage(1 + len(LEVERS))
    r1("Round 1 of 3 — baseline")
    baseline = score(set(), opt_seeds)
    baseline_margin = run_metric(set(), opt_seeds, sprints, matters, "matter_profit_margin")
    effects, margin_effects = {}, {}
    for i, lever in enumerate(LEVERS):
        r1(f"Round 1 of 3 — {lever} ({i + 1} of {len(LEVERS)})")
        effects[lever] = score({lever}, opt_seeds) - baseline
        margin_effects[lever] = run_metric({lever}, opt_seeds, sprints, matters, "matter_profit_margin") - baseline_margin
    ranked = sorted(effects.items(), key=lambda kv: kv[1], reverse=True)

    # Round 2 — factorial on top-2 + comp×pricing
    r2 = make_stage(2)
    positives = [lv for lv, d in ranked if d > 0]
    pair = positives[:2] if len(positives) >= 2 else [lv for lv, _ in ranked[:2]]
    top2 = positives[:2]
    a, b = pair[0], pair[1]
    alone = {x: effects[x] for x in (a, b)}
    r2(f"Round 2 of 3 — {a} + {b} together")
    both = score({a, b}, opt_seeds) - baseline
    additive = alone[a] + alone[b]
    synergy = both - additive
    r2("Round 2 of 3 — comp under AFA pricing")
    comp_under_afa = score({"comp", "pricing"}, opt_seeds) - score({"pricing"}, opt_seeds)

    # Round 3 — refinement
    best = set(top2)
    if comp_under_afa > 0:
        best.add("comp")
    remaining = [l for l in LEVERS if l not in best]
    r3 = make_stage(1 + len(remaining))
    r3("Round 3 of 3 — score current best")
    best_score = score(best, opt_seeds)
    for lever in remaining:
        r3(f"Round 3 of 3 — try adding {lever}")
        if score(best | {lever}, opt_seeds) - best_score > KEEP_THRESH:
            best.add(lever)

    # Guardrails
    guardrail_note = None
    if guardrails and not guardrails_ok(best, opt_seeds, sprints, matters, guardrails):
        from itertools import combinations
        combos = [set(c) for r in range(len(LEVERS) + 1) for c in combinations(LEVERS, r)]
        feasible = [c for c in combos if guardrails_ok(c, opt_seeds, sprints, matters, guardrails)]
        if feasible:
            prev = ", ".join(sorted(best)) or "none"
            best = max(feasible, key=lambda c: score(c, opt_seeds))
            guardrail_note = f"adaptive winner ({prev}) violated a guardrail; best FEASIBLE combo is {', '.join(sorted(best)) or 'none'}"
        else:
            best = set()
            guardrail_note = "no lever combination satisfies the guardrails — reporting baseline"

    # Final Monte Carlo
    r4 = make_stage(2)
    r4("Final check — Monte Carlo over the winner")
    win_vals = run_trials(best, mc_list, sprints, matters)[obj_key]
    win_mean = statistics.mean(win_vals)
    n = len(win_vals)
    spread = statistics.pstdev(win_vals)
    ci95 = 1.96 * statistics.stdev(win_vals) / math.sqrt(n) if n > 1 else 0.0
    r4("Final check — metrics")
    base_mc = run_metric(set(), mc_list, sprints, matters, obj_key)
    improvement = obj_dir * (win_mean - base_mc)
    ppp_win = run_metric(best, mc_list, sprints, matters, "ppp")

    ppp_base_opt = run_metric(set(), opt_seeds, sprints, matters, "ppp")
    # Per-lever trials capture both the effect and its own run-to-run spread — the noise
    # floor the report uses to refuse calling a within-spread lever a real finding.
    ppp_trials = {lv: run_trials({lv}, opt_seeds, sprints, matters)["ppp"] for lv in LEVERS}
    ppp_effects = {lv: statistics.mean(ppp_trials[lv]) - ppp_base_opt for lv in LEVERS}
    ppp_spreads = {lv: statistics.stdev(ppp_trials[lv]) if len(ppp_trials[lv]) > 1 else 0.0
                   for lv in LEVERS}
    ppp_base_mc = run_metric(set(), mc_list, sprints, matters, "ppp")

    # When to make each change — a timing pass over the winner, judged on cumulative profit.
    # Runs on the same (mock by default) search provider and seeds; cheap.
    r5 = make_stage(1)
    r5("Timing — when to make each change")
    timing = run_timing_search(sorted(best), seeds=opt_seeds, sprints=sprints, matters=matters,
                               weights=weights, guardrails=guardrails)

    movers = ", ".join(sorted(best)) or "(no lever reliably helps this objective)"
    story = f"[objective: {obj_label}] Pull {movers} (reliable movers). " + (
        "Then comp — it only helps AFTER AFA (under hourly it costs you)." if comp_under_afa > 0
        else "Skip comp — it doesn't help even under AFA.")

    return {
        "optimize": {
            "objective": primary,
            "objective_label": obj_label,
            "weights": weights,
            "guardrails": [f"{m}{op}{v:g}" for m, op, v in guardrails],
            "guardrail_note": guardrail_note,
            # Search scale — what the report quotes to show the size of the work behind
            # the recommendation.
            "round_seeds": round_seeds,
            "mc_seeds": mc_seeds,
            "sims_run": sims_run(),
            "baseline_ppp": ppp_base_opt,
            "baseline_objective": obj_dir * baseline,
            "main_effects": {lv: {"delta_ppp": ppp_effects[lv], "delta_objective": effects[lv],
                                  "delta_margin": margin_effects[lv],
                                  "spread_ppp": ppp_spreads[lv]} for lv in LEVERS},
            "interactions": {
                f"{a}x{b}": {"both": both, "additive": additive, "synergy": synergy},
                "comp_x_pricing": {"delta": comp_under_afa},
            },
            "best_combo": sorted(best),
            "best_objective": win_mean,
            "best_delta_objective": improvement,
            "best_ppp": ppp_win,
            "best_delta": ppp_win - ppp_base_mc,
            "spread": spread,
            "ci95": ci95,
            "story": story,
            # When to make each change — the timing pass over the winner. Renders as the
            # "When to make each change" block in the report; None when no lever was worth pulling.
            "timing": timing,
            # The two chart lines, apples-to-apples across the same seeds: the decline if
            # nothing changes vs the recovery under the recommended lever set. The lever-
            # optimization report's chart needs these just like the scenario report does,
            # or it renders a single line and loses the decision comparison.
            "ppp_trajectory": run_trajectory(best, mc_list, sprints, matters, "ppp"),
            "baseline_trajectory": run_trajectory(set(), mc_list, sprints, matters, "ppp"),
        }
    }


def run_scenario_mc(rc: dict, combo, *, sprints: int, matters: int,
                    mc_seeds: int = 20, progress=None, provider: str = "mock",
                    model=None) -> dict:
    """Re-run ONLY the final Monte Carlo for a determined lever set — no search rounds.

    This is the "Scenario Simulation" stage: the lever set is already fixed (by a prior
    lever optimization), and this measures it across `mc_seeds` fresh scenarios to refresh
    the confidence band. Returns the subset of the `optimize` dict that the band-dependent
    parts of the report read; callers overlay it onto the optimization's stored dict so the
    narrative stays intact and only the numbers move. Synchronous, like run_optimization."""
    _provider_state.provider = provider
    _provider_state.model = model
    from .run_config import build_firm, build_elasticities, build_objective
    set_base_firm(build_firm(rc.get("firm") or {}), build_elasticities(rc))
    weights = build_objective(rc)["weights"]
    primary = max(weights, key=weights.get)
    obj_key, obj_dir, obj_label, _ = OBJECTIVES[primary]

    combo = set(combo)
    mc_list = list(range(100, 100 + mc_seeds))

    def step(msg, i, n):
        if progress:
            progress(msg, i, n)

    step("Monte Carlo over the lever set", 1, 2)
    win_vals = run_trials(combo, mc_list, sprints, matters)[obj_key]
    win_mean = statistics.mean(win_vals)
    n = len(win_vals)
    spread = statistics.pstdev(win_vals)
    ci95 = 1.96 * statistics.stdev(win_vals) / math.sqrt(n) if n > 1 else 0.0

    step("baseline comparison", 2, 2)
    base_mc = run_metric(set(), mc_list, sprints, matters, obj_key)
    improvement = obj_dir * (win_mean - base_mc)
    ppp_win = run_metric(combo, mc_list, sprints, matters, "ppp")
    ppp_base_mc = run_metric(set(), mc_list, sprints, matters, "ppp")

    return {
        "best_combo": sorted(combo),
        "best_objective": win_mean,
        "best_delta_objective": improvement,
        "best_ppp": ppp_win,
        "best_delta": ppp_win - ppp_base_mc,
        "spread": spread,
        "ci95": ci95,
        "mc_seeds": mc_seeds,
        "sims_run": sims_run(),
        # Mean per-quarter PPP across the same seeds — baseline vs recommended — so the
        # report can draw the decline and the recovery on one axes (apples-to-apples).
        "ppp_trajectory": run_trajectory(combo, mc_list, sprints, matters, "ppp"),
        "baseline_trajectory": run_trajectory(set(), mc_list, sprints, matters, "ppp"),
    }


if __name__ == "__main__":
    main()
