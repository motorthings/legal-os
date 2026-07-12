# Portfolio Dashboard

The Dashboard provides a consolidated view of AI program performance across all functions: hours saved, cost avoided, net ROI, adoption, and quality metrics.

## KPI Cards

The top row displays four key metrics for the selected period:

- **Hours Saved** — Aggregate attorney time saved across all functions, based on calibrated baselines (not estimates)
- **Cost Avoided** — Hours saved × the appropriate billable rate (blended, partner, or associate rate from rate cards)
- **Net ROI** — Cost avoided minus AI costs (LLM API tokens + infrastructure). The ROI ratio shows dollars saved per dollar spent
- **Adoption** — Active users / eligible users, refreshed on a 30-day rolling window

## Period Selector

Use the period selector to switch between 30-day, 90-day (quarterly), and 365-day (annual) views. All metrics, charts, and breakdowns recalculate for the selected period.

## Function Breakdown

The table below the KPI cards breaks down each function by:

- **Invocations** — Total number of AI function calls in the period
- **Hours Saved** — Time saved per function, based on calibrated baselines
- **Cost Avoided** — Hours saved × applicable rate
- **AI Cost** — LLM API costs for those invocations (including multi-step pipeline costs for complex functions)
- **Net ROI** — Cost avoided minus AI cost

Column headers include tooltips explaining the calculation methodology. Hover over **AI Cost**, **Cost Avoided**, or **Invocations** to see details.

## Quality Metrics

The quality section shows aggregate metrics from attorney quality reviews:

- **Accuracy Rate** — Percentage of outputs rated correct or with minor issues
- **Override Rate** — Percentage of outputs where the attorney overrode the AI recommendation
- **False Positive Rate** — Percentage of outputs incorrectly flagged as issues

## Hours Saved Chart

A bar chart visualizes hours saved by function for the selected period, making it easy to identify which functions deliver the most time savings.

## How Rates Are Resolved

Cost avoided calculations use rate cards that support:

- **Client-specific rates** — Different clients may have different rate agreements
- **Practice group rates** — Different practice areas may bill at different rates
- **Rate types** — Blended, partner, and associate rates
- **Effective dating** — Rates have effective-from and effective-to dates

The system resolves the most specific applicable rate: client + practice group first, then practice group only, then the default blended rate.
