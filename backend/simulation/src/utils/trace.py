"""
Trace — comprehensive event log for auditing the entire simulation.

One JSONL file captures every event: environmental inputs, agent decisions,
firm actions, agent state shifts, and political events. Self-contained audit trail.
"""

import json
from pathlib import Path


class TraceLog:
    """In-memory event buffer. Appends only. Exports to JSONL."""

    def __init__(self):
        self.events: list[dict] = []

    def _emit(self, sprint: int, event: str, data: dict):
        self.events.append({
            "sprint": sprint,
            "event": event,
            **data,
        })

    # --- Environmental ---
    def env_event(self, sprint: int, event_name: str, params: dict):
        self._emit(sprint, "env_event", {
            "event_name": event_name,
            "parameters": {k: v for k, v in params.items()
                          if not k.startswith("active_event")},
        })

    # --- Agent decisions ---
    def agent_decision(self, sprint: int, d):
        """d is an AgentDecision object or dict."""
        if hasattr(d, 'to_dict'):
            d = d.to_dict()
        self._emit(sprint, "agent_decision", {
            "matter_id": d.get("matter_id", "?"),
            "step": d.get("step_name", "?"),
            "agent": d.get("agent_name", d.get("agent_role_id", "?")),
            "decision": d.get("decision", "?"),
            "used_ai": d.get("used_ai", False),
            "ai_correct": d.get("ai_was_correct"),
            "exception": d.get("exception_raised", False),
            "translation": d.get("translation_incident", False),
            "reasoning": (d.get("reasoning", "") or "")[:150],
            "concerns": d.get("concerns", ""),
            "emotion": d.get("emotion_note", ""),
        })

    # --- LLM calls (full input/output — the auditability core) ---
    def llm_call(self, sprint: int, d, provider: str = "", model: str = ""):
        """Emit one event per LLM interaction with the FULL prompt and response.

        This is what "everything sent to the LLM and back" means: the exact
        messages the model received and the exact raw text it returned. Deterministic
        mock chatter is captured identically (provider='mock'), so a run is auditable
        regardless of whether it used a real model.
        """
        if hasattr(d, 'to_dict'):
            d = d.to_dict()
        raw_prompt = d.get("raw_prompt", "") or ""
        raw_response = d.get("raw_response", "") or ""
        # Skip the deterministic AI-pipeline auto-decisions — they never hit an LLM.
        if not raw_prompt and not raw_response:
            return
        self._emit(sprint, "llm_call", {
            "matter_id": d.get("matter_id", "?"),
            "step": d.get("step_name", "?"),
            "agent": d.get("agent_name", d.get("agent_role_id", "?")),
            "provider": provider,
            "model": model,
            "status": "error" if d.get("exception_raised") else "ok",
            "prompt": raw_prompt,
            "response": raw_response,
        })

    # --- Firm / transformation actions ---
    def firm_action(self, sprint: int, action: str, detail: dict):
        self._emit(sprint, "firm_action", {
            "action": action,
            **detail,
        })

    # --- Agent state changes ---
    def agent_trust_shift(self, sprint: int, role_id: str, old_trust: float, new_trust: float, reason: str = ""):
        if abs(new_trust - old_trust) < 0.01:
            return  # skip negligible shifts
        self._emit(sprint, "trust_shift", {
            "role": role_id,
            "from": round(old_trust, 3),
            "to": round(new_trust, 3),
            "delta": round(new_trust - old_trust, 3),
            "reason": reason,
        })

    def agent_departed(self, sprint: int, role_id: str, reason: str):
        self._emit(sprint, "agent_departed", {
            "role": role_id,
            "reason": reason,
        })

    # --- Political events ---
    def political_event(self, sprint: int, event_type: str, detail: str):
        self._emit(sprint, "political_event", {
            "type": event_type,
            "detail": detail[:200],
        })

    # --- Metric snapshot (sprint-end summary) ---
    def metric_snapshot(self, sprint: int, metrics: dict):
        # Only emit key metrics
        key = ["translation_debt_index", "exception_rate", "partner_ai_trust",
               "redline_rework_rate", "handoff_failure_rate", "matter_profit_margin"]
        compact = {k: round(v, 2) for k, v in metrics.items() if k in key}
        self._emit(sprint, "metric_snapshot", compact)

    # --- Export ---
    def export(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for event in self.events:
                f.write(json.dumps(event, default=str) + "\n")
        return path

    def summary(self) -> str:
        from collections import Counter
        counts = Counter(e["event"] for e in self.events)
        lines = [f"Trace: {len(self.events)} events"]
        for event_type, count in counts.most_common():
            lines.append(f"  {event_type}: {count}")
        return "\n".join(lines)
