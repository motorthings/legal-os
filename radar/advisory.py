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
DATA_JSON = REPO / "docs" / "radar" / "data.json"       # frozen experiment landscape
LIVE_JSON = REPO / "docs" / "radar" / "live.json"       # refreshable advisory landscape
FRONTEND_RADAR = REPO / "frontend" / "public" / "radar"

sys.path.insert(0, str(HERE))   # allow flat imports when run as a script
from calibration import CALL_THRESHOLD          # noqa: E402  (the mandate threshold)
import fault_lines as K                         # noqa: E402  (leverage classes)
import milestones                               # noqa: E402  (lead time, for sequencing)
import leverage                                 # noqa: E402  (who withholds what)

# --- Order 4 gate: reuse the paradox identity from legal-sim (single source) --
# HERE = legal-os/radar, so parents[1] = the directory holding the sibling repos
# (GitHub/). This was parents[2], which pointed one level above the repos and made the
# import fail silently: the seam then ran on the mirror constants below while still
# reporting legal-sim as its source. Keep the index at 1, and keep the fallback loud.
PRICING_DIR = HERE.parents[1] / "legal-sim" / "pricing"  # GitHub/legal-sim/pricing
sys.path.insert(0, str(PRICING_DIR))
try:
    from pricing_model import evaluate, ParadoxInputs, REFILL_BENCHMARK
    PRICING_OK = True
    PRICING_SOURCE = "AI Profit Paradox (legal-sim/pricing, imported)"
except Exception as _e:  # pragma: no cover - mirror so the seam still runs standalone
    PRICING_OK = False
    PRICING_SOURCE = (f"AI Profit Paradox (MIRROR CONSTANTS — legal-sim not importable: "
                      f"{type(_e).__name__}: {_e})")
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
# Two DIFFERENT reasons a control lands on a firm, kept apart because the remedies are
# different. A duty is comply-or-risk-sanction. A norm is compete-or-lose-work. The old
# `required = pressure OR adoption` fused them, which produced the same `stand-up-now`
# for `confidentiality` (13 ruling items, a binding rule) and for `insurance` (zero
# ruling items, two CNA renewal questionnaires).
MANDATED_PRESSURE = CALL_THRESHOLD   # a DUTY: the law has moved. IMPORTED, not restated —
                                      # this constant used to be a hardcoded 7.0 whose own
                                      # comment called it "the radar call threshold" while
                                      # calibration.CALL_THRESHOLD had moved to 8.0. Two
                                      # modules disagreeing about what "the law moved" means
                                      # is a bug, so there is now one source.
EXPECTED_ADOPTION = 7.0      # RETIRED FROM THE GATE 2026-09-17. Kept only so the number
                             # remains visible and comparable; nothing reads it to decide.
                             # Why it could not be calibrated: with leverage gating in place
                             # it reached only two lines (`insurance` 8.1, `fees` 5.3) and
                             # sweeping it 0-10 moved at most two verdicts; the adoption
                             # ground truth is one clean event; and the meter it thresholded
                             # rested on three items across eleven lines, two of them the same
                             # carrier. A control is table stakes when a NAMED ACTOR who can
                             # withhold something requires it (`leverage.py`), which is a
                             # countable fact rather than a fitted parameter.
OPPORTUNE_CAPABILITY = 6.5   # capability high enough to build value before it is mandatory
READY_ENABLEMENT = 6.0       # firm enablement (tools + skills + data) at/above = can act now
ENABLE_READY = 6.0           # market enablement E at/above = the market can supply mature tooling
MIN_DRIVING_EVIDENCE = 3     # the lane driving a verdict must carry at least this many items
                             # or the verdict is marked `thin`. `agentic` was being called
                             # `stand-up-now` off a single ruling item; n=1 is a signal to
                             # watch, not one to stand a control up over. Reported, not
                             # suppressed: the firm sees "mandated, thin evidence", which is
                             # exactly true.

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
    # Who can withhold something from THIS firm. Leverage is firm-relative: if your carrier
    # requires a control, it is table stakes for you, and a carrier requiring it in the trade
    # press is only a proxy for that. Same category as pricing and enablement — a stated firm
    # fact, not something to be estimated.
    carriers: tuple = ()          # malpractice carriers, e.g. ("CNA", "Chubb")
    key_clients: tuple = ()       # clients whose requirements bind, e.g. ("Acme Corp",)


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
            "pricing_model_imported": PRICING_OK, "source": PRICING_SOURCE}


