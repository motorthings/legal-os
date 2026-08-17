"""Single source of truth for the metrics the report and dashboard render.

Both `report.py` and `dashboard.py` import from here, so the two surfaces can
never drift apart on which metrics matter, what they're called, which direction
is better, or how they're grouped.

Metrics are organized into three groups that answer three different questions:

- **pnl** — "what moved": the P&L outcomes. The deltas a partner reads first.
- **causal** — "why it moved": the translation-debt and cycle-time levers that
  actually drove those P&L deltas.
- **people** — "what it cost": trust, attrition, and the slow-money drags
  (collection, WIP) that the P&L line hides.

`ai_assisted_matter_pct` is adoption — a leading input, not an outcome — so it
sits under P&L as its own line, not as a fabricated P&L delta.

Add, remove, or re-group a metric here and every page updates at once.
"""

from dataclasses import dataclass

# Group ids, in render order, with the short header label.
GROUPS = [
    ("pnl", "P&L"),
    ("causal", "Causal"),
    ("people", "People & cost"),
]

GROUP_READ = {
    "pnl": "what moved",
    "causal": "why it moved",
    "people": "what it cost",
}


@dataclass(frozen=True)
class Metric:
    id: str
    label: str
    unit: str        # "$", "%", "hrs", "days", "mo", "/100", "/10"
    direction: str   # "higher" (better) | "lower" (better)
    what: str        # one-line plain-English definition
    group: str       # "pnl" | "causal" | "people"


METRICS = [
    # --- P&L: the "what moved" ---
    Metric("ppp", "Profit Per Partner", "$", "higher",
           "Net income per equity partner — the single optimizing number.", "pnl"),
    Metric("rpl", "Revenue Per Lawyer", "$", "higher",
           "Total revenue per lawyer — top-line productivity.", "pnl"),
    Metric("matter_profit_margin", "Matter Profit Margin", "%", "higher",
           "Margin on a matter, especially under AFA/fixed fee.", "pnl"),
    Metric("realization_rate", "Realization Rate", "%", "higher",
           "Share of billed hours actually collected.", "pnl"),
    Metric("utilization", "Associate Utilization", "hrs", "higher",
           "Billable hours per associate per year.", "pnl"),
    Metric("ai_assisted_matter_pct", "AI-Assisted Matters", "%", "higher",
           "Adoption — matters where AI touched a workflow step.", "pnl"),

    # --- Causal: the "why it moved" ---
    Metric("matter_cycle_time", "Matter Cycle Time", "mo", "lower",
           "Sprints from intake to close.", "causal"),
    Metric("exception_rate", "Exception Rate", "%", "lower",
           "How often work hits an exception needing partner judgment.", "causal"),
    Metric("first_pass_accuracy", "First-Pass Accuracy", "%", "higher",
           "Share of work right the first time, no rework.", "causal"),
    Metric("translation_debt_index", "Translation Debt", "/100", "lower",
           "Meaning lost when work passes between steps.", "causal"),
    Metric("handoff_failure_rate", "Handoff Failure Rate", "%", "lower",
           "How often a handoff between steps breaks.", "causal"),
    Metric("redline_rework_rate", "Redline Rework Rate", "%", "lower",
           "How often the partner substantially rewrote an AI/associate draft.", "causal"),

    # --- People & cost: the "what it cost" ---
    Metric("partner_ai_trust", "Partner AI Trust", "/10", "higher",
           "How much partners trust the AI.", "people"),
    Metric("associate_ai_trust", "Associate AI Trust", "/10", "higher",
           "How much associates trust the AI.", "people"),
    Metric("trust_polarization", "Trust Polarization", "/10", "lower",
           "How divided the firm is about the AI.", "people"),
    Metric("associate_attrition", "Associate Attrition", "%", "lower",
           "Voluntary turnover of associates.", "people"),
    Metric("collection_cycle", "Collection Cycle", "days", "lower",
           "Days from invoice to payment.", "people"),
    Metric("wip_aging", "WIP Aging", "days", "lower",
           "Days of unbilled work-in-progress.", "people"),
]

# Convenience views.
METRIC_IDS = [m.id for m in METRICS]
DIRECTION = {m.id: m.direction for m in METRICS}
LOWER_BETTER = {m.id for m in METRICS if m.direction == "lower"}
METRIC_INFO = {m.id: m for m in METRICS}


def metrics_by_group() -> dict[str, list[Metric]]:
    """Return {group: [Metric, ...]} in GROUPS order."""
    out: dict[str, list[Metric]] = {}
    for gid, _label in GROUPS:
        out[gid] = [m for m in METRICS if m.group == gid]
    return out


# (id, label, unit, group) — the shape report.py and dashboard.py iterate.
KEY_METRICS = [(m.id, m.label, m.unit, m.group) for m in METRICS]
