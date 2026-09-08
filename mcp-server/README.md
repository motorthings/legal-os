# legal-os MCP server

A self-contained MCP (Model Context Protocol) server exposing legal productivity
tools. Built as a learning exercise — deterministic tools, no LLM, no database,
no external API. The point is the mechanics: how a typed tool schema becomes a
callable interface, and how the Streamable HTTP transport deploys.

## What it exposes

| Tool | Input | Returns |
|------|-------|---------|
| `clause_risk_check` | `clause_type`, `clause_text` | risk band (GREEN/YELLOW/RED), flagged terms, rationale |
| `nda_triage` | `nda_text` | pass/needs-review verdict, present/missing carve-outs, red flags |
| `risk_matrix` | `severity`, `likelihood` (1-5 each) | band + recommended action from a 1-25 score |

Plus one static resource, `legal://playbook`.

## Run locally

```bash
cd mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# interactive inspector (lists tools, lets you call them)
mcp dev server.py

# or plain HTTP transport
python server.py            # Streamable HTTP on :8000
```

## Connect from Claude Code

```bash
# local
claude mcp add --transport http legal-os http://localhost:8000/mcp

# deployed
claude mcp add --transport http legal-os https://legalos-mcp.fly.dev/mcp
```

## Deploy to Fly.io

```bash
cd mcp-server
fly launch --no-deploy       # first time, creates the app
fly deploy
```

The server reads `PORT` from the environment (Fly sets 8080; local defaults to
8000). The MCP endpoint is at `/mcp`.

## How it maps to the real legal-os

The backend's functions (`backend/app/api/routes/`) are the production versions
of these tools. This server shows the same shape — a typed function whose
docstring becomes its description and whose signature becomes its schema — but
with the logic inlined so there's nothing to provision to run it. Swapping a
tool body from `_match(...)` to `requests.post(f"{BACKEND}/...")` is the whole
migration to "MCP as front door to the real API."