def _capture(seam: str, capability: float) -> float:
    """Fraction of the work AI actually frees for this control now = seam × capability."""
    return max(SEAM_CAPTURE.get(seam, 1.0) * min(capability / 10.0, 1.0), MIN_CAPTURE)


def _decide(fl, gate, base_hourly_full, f: FirmPosture):
    """Two verdicts per fault line: GOVERN (stand up the control) + DEPLOY (put AI on the work)."""
    cap, press, adopt = fl["capability"], fl["pressure"], fl["adoption"]
    enable = fl.get("enable", 5.0)
    seam, driver = fl.get("seam", "codifiable"), fl.get("driver", "market")
    ai_work = driver in AI_WORK_DRIVERS

    # --- Why this control is on the board: duty, norm, or opportunity --------
    # `mandated` wins over `expected` when both trip: a duty outranks a market norm, and a
    # firm reading one label should see the heavier one.
    n_ruling = fl.get("n_ruling_evidence", 0)
    n_adopt = fl.get("n_adoption_evidence", 0)
    mandated = press >= MANDATED_PRESSURE
    # A market norm requires LEVERAGE, not a score: a NAMED ACTOR who can withhold something
    # (coverage, the engagement, the docket) must be requiring the control. `EXPECTED_ADOPTION`
    # is no longer read here — see its docstring for why it could not be calibrated.
    reqs = _leverage_facts()["by_fault_line"].get(fl["id"], {})
    actors = sorted(reqs)
    named = tuple(f.carriers) + tuple(f.key_clients)
    your_actors = [a for a in actors if leverage.actor_match(a, named)]
    expected = (not mandated) and bool(actors)
    opportune = (not mandated) and (not expected) and cap >= OPPORTUNE_CAPABILITY

    # GOVERN is gated on duty and norm ONLY. Opportunity is a DEPLOY input: it answers
    # "would this pay", not "is this required", and answering the second question with the
    # first produced GOVERN verdicts reading "required/open" for lines that were neither.
    govern_actionable = mandated or expected
    deploy_actionable = mandated or expected or opportune

    # Evidence floor: a verdict is only as good as the lane driving it. For a norm, an actor
    # the firm NAMED clears the floor by itself — one carrier requiring a control of you is
    # decisive in a way that two carriers requiring it of the market are not.
    driving_n = n_ruling if mandated else (n_adopt if expected else 0)
    if mandated:
        confidence = "supported" if driving_n >= MIN_DRIVING_EVIDENCE else "thin"
    elif expected:
        confidence = ("supported" if (your_actors or driving_n >= MIN_DRIVING_EVIDENCE)
                      else "thin")
    else:
        confidence = None

    # Per-control effective economics: capture-scaled (for the deploy axis only).
    capture = _capture(seam, cap) if ai_work else 1.0
    eff_delta, _ = _delta(f, max(f.addressable * capture, MIN_CAPTURE), f.pricing)

    # --- GOVERN: stand up the control? (governance, not economics) ----------
    ready = f.enablement >= READY_ENABLEMENT
    if not govern_actionable:
        govern = "no-mandate"
        gnote = "nothing on the record requires or expects this yet"
    elif not ready:
        govern = "build-capacity-first"
        gnote = (f"{'a duty' if mandated else 'a market norm'} the firm can't meet yet "
                 f"(Order 2 readiness below {READY_ENABLEMENT})")
    elif mandated:
        govern = "stand-up-now"
        gnote = "the law has moved and the firm is ready — stand the control up"
    else:
        govern = "match-the-market"
        if your_actors:
            gnote = (f"not a duty, but {', '.join(your_actors)} — an actor you named — "
                     f"requires it: match it or lose {'coverage' if not f.key_clients else 'work'}")
        else:
            gnote = (f"not a duty — {', '.join(actors)} requires it of firms like yours: "
                     f"match it or lose work")
    if confidence == "thin":
        gnote += (f" [thin: {driving_n} item(s) drive this, floor is {MIN_DRIVING_EVIDENCE}]")

    # --- DEPLOY: put AI on the underlying work? (economics) ------------------
    if not ai_work:
        deploy, dnote = None, "not an AI-deployment question (market-driven governance control)"
    elif not deploy_actionable:
        deploy, dnote = "watch", "no deploy case yet — not required, expected, or opportunistic"
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
        # Why it is on the board. `required` is kept as the union for back-compat, but the
        # two halves are now carried separately because they are different claims.
        "mandated": mandated,
        "expected": expected,
        # Who requires it, and whether that is someone the firm named. Empty on a line with
        # no leverage requirement, which is 9 of 11 lines today.
        "leverage_actors": actors,
        "leverage_is_yours": bool(your_actors),
        "leverage_requirements": [r["requirement"] for a in actors for r in reqs[a]],
        "opportunistic": opportune,
        "required": mandated or expected,
        "confidence": confidence,
        "driving_evidence": driving_n,
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


