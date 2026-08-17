"""
Legal-AI tool capability model — the "hot-swappable" layer (§7.9).

The simulation only cares about a tool's *behavioral profile*, not its code. So a
tool is modeled as a capability spec: which operations it supports, how accurate it
is at each, and how much tacit judgment each operation still leaves to a human.

"Hot-swap" = load a different `LegalTool` spec via `SimulationConfig.legal_tool`.
The tool's profile drives the AI-capable steps' `ai_error_rate` (from `accuracy`)
and, for the steps the tool does NOT support, disables AI entirely (`ai_capable=False`).

Why this is interesting, not cosmetic: different tools draw the codifiable/tacit
boundary in different places. Descrybe is strong on cite/quote/treatment verification
(→ B territory, low tacitness) but does not draft; Harvey is strong on drafting but
weak on verification (→ A territory). Swapping the tool changes *which seams* each
track wins, making tool choice a sweep dimension (strengthens Gate #3 robustness and
Gate #5 honest counterfactual).

Accuracy/tacit_residual values are [ASSUMPTION — calibrate]. Descrybe is available as
a live MCP tool in this workspace, so its `accuracy`/`tacit_residual` can be grounded
by actually probing `verify_quote`/`check_treatment` rather than guessed.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolOperation:
    """One capability of a legal-AI tool, with its error profile."""
    name: str              # "find_cases", "verify_quote", "check_treatment", "draft", "doc_review"
    supports: bool
    accuracy: float        # error rate 0-1 (probability the tool gets this operation wrong)
    tacit_residual: float  # fraction 0-1 that STILL needs human judgment after the tool


@dataclass(frozen=True)
class LegalTool:
    """A named legal-AI tool = a set of operations with error profiles."""
    name: str
    operations: dict[str, ToolOperation]

    def op(self, name: str) -> ToolOperation:
        """Return an operation, defaulting to 'unsupported' if absent."""
        return self.operations.get(
            name, ToolOperation(name=name, supports=False, accuracy=1.0, tacit_residual=1.0)
        )


# The five legal-AI operations the simulation models, mapped to workflow steps in
# orchestrator._apply_tool_profile.
OPERATIONS = ("find_cases", "verify_quote", "check_treatment", "draft", "doc_review")


def _tool(name: str, **ops) -> LegalTool:
    """Build a LegalTool, filling any missing operation with 'unsupported'."""
    full = {}
    for op in OPERATIONS:
        full[op] = ops.get(op, ToolOperation(name=op, supports=False, accuracy=1.0, tacit_residual=1.0))
    return LegalTool(name=name, operations=full)


# === TOOL REGISTRY ===
# Grounded in what each platform actually emphasizes (2026 GenAI legal stack):
# Descrybe/CoCounsel — cite/quote/treatment verification is the core product.
# Westlaw/Lexis AI — research + native shepardization/citation checks.
# Harvey — drafting/research assistant, verification not its core strength.
# mock — the zero-cost default for Phase 0-5 runs; moderate on everything.
TOOL_REGISTRY = {
    "descrybe": _tool("descrybe",
        find_cases=ToolOperation("find_cases", True, 0.05, 0.15),
        verify_quote=ToolOperation("verify_quote", True, 0.01, 0.05),
        check_treatment=ToolOperation("check_treatment", True, 0.05, 0.15),
        # Descrybe does not draft or run doc review.
    ),
    "cocounsel": _tool("cocounsel",
        find_cases=ToolOperation("find_cases", True, 0.06, 0.20),
        verify_quote=ToolOperation("verify_quote", True, 0.05, 0.15),
        check_treatment=ToolOperation("check_treatment", True, 0.08, 0.25),
        draft=ToolOperation("draft", True, 0.15, 0.45),
        doc_review=ToolOperation("doc_review", True, 0.13, 0.35),
    ),
    "westlaw_ai": _tool("westlaw_ai",
        find_cases=ToolOperation("find_cases", True, 0.05, 0.20),
        verify_quote=ToolOperation("verify_quote", True, 0.06, 0.20),  # KeyCite/Shepard's
        check_treatment=ToolOperation("check_treatment", True, 0.07, 0.25),
        draft=ToolOperation("draft", True, 0.15, 0.45),
        doc_review=ToolOperation("doc_review", True, 0.12, 0.35),
    ),
    "lexis_ai": _tool("lexis_ai",
        find_cases=ToolOperation("find_cases", True, 0.06, 0.20),
        verify_quote=ToolOperation("verify_quote", True, 0.07, 0.20),
        check_treatment=ToolOperation("check_treatment", True, 0.08, 0.25),
        draft=ToolOperation("draft", True, 0.14, 0.45),
        doc_review=ToolOperation("doc_review", True, 0.12, 0.35),
    ),
    "harvey": _tool("harvey",
        find_cases=ToolOperation("find_cases", True, 0.10, 0.35),
        verify_quote=ToolOperation("verify_quote", True, 0.25, 0.60),  # weak — hallucination risk
        check_treatment=ToolOperation("check_treatment", True, 0.20, 0.50),
        draft=ToolOperation("draft", True, 0.08, 0.35),               # strong on drafting
        doc_review=ToolOperation("doc_review", True, 0.10, 0.30),
    ),
    "mock": _tool("mock",
        find_cases=ToolOperation("find_cases", True, 0.10, 0.30),
        verify_quote=ToolOperation("verify_quote", True, 0.10, 0.30),
        check_treatment=ToolOperation("check_treatment", True, 0.12, 0.35),
        draft=ToolOperation("draft", True, 0.12, 0.40),
        doc_review=ToolOperation("doc_review", True, 0.08, 0.30),
    ),
}


def get_tool(name: str) -> LegalTool:
    """Look up a tool by name, raising on an unknown id."""
    if name not in TOOL_REGISTRY:
        raise ValueError(
            f"Unknown legal_tool {name!r}. Choose from: {', '.join(TOOL_REGISTRY)}"
        )
    return TOOL_REGISTRY[name]
