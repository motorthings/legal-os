"""
State management for the simulation.

Tracks and persists a single firm:
- Company state
- Agent states
- Matter states (active, completed)
- Metric history
- Environmental history
- Decision logs

The state is the single source of truth for the simulation.
Everything that happens is recorded here.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.company import CompanyState
from ..models.matters import Matter
from ..models.events import WorldEngine
from ..models.metrics import MetricSnapshot
from .agents import AgentStates, AgentDecision
from .dynamics import AttritionState, TrustState


@dataclass
class SprintLog:
    """Complete record of one sprint for the firm."""
    sprint: int
    decisions: list[AgentDecision] = field(default_factory=list)
    matters_completed: list[Matter] = field(default_factory=list)
    matters_active: list[Matter] = field(default_factory=list)
    metric_snapshots: list[MetricSnapshot] = field(default_factory=list)
    agent_state_summaries: dict[str, str] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class SimulationRun:
    """
    Complete state for one simulation run: a single, parameterized firm.
    """

    run_id: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sprints_total: int = 16

    # The firm
    company: CompanyState = field(default_factory=CompanyState)

    # World engine (generates the environment)
    world: WorldEngine = field(default_factory=lambda: WorldEngine(seed=42))

    # Agent / attrition / trust state (single firm)
    agent_states: AgentStates = field(default_factory=AgentStates)
    attrition: AttritionState = field(default_factory=AttritionState)
    trust: TrustState = field(default_factory=TrustState)

    # Current sprint
    current_sprint: int = 0

    # Full history
    sprint_logs: list[SprintLog] = field(default_factory=list)

    # Environmental history
    env_history: list[dict] = field(default_factory=list)

    # Status
    completed: bool = False
    error: Optional[str] = None

    def initialize(self):
        """Initialize the simulation state."""
        self.company.initialize_agent_states()
        self.world.initialize()

        for role_id, role in self.company.roles.items():
            self.agent_states.get_or_create(role_id, role)
            self.attrition.active_agents.add(role_id)

        self.trust.initialize_from_company(self.company)

    def advance(self):
        """Advance to the next sprint."""
        self.current_sprint += 1

    def is_complete(self) -> bool:
        return self.current_sprint >= self.sprints_total

    def summary(self) -> str:
        lines = [
            f"=== Simulation Run: {self.run_id} ===",
            f"Sprint: {self.current_sprint}/{self.sprints_total}",
            f"",
            f"Firm — {self.company.name}:",
            f"  Active agents: {len(self.agent_states.all_active())}",
            f"  Decisions logged: {sum(len(log.decisions) for log in self.sprint_logs)}",
            f"  Matters completed: {sum(len(log.matters_completed) for log in self.sprint_logs)}",
            f"",
            f"Environment: {len(self.env_history)} snapshots recorded",
        ]
        return "\n".join(lines)


class StateSerializer:
    """Serialize and deserialize simulation state for persistence and analysis."""

    @staticmethod
    def to_dict(run: SimulationRun) -> dict:
        """Convert a simulation run to a serializable dict."""
        return {
            "run_id": run.run_id,
            "started_at": run.started_at,
            "sprints_total": run.sprints_total,
            "current_sprint": run.current_sprint,
            "completed": run.completed,
            "error": run.error,
            "env_history": run.env_history,
            "agent_states": {
                rid: state.summary()
                for rid, state in run.agent_states.states.items()
            },
            "trust": run.trust.confidence,
        }

    @staticmethod
    def save(run: SimulationRun, path: Path):
        """Save simulation state to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = StateSerializer.to_dict(run)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def export_metrics_csv(run: SimulationRun, path: Path):
        """Export all metric history as CSV for analysis."""
        import csv
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric_id", "sprint", "value", "confidence"])

            for metric_id, history in run.company.metric_history.items():
                for snap in history.values:
                    writer.writerow([metric_id, snap.sprint, snap.value, snap.confidence])

    @staticmethod
    def export_decisions_jsonl(run: SimulationRun, path: Path):
        """Export all agent decisions as JSONL for analysis."""
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            for log in run.sprint_logs:
                for decision in log.decisions:
                    f.write(json.dumps({
                        **decision.to_dict(),
                        "sprint": log.sprint,
                    }) + "\n")