def landscape_path(prefer_live=True):
    """The advisory reads the LIVE landscape when one exists.

    The advisory answers a present-tense question ("what does the record oblige this firm
    to do now"), so it wants the freshest corpus. The frozen `data.json` is the
    experiment's landscape and stays frozen; preferring it here would sell a firm a stale
    answer to keep a research artifact clean. Falls back to the frozen landscape before
    the first live build, so nothing breaks on day one.
    """
    if prefer_live and LIVE_JSON.exists():
        return LIVE_JSON
    return DATA_JSON


# --- Sequencing: turn the board into a plan --------------------------------
# Ten rows all reading `stand-up-now` is a list, not direction. A firm needs an order.
# The order comes from the two things that actually differ between controls: WHY the
# control is on the board (duty beats norm) and whether the firm can meet it yet. Lead
# time from `milestones` is reported alongside, because a control you have 600 days of
# cover on is not the one to start today.
_TIERS = [
    ("duty-unsupported", "a duty the firm cannot yet meet — most urgent"),
    ("duty", "a duty, and the firm is ready"),
    ("norm-unsupported", "a market norm the firm cannot yet meet"),
    ("norm", "a market norm, and the firm is ready"),
    ("none", "nothing requires or expects this yet"),
]

_LEAD_CACHE = {}


