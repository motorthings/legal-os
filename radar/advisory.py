"""Advisory seam — map the four effect-orders into two verdicts per fault line.

The integration between the radar (Part A, public landscape) and the firm (Part C,
private economics + enablement). For each fault line the radar tracks it answers TWO
separate questions, because standing up a governance control is not the same decision
as deploying more AI:

    GOVERN  "Is the control required of us now, and can we meet it?"
            Gated by: is-it-required/opportunistic, then firm readiness.
            NOT blocked by AI economics — the billable hour doesn't stop a firm
            standing up a competence program or data-governance it is required to have.
            -> no-mandate | build-capacity-first | stand-up-now

    DEPLOY  "Is now the time to put AI on the underlying work?"
            Gated by: pricing (the AI Profit Paradox), then whether the AI can capture
            the work yet (seam × capability). Only asked where AI does billable work
            (capability/deployment-driven lines); market-driven governance lines have
            no deploy question.
            -> watch | fix-pricing-first | defer | deploy-now

The four effect-orders, and where each comes from:

    Order 1  Capability   AI can now do the thing            radar L1 `capability`  (public)
    Order 2  Enablement   the market + firm can deploy it     E meter (public) + firm input (private)
    Order 3  Governance   the law reacts + fix becomes req'd  radar L2 `pressure` + L3 `adoption` (public)
    Order 4  Consequence  whether acting pays for THIS firm   AI-Profit-Paradox gate (derived)

Per-line annotations (fault_lines.FAULT_ANNOTATIONS) shape the gates:
  seam   codifiable/mixed/tacit — how capturable the underlying work is by current AI.
  driver capability/deployment/market — whether this control is about AI doing billable
         work (deploy question applies) or a market-driven governance response (deploy = n/a).

Determinism contract preserved: Orders 1 and 3 come from the radar's deterministic,
calibrated feed (never touched). Orders 2 and 4 are firm facts the operator supplies, not
predicted. The verdicts are pure, replayable functions of the inputs.
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --- Where the radar landscape lives ----------------------------------------
HERE = Path(__file__).resolve().parent                 # legal-os/radar
REPO = HERE.parent                                      # legal-os
DATA_JSON = REPO / "docs" / "radar" / "data.json"
FRONTEND_RADAR = REPO / "frontend" / "public" / "radar"

# --- Order 4 gate: reuse the paradox identity from legal-sim (single source) --
PRICING_DIR = HERE.parents[2] / "legal-sim" / "pricing"  # GitHub/legal-sim/pricing
sys.path.insert(0, str(PRICING_DIR))
try:
    from pricing_model import evaluate, ParadoxInputs, REFILL_BENCHMARK
    PRICING_OK = True
except Exception:  # pragma: no cover - mirror so the seam still runs standalone
    PRICING_OK = False
    REFILL_BENCHMARK = 0.25

    @dataclass(frozen=True)
    class ParadoxInputs:
        rate: float = 550.0; hours: float = 1800.0; addressable: float = 0.35
        compression: float = 0.40; refill: float = REFILL_BENCHMARK
        ai_cost: float = 6000.0; lawyers: int = 900; pass_through: float = 0.25

    def evaluate(i):
        class _R: pass
        f = i.hours * i.addressable * i.compression
        _R.hourly_delta = -i.rate * f * (1.0 - i.refill) - i.ai_cost
        _R.fixed_delta = i.rate * f * i.refill - i.rate * f * i.pass_through - i.ai_cost
        return _R()

# --- Decision thresholds (explicit, replayable) ------------------------------
MANDATORY_PRESSURE = 7.0     # rule pressure at/above = the law has moved (radar call threshold)
MANDATORY_ADOPTION = 7.0     # control-adoption at/above = table stakes already
OPPORTUNE_CAPABILITY = 6.5   # capability high enough to build value before it is mandatory
READY_ENABLEMENT = 6.0       # firm enablement (tools + skills + data) at/above = can deploy now
ENABLE_READY = 6.0           # market enablement E at/above = the market can supply mature tooling

SEAM_CAPTURE = {"codifiable": 1.0, "mixed": 0.6, "tacit": 0.35}   # work AI can free, per seam
MIN_CAPTURE = 0.05           # never let addressable go to zero (keep the math defined)
AI_WORK_DRIVERS = {"capability", "deployment"}   # only these lines ask the deploy question


@dataclass(frozen=True)
class FirmPosture:
    """Order 2 + Order 4 firm facts. Private, supplied by the operator/diagnostic,
    never predicted. pricing: 'hourly' | 'fixed_fee' | 'value_based'."""
    name: str = "Unnamed firm"
    pricing: str = "hourly"
    refill: float = REFILL_BENCHMARK
    enablement: float = 4.0               # Order 2 readiness, 0-10 (tools + skills + data)
    rate: float = 550.0
    hours: float = 1800.0
    addressable: float = 0.35
    compression: float = 0.40
    ai_cost: float = 6000.0
    lawyers: int = 900
    pass_through: float = 0.25


def _delta(f: FirmPosture, addressable: float, mode: str):
    i = ParadoxInputs(rate=f.rate, hours=f.hours, addressable=addressable,
                      compression=f.compression, refill=f.refill, ai_cost=f.ai_cost,
                      lawyers=f.lawyers, pass_through=f.pass_through)
    r = evaluate(i)
    return (r.hourly_delta if mode == "hourly" else r.fixed_delta), r.hourly_delta


def _base_gate(f: FirmPosture):
    """Order 4 at full capture: the headline paradox number for the firm's mode."""
    full = max(f.addressable, MIN_CAPTURE)
    mode_delta, hourly_full = _delta(f, full, f.pricing)
    return {"delta_per_lawyer": round(mode_delta), "firm_delta": round(mode_delta * f.lawyers),
            "hourly_full_capture": round(hourly_full), "mode": f.pricing, "refill": f.refill,
            "source": "AI Profit Paradox (legal-sim/pricing)"}


