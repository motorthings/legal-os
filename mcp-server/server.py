"""Legal OS MCP server.

Self-contained legal tools exposed over the Model Context Protocol (MCP).

Deliberately deterministic — no LLM, no external API, no database. This is the
"programmatic over LLM" principle from the legal-os architecture, but for a toy
surface: every tool is a plain function whose docstring becomes the tool's
description and whose signature becomes its input schema.

Run locally:
    mcp dev server.py                # interactive inspector (needs `mcp[cli]`)
    python server.py                 # Streamable HTTP on :8000

Run the HTTP transport and connect from Claude Code:
    claude mcp add --transport http legal-os http://localhost:8000/mcp
"""

from __future__ import annotations

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

# --- Server -----------------------------------------------------------------

mcp = FastMCP(
    "legal-os",
    instructions=(
        "Legal productivity tools: contract clause triage, NDA screening, risk "
        "scoring, and full citation verification against the Descrybe Legal "
        "Engine. Deterministic scoring — the model provides no judgment, only "
        "the caller. Results are structured JSON so downstream code can act on "
        "them."
    ),
    # Bind 0.0.0.0 because uvicorn (below) listens on all interfaces behind
    # Fly's proxy. This also disables FastMCP's localhost-only DNS-rebinding
    # guard, which would otherwise reject the public Host header.
    host="0.0.0.0",
)

# --- Rule tables (deterministic) -------------------------------------------

# RED terms are deal-breakers for that clause type. YELLOW terms are worth
# flagging for a human. Matching is substring, case-insensitive.
_CLAUSE_RULES: dict[str, dict[str, set[str]]] = {
    "liability": {
        "red": {
            "uncapped",
            "unlimited liability",
            "consequential damages",
            "lost profits",
            "indirect damages",
            "no cap",
        },
        "yellow": {
            "cap exceeds 12 months",
            "one-sided cap",
            "supercap",
            "carve-out for gross negligence",
        },
    },
    "indemnification": {
        "red": {
            "unilateral indemnification",
            "uncapped indemnification",
            "defend any claim",
            "indemnify for third party acts",
        },
        "yellow": {
            "no mutual indemnity",
            "sole discretion to settle",
            "no notice requirement",
        },
    },
    "ip": {
        "red": {
            "work for hire",
            "assignment of all ip",
            "broad assignment",
            "joint ownership",
            "perpetual license",
        },
        "yellow": {
            "background ip license",
            "improvements assigned",
            "no carve-out for pre-existing ip",
        },
    },
    "confidentiality": {
        "red": {
            "no dpa",
            "cross-border transfer",
            "unlimited retention",
            "no return or destroy",
        },
        "yellow": {
            "no sub-processor notice",
            "no breach notification",
            "residual knowledge clause",
        },
    },
    "termination": {
        "red": {
            "auto-renewal",
            "termination for convenience by one party",
            "survival of all provisions",
        },
        "yellow": {
            "no cure period",
            "immediate termination",
            "no post-termination obligations",
        },
    },
}

# Standard provisions an NDA should contain. Each maps to the phrase(s) that
# signal it's present.
_NDA_CARVEOUTS: list[dict[str, str | list[str]]] = [
    {"key": "confidentiality_definition", "label": "Confidential information is defined", "markers": ["confidential information", "confidential information means", "defined as"]},
    {"key": "permitted_disclosures", "label": "Compelled-by-law disclosure permitted", "markers": ["compelled", "required by law", "court order", "subpoena", "legal requirement"]},
    {"key": "return_or_destroy", "label": "Return-or-destroy on termination", "markers": ["return or destroy", "return and destroy", "destroy all", "return all"]},
    {"key": "survival", "label": "Confidentiality survives termination", "markers": ["survive", "survival", "survives termination"]},
    {"key": "term", "label": "Defined term / duration", "markers": ["years", "months", "term of this agreement", "for a period"]},
]

# Standard NDA carve-outs that are RED flags (they gut the protection).
_NDA_RED_FLAGS: list[dict[str, str | list[str]]] = [
    {"key": "no_written_requirement", "label": "Oral-only disclosures protected", "markers": ["oral", "verbally", "not in writing"]},
    {"key": "residual_knowledge", "label": "Residual knowledge clause", "markers": ["residual knowledge", "residual information"]},
    {"key": "perpetual_term", "label": "Perpetual / indefinite term", "markers": ["perpetual", "indefinite", "in perpetuity"]},
    {"key": "no_remedies", "label": "No injunctive relief", "markers": ["no injunctive", "waives injunctive", "money damages are adequate"]},
]

_CLAUSE_TYPES = sorted(_CLAUSE_RULES)


# --- Helpers ----------------------------------------------------------------


def _match(text: str, terms: set[str]) -> list[str]:
    """Return the subset of `terms` present as substrings in `text`."""
    lowered = text.lower()
    return sorted(t for t in terms if t.lower() in lowered)


# --- Tools ------------------------------------------------------------------


@mcp.tool()
def clause_risk_check(clause_type: str, clause_text: str) -> dict:
    """Score a single contract clause for risk.

    Args:
        clause_type: One of "liability", "indemnification", "ip",
            "confidentiality", or "termination".
        clause_text: The clause text to analyze.

    Returns a dict with the risk band (GREEN/YELLOW/RED), the terms that
    triggered it, and a one-line rationale.
    """
    key = clause_type.strip().lower()
    if key not in _CLAUSE_RULES:
        valid = ", ".join(_CLAUSE_TYPES)
        raise ValueError(f"Unknown clause_type '{clause_type}'. Must be one of: {valid}")

    red = _match(clause_text, _CLAUSE_RULES[key]["red"])
    yellow = _match(clause_text, _CLAUSE_RULES[key]["yellow"])

    if red:
        band = "RED"
        rationale = f"{len(red)} red flag(s) in a {key} clause."
    elif yellow:
        band = "YELLOW"
        rationale = f"{len(yellow)} term(s) worth attorney review."
    else:
        band = "GREEN"
        rationale = "No flagged terms."

    return {
        "clause_type": key,
        "risk": band,
        "red_flags": red,
        "yellow_flags": yellow,
        "rationale": rationale,
    }


