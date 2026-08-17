"""Sensitivity bands — turn each lever's point estimate into an honest range.

A single "seams -> +$600k" invites a skeptic to reject the number. The defensible
version is "+$300k to +$900k across a plausible range of the seam-response coefficient."
This runs the Monte Carlo lever effect at the LOW / BASE / HIGH of each lever's governing
elasticity and reports the resulting spread in PPP.

It's mock-LLM and cached, so the whole sweep is free and fast. The band reflects
coefficient uncertainty (how strongly the lever works), which is distinct from the
seed spread (run-to-run noise) the optimizer already reports.

Usage:
    /opt/homebrew/bin/python3 sensitivity.py [--seeds 12] [--sprints 16] [--matters 30]
"""
import os, sys, asyncio, contextlib, io, argparse, statistics

from .src.orchestrator import Orchestrator, SimulationConfig, FirmSignature
from .src.models.elasticities import DEFAULT_ELASTICITIES, default_profile
from .optimize import build_overrides, LEVERS, persist_experiment


def _ppp(pulled: set, seeds, sprints, matters, profile) -> float:
    """Mean final PPP across seeds for a lever set, under a given elasticity profile."""
    overrides = build_overrides(pulled)
    overrides["elasticities"] = profile
    vals = []
    for seed in seeds:
        cfg = SimulationConfig(sprints=sprints, matters_per_sprint=matters, llm_provider="mock",
                               seed=seed, output_dir="results/_sens", run_id="SENS", **overrides)
        o = Orchestrator(cfg)
        o.initialize()
        with contextlib.redirect_stdout(io.StringIO()):
            r = asyncio.run(o.run())
        h = r.company.metric_history.get("ppp")
        vals.append(h.values[-1].value if h and h.values else 0.0)
    return statistics.mean(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--sprints", type=int, default=16)
    ap.add_argument("--matters", type=int, default=30)
    args = ap.parse_args()
    seeds = list(range(42, 42 + args.seeds))

    # The coefficient whose range most drives each lever's PPP effect. Explicit (not
    # dict last-wins) and restricted to coefficients actually wired into the metric
    # equations, so the sweep moves the number.
    governing = {
        "pricing":  "margin_ai_afa_gain",     # how much AFA converts saved hours to margin
        "seams":    "margin_redline_penalty",  # the redline/rework cost the seam lever attacks
        "comp":     "adoption_comp_gain",      # how much paying for AI lifts adoption
        "leverage": "utilization_ai_cut",      # how hard AI compresses billable hours
    }
    print(f"\n=== Lever sensitivity bands ({args.seeds} seeds x {args.sprints} sprints) ===")
    print("Each lever's PPP effect, swept across the plausible range of its governing coefficient.\n")
    print(f"{'lever':10s} {'coefficient':26s} {'low':>14s} {'base':>14s} {'high':>14s}  band")

    bands = {}
    for lever in LEVERS:
        cid = governing.get(lever)
        if not cid:
            continue
        coef = DEFAULT_ELASTICITIES[cid]
        deltas = {}
        for where in ("low", "base", "high"):
            prof = default_profile().with_point(cid, where)
            base_ppp = _ppp(set(), seeds, args.sprints, args.matters, prof)
            lever_ppp = _ppp({lever}, seeds, args.sprints, args.matters, prof)
            deltas[where] = lever_ppp - base_ppp
        lo, hi = min(deltas.values()), max(deltas.values())
        bands[lever] = {"coefficient": cid, "coefficient_name": coef.name, "source": coef.source,
                        "low": deltas["low"], "base": deltas["base"], "high": deltas["high"],
                        "band_low": lo, "band_high": hi}
        print(f"{lever:10s} {coef.name:26s} {deltas['low']:>+14,.0f} {deltas['base']:>+14,.0f} "
              f"{deltas['high']:>+14,.0f}  {lo:+,.0f} .. {hi:+,.0f}")

    print("\nRead: the band is the honest deltarange — 'this lever moves PPP by X..Y depending on")
    print("how strongly the coefficient actually holds at your firm.' Calibrate the coefficient")
    print("(see elasticities.py calibration questions) to tighten it.")

    persist_experiment({"sensitivity": {"seeds": args.seeds, "sprints": args.sprints,
                                        "matters": args.matters, "bands": bands}})


if __name__ == "__main__":
    main()
