# Frequently Asked Questions

## General

### What is Legal AI OS?

Legal AI OS is a governed AI platform for legal enterprises. It provides an independent measurement, governance, and enablement layer around existing AI tools like Harvey AI. It does not replace Harvey — it measures, audits, and certifies what Harvey produces.

### Who is this for?

K&I Program Managers, Innovation leads, Practice Operations directors, and anyone responsible for proving that AI is working, safe, and worth it in a law firm.

### Does Legal AI OS store client data?

The platform's governance architecture enforces client data isolation through Row-Level Security (RLS). The platform's LLM provider (DeepSeek) does not train on API data. The audit trail records decisions, not documents.

## Harvey Monitor

### Why evaluate Harvey separately?

AI has a fundamental conflict of interest: the same system that generates an output cannot reliably evaluate that output. Harvey Monitor runs separate, specialized evaluator agents — each trained to be skeptical and exhaustive — producing an independent score.

### How often should I run evaluations?

At minimum: weekly drift checks to detect behavioral degradation. Per-invocation evaluation for high-stakes outputs (litigation, regulatory filings, client deliverables). Monthly full evaluations for each active agent.

### What triggers the veto?

Any Tier 1 dimension (Accuracy, Safety, Bias) scoring below 75 caps the final score at 74.9. This means an output with a hallucinated citation, a confidentiality gap, or biased reasoning cannot receive certification — no matter how well it performs elsewhere.

### What if the Anthropic API key isn't available?

The evaluation system automatically falls back to the configured default provider (DeepSeek). Evaluations complete successfully regardless of which provider is available.

## ROI & Dashboard

### How is cost avoided calculated?

Time saved (from calibrated baselines) × the applicable billable rate (from rate cards). This is human cost avoided — not API token cost. A task that used to take 2 hours at $500/hour that now takes 30 seconds represents approximately $1,000 in cost avoided per invocation.

### What if we haven't calibrated baselines?

Calibrated baselines produce the most defensible numbers. You can establish baselines through time studies, expert estimates, surveys, or historical data. Each baseline records its methodology, sample size, and confidence level so the methodology is transparent — you can always explain how you know.

### What's included in AI Cost?

LLM API token costs for all steps in the pipeline. For complex functions, this includes multi-step costs: router + evaluator + hallucination check + parallel verification + scoring. These are real costs, not estimates.

## POC Pipeline

### What's the difference between Graduated and Cancelled?

Graduated projects have passed attorney review and are deployed for regular use. Cancelled projects were terminated — they may have been superseded, deemed infeasible, or no longer needed. Cancellation is not a failure; it's a decision.

### Can I reopen a cancelled project?

Currently, cancelled projects are terminal. You can create a new POC with similar scope if the need re-emerges.
