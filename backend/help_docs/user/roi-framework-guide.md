# ROI Framework

The ROI Framework measures AI solution performance across three dimensions: time saved, cost impact, and quality metrics. Every number is backed by the audit trail — not estimates, not surveys, not vendor claims.

## Three Dimensions

### 1. Cost Impact

Cost impact = time saved × the appropriate billable rate. This is human cost avoided, not API token cost.

**How rates are resolved:**

1. Check for a client-specific rate for the practice group
2. Check for a practice-group-wide rate
3. Fall back to the default blended rate

Rates have effective-from and effective-to dates. The system uses the rate that was active at the time of the invocation.

**Rate types:**
- Blended (default)
- Partner
- Associate

### 2. Quality Metrics

Quality is tracked through structured attorney reviews:

- **Accuracy Rate** — Percentage of outputs rated correct or with minor issues
- **Override Rate** — Percentage of outputs where the attorney overrode the AI recommendation
- **False Positive Rate** — Percentage of outputs incorrectly flagged as issues
- **False Negative Rate** — Percentage of real issues the AI missed
- **Agreement Score** — How closely attorney review matched AI assessment (0-100)

If 40% of outputs are being overridden, the AI is not helping — it's creating more work. The override rate is the most important quality metric.

### 3. Adoption Rate

Adoption = active users / eligible users, not "who clicked once."

- **Eligible users** — Attorneys in practice groups where AI functions are available
- **Active users** — At least one invocation in the measurement period (default: 30 days)
- **Adoption %** — Active / eligible × 100

A raw count of "50 lawyers used Harvey" means nothing without the denominator. 50 out of 50 is great. 50 out of 500 is a problem.

## ROI Summary

The ROI summary endpoint aggregates all three dimensions:

- **Total Cost Avoided** — Sum of (time saved × rate) across all invocations
- **Total AI Cost** — LLM API costs (including multi-step pipeline costs where applicable)
- **Net ROI** — Cost avoided minus AI cost
- **ROI Ratio** — Cost avoided / AI cost (e.g., "$12.40 saved for every $1 spent")

## Baselines

Time-saved calculations depend on calibrated baselines — how long did this task take before AI? Every baseline record includes:

- **Methodology** — How was this established? (time study, expert estimate, survey, historical data)
- **Sample Size** — How many manual timings?
- **Confidence Level** — Low, medium, or high
- **Calibrated By** — Who established the baseline?
- **Calibrated At** — When was it last updated?

When a partner or client asks "how do you know this used to take 2 hours?", the answer is in the baseline record — not an assertion.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/roi/summary` | Full ROI summary with by-function breakdown |
| `GET /api/roi/cost-impact` | Cost avoided for a specific function |
| `GET /api/roi/quality/summary` | Aggregate quality metrics |
| `GET /api/roi/adoption` | Adoption rate with eligible/active counts |
| `GET /api/roi/baselines` | List all baselines with methodology |
| `PUT /api/roi/baselines/{id}` | Update baseline with calibration metadata |