def _milestone_facts():
    """Lead time per fault line + the pending precursors, read once.

    Memoized: grading replays the engine once per milestone, so recomputing this per
    posture would multiply that work by the number of demo postures for no new
    information.
    """
    if "v" in _LEAD_CACHE:
        return _LEAD_CACHE["v"]
    lead, overall, pending = {}, [], {}
    try:
        report = milestones.grade()
        buckets = {}
        for m in report["milestones"]:
            if m["status"] == "landed" and m["lead_days"] is not None:
                buckets.setdefault(m["fault_line"], []).append(m["lead_days"])
                overall.append(m["lead_days"])
            elif m["status"] == "pending" and m["antecedent_date"]:
                pending.setdefault(m["fault_line"], {"date": m["antecedent_date"],
                                                     "title": m["antecedent"]})
        for fid, ds in buckets.items():
            lead[fid] = sorted(ds)[len(ds) // 2]
    except Exception:
        pass
    facts = {"lead": lead,
             "overall": sorted(overall)[len(overall) // 2] if overall else None,
             "pending": pending}
    _LEAD_CACHE["v"] = facts
    return facts


_LEV_CACHE = {}


def _leverage_facts():
    """Resolved leverage requirements, read once. Memoized for the same reason as the
    milestone facts: `run()` is called per demo posture and this resolves against the
    corpus every time."""
    if "v" not in _LEV_CACHE:
        try:
            _LEV_CACHE["v"] = leverage.facts()
        except Exception as e:   # a bad reference must not take the whole advisory down
            _LEV_CACHE["v"] = {"requirements": [], "excluded": [], "by_fault_line": {},
                               "actors_by_line": {}, "error": f"{type(e).__name__}: {e}"}
    return _LEV_CACHE["v"]


def lead_by_line():
    """Median antecedent -> binding lead per fault line, plus the `_overall` median."""
    f = _milestone_facts()
    out = dict(f["lead"])
    out["_overall"] = f["overall"]
    return out


def _tier_of(row):
    if row["mandated"]:
        return 0 if row["govern"] == "build-capacity-first" else 1
    if row["expected"]:
        return 2 if row["govern"] == "build-capacity-first" else 3
    return 4


def sequence(rows):
    """Order the GOVERN board into a plan.

    The sort is, in order of precedence:

      1. tier        — duty before norm, and un-met before met
      2. confidence  — thin-evidence calls sort below supported ones
      3. urgency     — SHORTEST measured lead first. A line whose antecedents historically
                       bind in 192 days gives less warning than one that binds in 907, so it
                       is the one to start on. This is the axis that makes the output a plan
                       rather than a list.
      4. pressure    — tiebreak

    A line with no milestone of its own has no measured lead. It is REPORTED with the record
    median (labeled `lead_source="record median"`) but deliberately NOT ranked by it: an
    invented 601 would place it against lines that were actually measured. Those lines sort
    after the measured ones within their tier, ordered by pressure.
    """
    facts = _milestone_facts()
    leads = dict(facts["lead"]); leads["_overall"] = facts["overall"]
    ordered = sorted(
        rows,
        key=lambda r: (_tier_of(r),
                       0 if r["confidence"] != "thin" else 1,
                       0 if r["fault_line"] in leads else 1,
                       leads.get(r["fault_line"], 0),
                       -r["orders"]["3_pressure"]),
    )
    plan = []
    for i, r in enumerate(ordered, 1):
        t = _tier_of(r)
        r["tier"] = _TIERS[t][0]
        r["tier_note"] = _TIERS[t][1]
        r["sequence"] = i
        r["lead_days"] = leads.get(r["fault_line"], leads.get("_overall"))
        r["lead_source"] = ("this line" if r["fault_line"] in facts["lead"]
                            else "record median" if facts["overall"] else None)
        # A precursor on the record with nothing bound yet. GOVERN correctly says this is
        # not required of the firm, but saying only "no-mandate" read as "ignore it" for
        # `agentic`, which milestones.py simultaneously flags as actionable now. Both
        # statements are true; the row has to carry both or the two artifacts disagree.
        r["precursor"] = facts["pending"].get(r["fault_line"])
        if r["precursor"] and r["govern"] == "no-mandate":
            r["govern_note"] = (f"not required yet, but a precursor is on the record "
                                f"({r['precursor']['date']}): {r['precursor']['title']}")
        plan.append({
            "sequence": i,
            "fault_line": r["fault_line"],
            "control": r["control"],
            "tier": r["tier"],
            "govern": r["govern"],
            "confidence": r["confidence"],
            "lead_days": r["lead_days"],
            "why": (f"not required yet — precursor on the record "
                    f"({r['precursor']['date']})" if r["precursor"] and
                    r["govern"] == "no-mandate"
                    else r["govern_note"] if r["expected"] else r["tier_note"]),
            "precursor": r["precursor"],
        })
    return ordered, plan


def run(firm: FirmPosture | None = None, data_path=None, as_of=None):
    firm = firm or FirmPosture()
    data_path = data_path or landscape_path()
    data = json.loads(Path(data_path).read_text())
    gate = _base_gate(firm)
    rows = [_decide(fl, gate, gate["hourly_full_capture"], firm) for fl in data["fault_lines"]]
    rows, plan = sequence(rows)

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
        # Provenance of the record these verdicts rest on. A firm should be able to see
        # which corpus answered, and how current it is, without reading a log.
        "landscape": {
            "path": str(Path(data_path).name),
            "corpus": data.get("corpus", "frozen experiment landscape"),
            "n_items": data.get("n_items"),
            "freshness": data.get("freshness"),
        },
        "firm": {k: v for k, v in asdict(firm).items()},
        "economic_gate": gate,
        "thresholds": {"mandated_pressure": MANDATED_PRESSURE,
                       "mandated_pressure_source": "calibration.CALL_THRESHOLD (imported)",
                       "expected_adoption": EXPECTED_ADOPTION,
                       "expected_adoption_calibrated": False,
                       "expected_adoption_gates_anything": False,
                       "opportune_capability": OPPORTUNE_CAPABILITY,
                       "ready_enablement": READY_ENABLEMENT,
                       "min_driving_evidence": MIN_DRIVING_EVIDENCE},
        # The gate that replaced the number, stated so a reader can see what decided.
        "leverage_gate": {"rule": "a named actor who can withhold something requires it",
                          "actors_on_record": _leverage_facts()["actors_by_line"],
                          "reviewed_not_leverage":
                              [r["title"] for r in _leverage_facts()["excluded"]],
                          "your_actors": sorted(set(firm.carriers) | set(firm.key_clients))},
        "pricing_model_source": PRICING_OK,
        "verdict_counts": {"govern": _counts("govern"), "deploy": _counts("deploy")},
        "plan": plan,
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
    L.append("PLAN — the order to do them in")
    L.append(f"  {'#':<3}{'FAULT LINE':<19}{'GOVERN':<22}{'CONF':<11}{'LEAD':>7}  WHY")
    L.append("  " + "-" * 92)
    for p in result["plan"]:
        lead = f"{p['lead_days']}d" if p["lead_days"] else "—"
        L.append(f"  {p['sequence']:<3}{p['fault_line'][:18]:<19}{p['govern']:<22}"
                 f"{(p['confidence'] or '—'):<11}{lead:>7}  {p['why']}")
    L.append("")
    L.append(f"  {'FAULT LINE':<19}{'DEPLOY':<20}  O1  O3p O3a")
    for r in result["rows"]:
        o = r["orders"]
        dep = r["deploy"] if r["deploy"] else "—"
        L.append(f"  {r['fault_line'][:18]:<19}{dep:<20}  "
                 f"{o['1_capability']:>3} {o['3_pressure']:>3} {o['3_adoption']:>3}")
    L.append("")
    L.append("GOVERN = stand the control up. A DUTY (the law moved, pressure >= "
             f"{MANDATED_PRESSURE:.0f}) is comply-or-risk-sanction and is never blocked by "
             "economics. A NORM (table stakes, adoption >= "
             f"{EXPECTED_ADOPTION:.0f}) is compete-or-lose-work. `thin` = fewer than "
             f"{MIN_DRIVING_EVIDENCE} items drive the call.")
    L.append("DEPLOY = put AI on the work (pricing/capability gated; only AI-work lines).")
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
    # Carriers named, to show the firm-relative leverage read: the same norm verdict, but
    # `supported` rather than `thin`, because an actor that can withhold THIS firm's
    # coverage requires it. The other two demos name none, which is the generic read.
    FirmPosture(name="Fixed-fee firm", pricing="fixed_fee", refill=0.35, enablement=7.0,
                carriers=("CNA",)),
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
    p.add_argument("--carrier", action="append", default=[],
                   help="a malpractice carrier that can withhold coverage (repeatable)")
    p.add_argument("--client", action="append", default=[],
                   help="a client whose requirements bind (repeatable)")
    p.add_argument("--write", action="store_true", help="write advisory.json next to data.json")
    a = p.parse_args()
    firm = FirmPosture(name=a.name, pricing=a.pricing, refill=a.refill,
                       enablement=a.enablement,
                       carriers=tuple(a.carrier), key_clients=tuple(a.client))
    out = run(firm)
    print(render_text(out))
    if a.write:
        print("\nWrote", write(out))
