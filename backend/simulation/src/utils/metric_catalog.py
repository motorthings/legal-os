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
    what: str        # one-line plain-English definition — what the number IS
    why: str         # one-line plain-English reason it MATTERS to the firm
    group: str       # "pnl" | "causal" | "people"


METRICS = [
    # --- P&L: the "what moved" ---
    Metric("ppp", "Profit Per Partner", "$", "higher",
           "Profit left for each partner after all costs.",
           "The headline number — what each partner actually takes home.", "pnl"),
    Metric("rpl", "Revenue Per Lawyer", "$", "higher",
           "Total revenue for each lawyer.",
           "How productive each lawyer is — the money coming in before costs.", "pnl"),
    Metric("matter_profit_margin", "Matter Profit Margin", "%", "higher",
           "How much profit a matter earns.",
           "Whether each matter actually makes money, not just does work.", "pnl"),
    Metric("realization_rate", "Realization Rate", "%", "higher",
           "Of what you bill, how much actually gets paid.",
           "Billed is not the same as collected — this is the cash that really arrives.", "pnl"),
    Metric("utilization", "Associate Utilization", "hrs", "higher",
           "Billable hours per associate per year.",
           "How fully the junior lawyers are actually working on billable matters.", "pnl"),
    Metric("ai_assisted_matter_pct", "AI-Assisted Matters", "%", "higher",
           "Share of matters where AI touched a step.",
           "How widely the AI is actually being used, not just bought.", "pnl"),

    # --- Causal: the "why it moved" ---
    Metric("matter_cycle_time", "Matter Cycle Time", "mo", "lower",
           "Time from opening a matter to closing it.",
           "Faster matters bill sooner and tie up less work in progress.", "causal"),
    Metric("exception_rate", "Exception Rate", "%", "lower",
           "How often work hits a snag that needs a senior person.",
           "Every exception pulls a partner off their own work to rescue someone's.", "causal"),
    Metric("first_pass_accuracy", "First-Pass Accuracy", "%", "higher",
           "Share of work right the first time, no redo.",
           "Getting it right once is far cheaper than fixing it later.", "causal"),
    Metric("translation_debt_index", "Translation Debt", "/100", "lower",
           "How much meaning is lost when work passes between people.",
           "The quieter the loss, the more rework and missed details pile up.", "causal"),
    Metric("handoff_failure_rate", "Handoff Failure Rate", "%", "lower",
           "How often a hand-off between steps drops the ball.",
           "A clean hand-off keeps a matter moving; a broken one stalls it.", "causal"),
    Metric("redline_rework_rate", "Redline Rework Rate", "%", "lower",
           "How often a partner rewrites a draft instead of using it.",
           "Rewriting is the most expensive time in the firm — it doubles the cost of the work.", "causal"),

    # --- People & cost: the "what it cost" ---
    Metric("partner_ai_trust", "Partner AI Trust", "/10", "higher",
           "How much the partners trust the AI.",
           "If partners don't trust it, they won't use it — and the whole plan stalls.", "people"),
    Metric("associate_ai_trust", "Associate AI Trust", "/10", "higher",
           "How much the associates trust the AI.",
           "Associates do the daily work; their buy-in decides whether it sticks.", "people"),
    Metric("trust_polarization", "Trust Polarization", "/10", "lower",
           "How divided the firm is about the AI.",
           "A firm split on the AI can't move together — division is a cost, not a debate.", "people"),
    Metric("associate_attrition", "Associate Attrition", "%", "lower",
           "How many associates leave each year.",
           "If the bench keeps walking out, there's no one to do the work tomorrow.", "people"),
    Metric("collection_cycle", "Collection Cycle", "days", "lower",
           "Days from sending the bill to getting paid.",
           "The longer clients take to pay, the longer the firm funds the work itself.", "people"),
    Metric("wip_aging", "WIP Aging", "days", "lower",
           "Days of work done but not yet billed.",
           "Done-but-unbilled work is money the firm has earned but can't touch.", "people"),
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
