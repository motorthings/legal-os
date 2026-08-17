"""
Run-config files — one file is a firm's ENTIRE setup: run scale, signature, levers,
calibrated elasticities, and optimization priorities. This is the config contract the
UI will POST (see docs/PRD.md) and the CLI launchers read today.

Keeps the launchers (run_deepseek.py / run_firm.py) NEUTRAL: with no config they run the
baseline firm; with `--config configs/<file>.json` they run exactly what the file specifies.

Schema (every block optional; anything omitted falls back to the archetype default):

    {
      "name": "recommended — pricing + seams + comp",   # label, surfaced in meta/report
      "run": {                       # run scale + LLM/tool selection
        "sprints": 16,
        "matters_per_sprint": 30,
        "seed": 42,
        "max_cost": 5.0,             # real-LLM spend cap ($); null = no cap
        "model": "deepseek-v4-flash",# LLM model id (null = provider default)
        "legal_tool": "mock"         # mock|descrybe|harvey|cocounsel|westlaw_ai|lexis_ai
      },
      "firm": {                      # FirmSignature via intake.build_firm — incl. pricing + leverage
        "pricing_posture": "afa_native",
        "leverage_ratio": 3.5
      },
      "levers": {                    # the non-signature lever knobs
        "comp_lever_strength": 0.9,
        "codify_seams": true,
        "decision_latency_sprints": 1
      },
      "elasticities": {              # firm-calibrated transfer-function coefficients (else defaults)
        "margin_ai_afa_gain": 0.20,  # keys are elasticity ids; see src/models/elasticities.py
        "seam_incident_slope": 0.6
      },
      "objective": {                 # optimization priorities (consumed by optimize.py)
        "weights": {"ppp": 0.6, "retention": 0.4},   # firm-priority blend (normalized)
        "guardrails": ["associate_attrition<=25", "realization_rate>=70"]
      }
    }
"""
import json
from pathlib import Path

from .src.orchestrator import SimulationConfig
from .src.models.elasticities import ElasticityProfile, DEFAULT_ELASTICITIES, default_profile
from .intake import build_firm

_RUN_DEFAULTS = {"sprints": 16, "matters_per_sprint": 30, "seed": 42,
                 "max_cost": None, "model": None, "legal_tool": "mock"}
_LEVER_DEFAULTS = {"comp_lever_strength": 0.3, "codify_seams": False,
                   "decision_latency_sprints": 2}


def load_run_config(path: str | Path) -> dict:
    """Read a run-config JSON file."""
    return json.loads(Path(path).read_text())


def build_elasticities(rc: dict) -> ElasticityProfile:
    """Turn the `elasticities` block (firm calibration) into an ElasticityProfile. Unknown
    coefficient ids are a hard error — a typo shouldn't silently run on defaults."""
    overrides = rc.get("elasticities") or {}
    prof = default_profile()
    for cid, val in overrides.items():
        if cid not in DEFAULT_ELASTICITIES:
            raise ValueError(f"unknown elasticity {cid!r}; valid: {sorted(DEFAULT_ELASTICITIES)}")
        prof = prof.with_override(cid, float(val))
    return prof


def build_objective(rc: dict) -> dict:
    """Turn the `objective` block into {weights, guardrails} for the optimizer. Weights are
    normalized to sum 1; guardrails are (metric, op, value) tuples. Empty block => PPP alone."""
    from .optimize import OBJECTIVES, parse_guardrails
    obj = rc.get("objective") or {}
    raw_weights = obj.get("weights") or {"ppp": 1.0}
    for k in raw_weights:
        if k not in OBJECTIVES:
            raise ValueError(f"unknown objective {k!r}; valid: {list(OBJECTIVES)}")
    total = sum(raw_weights.values())
    if total <= 0:
        raise ValueError("objective weights must sum to a positive number")
    weights = {k: v / total for k, v in raw_weights.items()}
    guardrails = parse_guardrails(obj.get("guardrails") or [])
    return {"weights": weights, "guardrails": guardrails}


def build_sim_config(rc: dict, *, provider: str, output_dir: str, **overrides) -> SimulationConfig:
    """Turn a run-config dict into a SimulationConfig for the given LLM provider.

    `overrides` (e.g. from CLI flags) win over the file; a None override is ignored, so
    a launcher can pass `sprints=args.sprints or None` and let the file decide when unset.
    (The `objective` block is not part of a single run — it drives the optimizer — so it is
    parsed separately via build_objective, not here.)
    """
    run = {**_RUN_DEFAULTS, **(rc.get("run") or {})}
    run.update({k: v for k, v in overrides.items() if v is not None})
    firm = build_firm(rc.get("firm") or {})
    levers = {**_LEVER_DEFAULTS, **(rc.get("levers") or {})}
    return SimulationConfig(
        sprints=run["sprints"],
        matters_per_sprint=run["matters_per_sprint"],
        seed=run["seed"],
        max_cost=run["max_cost"],
        llm_provider=provider,
        llm_model=run["model"],
        legal_tool=run["legal_tool"],
        firm_name=rc.get("firm_name") or rc.get("name", "Aldrich & Vale LLP"),
        firm_signature=firm,
        elasticities=build_elasticities(rc),
        output_dir=output_dir,
        comp_lever_strength=levers["comp_lever_strength"],
        codify_seams=levers["codify_seams"],
        decision_latency_sprints=levers["decision_latency_sprints"],
    )