def _capture(seam: str, capability: float) -> float:
    """Fraction of the work AI actually frees for this control now = seam × capability."""
    return max(SEAM_CAPTURE.get(seam, 1.0) * min(capability / 10.0, 1.0), MIN_CAPTURE)


def _decide(fl, gate, base_hourly_full, f: FirmPosture):
    """Two verdicts per fault line: GOVERN (stand up the control) + DEPLOY (put AI on the work)."""
    cap, press, adopt = fl["capability"], fl["pressure"], fl["adoption"]
    enable = fl.get("enable", 5.0)
    seam, driver = fl.get("seam", "codifiable"), fl.get("driver", "market")
    ai_work = driver in AI_WORK_DRIVERS

    required = press >= MANDATORY_PRESSURE or adopt >= MANDATORY_ADOPTION
    opportune = (not required) and cap >= OPPORTUNE_CAPABILITY
    actionable = required or opportune

    # Per-control effective economics: capture-scaled (for the deploy axis only).
    capture = _capture(seam, cap) if ai_work else 1.0
    eff_delta, _ = _delta(f, max(f.addressable * capture, MIN_CAPTURE), f.pricing)

    # --- GOVERN: stand up the control? (governance, not economics) ----------
    if not actionable:
        govern, gnote = "no-mandate", "not yet required or open — nothing forces it now"
    elif f.enablement < READY_ENABLEMENT:
        govern, gnote = ("build-capacity-first",
                         "required/open but the firm can't meet it yet (Order 2 readiness low)")
    else:
        govern, gnote = ("stand-up-now",
                         "required/open and the firm is ready — stand the control up")

    # --- DEPLOY: put AI on the underlying work? (economics) ------------------
    if not ai_work:
        deploy, dnote = None, "not an AI-deployment question (market-driven governance control)"
    elif not actionable:
        deploy, dnote = "watch", "no deploy case yet — not required or opportunistic"
    elif f.pricing == "hourly" and base_hourly_full <= 0:
        deploy, dnote = ("fix-pricing-first",
                         f"hourly billing makes AI adoption a net loss "
                         f"(${gate['delta_per_lawyer']:,}/lawyer/yr at full capture)")
    elif eff_delta <= 0:
        deploy, dnote = ("defer",
                         f"AI can't yet capture this work profitably (seam={seam}, "
                         f"capability={cap:.1f})")
    elif enable < ENABLE_READY:
        deploy, dnote = ("defer",
                         f"the market can't supply mature tooling for this yet "
                         f"(market enablement E={enable:.1f} below {ENABLE_READY})")
    else:
        deploy, dnote = "deploy-now", "AI can capture this work, the economics pass, and the market can supply it"

    return {
        "fault_line": fl["id"],
        "title": fl["title"],
        "control": fl["control"],
        "horizon": fl["horizon"],
        "lead": fl["lead"],
        "seam": seam,
        "driver": driver,
        "required": required,
        "opportunistic": opportune,
        "govern": govern,
        "govern_note": gnote,
        "deploy": deploy,
        "deploy_note": dnote,
        "orders": {
            "1_capability": cap,          # Order 1 (public)
            "2_enablement": f.enablement,  # Order 2 (private firm input)
            "2_market_enable": enable,     # Order 2 (public market half, E)
            "3_pressure": press,          # Order 3 (public)
            "3_adoption": adopt,          # Order 3 (public)
            "4_gate_full": round(gate["delta_per_lawyer"]),   # Order 4 at full capture
            "4_gate_eff": round(eff_delta),                    # Order 4 capture-scaled
        },
    }


