"""Plain-language actions — what a firm should actually do, per fault line.

The engine's own vocabulary is precise and useless to a firm owner. `fault_lines.py` names
each line's control as a noun phrase ("Verification-by-default with an audit trail") and its
`build_now` as a design intent ("so certification is a byproduct"). Both are correct for the
model and neither answers the question a managing partner asks, which is *what do I do on
Monday*.

So this is a presentation layer: one imperative per line, in the second person. It is
deliberately NOT in `fault_lines.py`, which is a frozen input to the forecast experiment —
copy is not evidence, and changing a sentence should not cost a re-freeze. Editing a string
here cannot move the fingerprint.

`why` is not written by hand. It is derived at render time from the line's actual evidence
(count, newest date, strongest source), so it stays true as the record moves instead of
going stale the way hand-written summaries do.
"""
from __future__ import annotations

# One imperative per fault line. Second person, present tense, no jargon, no noun phrases.
PLAIN_ACTIONS = {
    "verification": "Check every AI-assisted filing before it goes out",
    "disclosure": "Be able to prove who checked it, and when",
    "confidentiality": "Map where client data goes, and get no-training commitments in writing",
    "competence": "Train your lawyers on AI, and keep a record that you did",
    "convergence": "Run one AI policy, built to the strictest standard you operate under",
    "vendor_liability": "Document which AI tool produced which work",
    "judicial_analytics": "Stress-test strategy under uncertainty; never claim to predict a judge",
    "benchmark": "Benchmark an AI tool before you rely on it",
    "agentic": "Put human approval gates on any AI that acts on its own",
    "fees": "Measure value delivered, not hours saved",
    "insurance": "Be able to show your carrier the governance you actually run",
}

# Optional one-line consequence, shown under the action when present. Also free of jargon.
PLAIN_STAKES = {
    "verification": "Sanctions run to six figures, and they land on the signing lawyer.",
    "disclosure": "Courts are beginning to order disclosure up front, not just punish after.",
    "confidentiality": "Protective orders increasingly name which tools are allowed, and how.",
    "competence": "Bars are treating AI competence as a program requirement, not a personal one.",
    "convergence": "Operating to the strictest rule you touch is cheaper than tracking every patchwork.",
    "vendor_liability": "When a tool fails, the first question is what you can show about which one.",
    "judicial_analytics": "France criminalized judicial profiling; US direction is toward rules.",
    "benchmark": "A named benchmark turns a vendor claim into something you can check.",
    "agentic": "Scope-limiting and logging is the control that makes autonomy defensible.",
    "fees": "Billing on hours saved is what makes AI a net loss for an hourly firm.",
    "insurance": "Carriers are moving AI governance into underwriting and renewals.",
}


def plain_action(fault_id, fallback):
    return PLAIN_ACTIONS.get(fault_id, fallback)


def plain_stakes(fault_id):
    return PLAIN_STAKES.get(fault_id)
