"""In-process event bus for live SSE progress.

`publish` is called from sync contexts (the orchestrator's per-sprint on_progress hook),
so it must be non-blocking: it puts the event on each live subscriber's queue and schedules
a fire-and-forget DB persist (the DB is the replay source of truth for late/resumed
subscribers). Each event carries a per-run monotonic `seq`.

Crash-safety note: the resume checkpoint is `runs.seeds_completed` (awaited in the runner),
not these events — so a lost sprint event on crash is fine; resume re-runs from the seed.
"""
import asyncio
import json
from typing import Awaitable, Callable


class EventBus:
    def __init__(self, persist: Callable[[dict], Awaitable[None]] | None = None) -> None:
        # persist(event_dict) -> await; in production this is db.append_event.
        self._persist = persist or (lambda ev: _noop(ev))
        self._queues: dict[str, set[asyncio.Queue]] = {}
        self._seq: dict[str, int] = {}

    def publish(self, run_id: str, kind: str, payload: dict) -> None:
        seq = self._seq.get(run_id, 0) + 1
        self._seq[run_id] = seq
        event = {"run_id": run_id, "seq": seq, "kind": kind, "payload": payload}
        for q in list(self._queues.get(run_id, ())):
            try:
                q.put_nowait(event)
            except Exception:
                pass  # subscriber gone / full
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist(event))
        except Exception:
            pass  # no running loop (shouldn't happen inside a run) or persist failed

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(run_id, set()).add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        self._queues.get(run_id, set()).discard(q)


async def _noop(_ev: dict) -> None:
    return None


# --- SSE formatting ---

def sse(event: dict) -> str:
    """Format one event dict as an SSE frame: `data: <json>\n\n`."""
    return f"data: {json.dumps(event, default=str)}\n\n"


def sse_comment(text: str) -> str:
    return f": {text}\n\n"