def run(firm: FirmPosture | None = None, data_path=DATA_JSON, as_of=None):
    firm = firm or FirmPosture()
    data = json.loads(Path(data_path).read_text())
    gate = _base_gate(firm)
    rows = [_decide(fl, gate, gate["hourly_full_capture"], firm) for fl in data["fault_lines"]]
    def _counts(key):
        c = {}
        for r in rows:
            v = r[key]
            if v is None:
                continue
            c[v] = c.get(v, 0) + 1
        return c
    return {
        "as_of": as_of or data["as_of"],
        "firm": {k: v for k, v in asdict(firm).items()},
        "economic_gate": gate,
        "thresholds": {"mandatory_pressure": MANDATORY_PRESSURE,
                       "mandatory_adoption": MANDATORY_ADOPTION,
                       "opportune_capability": OPPORTUNE_CAPABILITY,
                       "ready_enablement": READY_ENABLEMENT},
        "pricing_model_source": PRICING_OK,
        "verdict_counts": {"govern": _counts("govern"), "deploy": _counts("deploy")},
        "rows": rows,
    }


def _money(v):
    return "$" + f"{v:,}" if isinstance(v, int) else f"{v:.0f}"


def render_text(result):
    f = result["firm"]
    gate = result["economic_gate"]
    L = []
    L.append(f"Advisory seam — {f['name']}  (pricing={f['pricing']} · enablement={f['enablement']}/10)")
    L.append(f"  Order 4 full-capture (AI Profit Paradox) = {_money(gate['delta_per_lawyer'])}/lawyer/yr "
             f"[{gate['source']}]")
    L.append("")
    hdr = (f"{'FAULT LINE':<15}{'GOVERN':<20}{'DEPLOY':<20}  req opp  O1  O3p O3a")
    L.append(hdr); L.append("-" * len(hdr))
    for r in result["rows"]:
        o = r["orders"]
        gov = r["govern"]; dep = r["deploy"] if r["deploy"] else "—"
        L.append(f"{r['fault_line'][:15]:<15}{gov:<20}{dep:<20}  "
                 f"{'Y' if r['required'] else '.':<3} {'Y' if r['opportunistic'] else '.':<3}"
                 f" {o['1_capability']:>3} {o['3_pressure']:>3} {o['3_adoption']:>3}")
    L.append("")
    L.append("GOVERN = stand up the control (required + ready; economics never block a required "
             "control). DEPLOY = put AI on the work (pricing/capability gated; only AI-work lines).")
    L.append("Counts: " + json.dumps(result["verdict_counts"]))
    return "\n".join(L)


def write(result, out_dir=DATA_JSON.parent):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "advisory.json").write_text(json.dumps(result, indent=2))
    if FRONTEND_RADAR.parent.exists():
        FRONTEND_RADAR.mkdir(parents=True, exist_ok=True)
        (FRONTEND_RADAR / "advisory.json").write_text(json.dumps(result, indent=2))
    return out_dir / "advisory.json"


# Representative firm postures for the in-app advisory view (clear-labeled demos).
DEMO_POSTURES = [
    FirmPosture(name="Hourly firm", pricing="hourly", refill=0.15, enablement=7.0),
    FirmPosture(name="Fixed-fee firm", pricing="fixed_fee", refill=0.35, enablement=7.0),
    FirmPosture(name="Fixed-fee, building capacity", pricing="fixed_fee", refill=0.35, enablement=2.0),
]
DEMO_SLUGS = ["hourly", "fixed-fee", "fixed-fee-building"]


def write_demos():
    """Write one advisory.json per demo posture into the app's public dir so the in-app
    /radar/advisory view can fetch them. Firm-specific and clearly labeled; the app renders
    GOVERN/DEPLOY per posture. Called from build.py so it regenerates with the radar."""
    out = FRONTEND_RADAR / "advisory"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for firm, slug in zip(DEMO_POSTURES, DEMO_SLUGS):
        path = out / f"{slug}.json"
        path.write_text(json.dumps(run(firm), indent=2))
        written.append(str(path))
    return written


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Map the four effect-orders into govern + deploy verdicts.")
    p.add_argument("--pricing", default="hourly", choices=["hourly", "fixed_fee", "value_based"])
    p.add_argument("--refill", type=float, default=REFILL_BENCHMARK)
    p.add_argument("--enablement", type=float, default=4.0, help="Order 2 readiness, 0-10")
    p.add_argument("--name", default="Unnamed firm")
    p.add_argument("--write", action="store_true", help="write advisory.json next to data.json")
    a = p.parse_args()
    firm = FirmPosture(name=a.name, pricing=a.pricing, refill=a.refill, enablement=a.enablement)
    out = run(firm)
    print(render_text(out))
    if a.write:
        print("\nWrote", write(out))
