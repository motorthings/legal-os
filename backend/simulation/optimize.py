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
import argparse, asyncio, contextlib, io, json, math, os, sys, statistics
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


def blended_score(pulled: set, seeds, sprints, matters, weights: dict) -> float:
    """Weighted, unit-normalized objective score. Each component is expressed as
    percentage improvement over the no-lever baseline (direction-signed so bigger is
    always better), then weighted. Normalizing to % makes dollars and percentage-point
    metrics comparable in one blend."""
    total = 0.0
    for obj_key, w in weights.items():
        metric, direction, _, _ = OBJECTIVES[obj_key]
        base = run_metric(set(), seeds, sprints, matters, metric)
        val = run_metric(pulled, seeds, sprints, matters, metric)
        denom = abs(base) if abs(base) > 1e-9 else 1.0
        total += w * direction * (val - base) / denom
    return total


def guardrails_ok(pulled: set, seeds, sprints, matters, guardrails: list) -> bool:
    """True if the pulled-lever combo satisfies every guardrail (on the seed-mean)."""
    for metric, op, bound in guardrails:
        val = run_metric(pulled, seeds, sprints, matters, metric)
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


def build_overrides(pulled: set) -> dict:
    """Merge the config for a set of pulled levers, starting from the base firm (or archetype)."""
    import copy
    sig = copy.deepcopy(_BASE_FIRM) if _BASE_FIRM is not None else FirmSignature()
    if "pricing" in pulled:
        sig.pricing_posture = "afa_native"
    if "leverage" in pulled:
        sig.leverage_ratio = 5.0
    overrides = {"firm_signature": sig}
    if _BASE_ELASTICITIES is not None:
        overrides["elasticities"] = _BASE_ELASTICITIES
    overrides["comp_lever_strength"] = 0.9 if "comp" in pulled else 0.0
    overrides["decision_latency_sprints"] = 1 if "latency" in pulled else 5
    overrides["codify_seams"] = "seams" in pulled
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


def run_trials(pulled: set, seeds, sprints, matters):
    """Return {metric: [per-seed final values]}. Cached by (levers, seeds, size)
    so a combination tested in one round isn't re-simulated in the next."""
    key = (frozenset(pulled), tuple(seeds), sprints, matters)
    if key in _TRIAL_CACHE:
        return _TRIAL_CACHE[key]
    overrides = build_overrides(pulled)
    out = {m: [] for m in _COLLECT}
    _SIMS_RUN[0] += len(seeds)
    for seed in seeds:
        cfg = SimulationConfig(sprints=sprints, matters_per_sprint=matters,
                               llm_provider="mock", seed=seed, output_dir="results/_opt",
                               run_id="OPT", **overrides)
        o = Orchestrator(cfg)
        o.initialize()
        with contextlib.redirect_stdout(io.StringIO()):
            r = asyncio.run(o.run())
        for m in _COLLECT:
            h = r.company.metric_history.get(m)
            out[m].append(h.values[-1].value if h and h.values else 0.0)
    _TRIAL_CACHE[key] = out
    return out


def run_metric(pulled: set, seeds, sprints, matters, key: str) -> float:
    return statistics.mean(run_trials(pulled, seeds, sprints, matters)[key])


def run_ppp(pulled: set, seeds, sprints, matters) -> float:
    return run_metric(pulled, seeds, sprints, matters, "ppp")


def run_margin(pulled: set, seeds, sprints, matters) -> float:
    return run_metric(pulled, seeds, sprints, matters, "matter_profit_margin")


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
    ppp_effects = {lv: run_metric({lv}, opt_seeds, args.sprints, args.matters, "ppp") - ppp_base_opt
                   for lv in LEVERS}
    ppp_base_mc = run_metric(set(), mc_seeds, args.sprints, args.matters, "ppp")
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
                                  "delta_margin": margin_effects[lv]}
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
                     mc_seeds: int = 20, progress=None) -> dict:
    """Run the adaptive 3-round lever optimization for a firm config and return the
    `experiments` dict (the `optimize` key) the report consumes. Synchronous — the runner
    calls it off the event loop (asyncio.to_thread) because run_trials spins its own loop."""
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
    ppp_effects = {lv: run_metric({lv}, opt_seeds, sprints, matters, "ppp") - ppp_base_opt for lv in LEVERS}
    ppp_base_mc = run_metric(set(), mc_list, sprints, matters, "ppp")

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
                                  "delta_margin": margin_effects[lv]} for lv in LEVERS},
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
        }
    }


def run_scenario_mc(rc: dict, combo, *, sprints: int, matters: int,
                    mc_seeds: int = 20, progress=None) -> dict:
    """Re-run ONLY the final Monte Carlo for a determined lever set — no search rounds.

    This is the "Scenario Simulation" stage: the lever set is already fixed (by a prior
    lever optimization), and this measures it across `mc_seeds` fresh scenarios to refresh
    the confidence band. Returns the subset of the `optimize` dict that the band-dependent
    parts of the report read; callers overlay it onto the optimization's stored dict so the
    narrative stays intact and only the numbers move. Synchronous, like run_optimization."""
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
    }


if __name__ == "__main__":
    main()