@mcp.tool()
def nda_triage(nda_text: str) -> dict:
    """Screen a non-disclosure agreement for standard carve-outs and red flags.

    Args:
        nda_text: The full NDA text (or the body of its substantive clauses).

    Returns a pass/needs-review verdict plus a checklist of which standard
    protections are present and which red flags were detected.
    """
    present = []
    missing = []
    for item in _NDA_CARVEOUTS:
        markers = item["markers"]
        if any(m.lower() in nda_text.lower() for m in markers):
            present.append(item["label"])
        else:
            missing.append(item["label"])

    red_flags = []
    for item in _NDA_RED_FLAGS:
        if any(m.lower() in nda_text.lower() for m in item["markers"]):
            red_flags.append(item["label"])

    needs_review = bool(missing) or bool(red_flags)
    verdict = "needs-review" if needs_review else "pass"

    return {
        "verdict": verdict,
        "present": present,
        "missing": missing,
        "red_flags": red_flags,
    }


@mcp.tool()
def risk_matrix(severity: int, likelihood: int) -> dict:
    """Map a risk to a severity x likelihood matrix band.

    Args:
        severity: Impact if the risk materializes, 1 (negligible) to 5 (severe).
        likelihood: Chance of occurrence, 1 (rare) to 5 (almost certain).

    Returns the band and a recommended action. Score is severity * likelihood
    (1-25), matching the legal-os "programmatic scoring" convention.
    """
    if not (1 <= severity <= 5):
        raise ValueError("severity must be between 1 and 5")
    if not (1 <= likelihood <= 5):
        raise ValueError("likelihood must be between 1 and 5")

    score = severity * likelihood

    if score >= 15:
        band, action = "CRITICAL", "Escalate immediately. Do not proceed without sign-off."
    elif score >= 8:
        band, action = "HIGH", "Attorney review required before commitment."
    elif score >= 4:
        band, action = "MEDIUM", "Log and monitor. Approve with noted conditions."
    else:
        band, action = "LOW", "Accept and document."

    return {
        "severity": severity,
        "likelihood": likelihood,
        "score": score,
        "band": band,
        "action": action,
    }


# --- Descrybe cite-check (proxied) ------------------------------------------

# The full cite-check logic lives in the legal-os backend, which holds the
# per-user Descrybe OAuth connection. This tool proxies to that deployed
# endpoint (running in DEMO_MODE, so no auth header is needed) and returns the
# structured report. Set LEGAL_OS_API_URL to point at a different backend.
_LEGAL_OS_API = os.environ.get("LEGAL_OS_API_URL", "https://legal-os-api.fly.dev").rstrip("/")


@mcp.tool()
async def cite_check(text: str, name: str | None = None) -> dict:
    """Validate a legal brief against the Descrybe Legal Engine.

    Extracts every citation, resolves it to a case, checks good-law treatment
    (good / caution / bad / unknown), and verifies quoted passages word-for-word.
    Returns a findings report plus an annotated copy of the brief.

    Args:
        text: The full brief or filing text to check.
        name: Optional document name (used for the annotated copy's filename).

    Returns a dict with the findings report, the annotated brief, and the
    step-by-step log of what was checked.
    """
    if not text.strip():
        raise ValueError("text is required")

    url = f"{_LEGAL_OS_API}/api/legal-research/cite-check"
    report: dict | None = None
    brief: dict | None = None
    logs: list[str] = []

    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json={"text": text, "name": name}) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"cite-check backend returned {resp.status_code}: {body.decode()[:300]}")
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                if kind == "log":
                    logs.append(event.get("message", ""))
                elif kind == "report":
                    report = event.get("report")
                elif kind == "brief":
                    brief = {"name": event.get("name"), "content": event.get("content")}
                elif kind == "error":
                    raise RuntimeError(f"cite-check error: {event.get('message')}")

    if report is None:
        raise RuntimeError("cite-check completed without a report")

    return {
        "report": report,
        "annotated_brief": brief,
        "log": logs,
    }


# --- Resource ---------------------------------------------------------------


@mcp.resource("legal://playbook")
def playbook() -> str:
    """The default review playbook, served as a static resource."""
    return """\
# Legal Review Playbook (default)

## Liability
- Standard: mutual cap at 12 months of fees paid/payable.
- Escalate: uncapped liability, consequential damages.

## Indemnification
- Standard: mutual indemnification for IP and data breach.
- Escalate: unilateral indemnification, uncapped indemnification.

## IP Ownership
- Standard: each party retains pre-existing IP.
- Escalate: work-for-hire, assignment of all IP.

## Confidentiality
- Standard: DPA required for any personal data processing.
- Escalate: no DPA, cross-border transfer without safeguards.
"""


# --- Entrypoint -------------------------------------------------------------

if __name__ == "__main__":
    # Streamable HTTP is the modern, deployable transport. Build the Starlette
    # app and serve it with uvicorn so we control host/port (the high-level
    # `mcp.run()` pins its own defaults, which Fly.io needs to override).
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
