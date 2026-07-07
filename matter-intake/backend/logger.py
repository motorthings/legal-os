"""
Structured JSONL logging for the Matter Intake Evaluator.

Every log line is a JSON object with required fields:
  - timestamp (ISO 8601)
  - event_type (string)
  - context (object or null)
  - data (object or null)
  - duration_ms (int or null)
  - schema_version (int, starts at 1)

Usage:
    from logger import get_logger
    log = get_logger("evaluator")
    log.info("claude_call", extra={"event_type": "claude_call", "context": {...}, "data": {...}, "duration_ms": 1234})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSONL."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "event_type": getattr(record, "event_type", record.levelname.lower()),
            "context": getattr(record, "context", None),
            "data": getattr(record, "data", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "schema_version": 1,
        }
        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with StructuredJSONFormatter, outputs to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    # Remove any existing handlers to avoid duplicates
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger with the given name."""
    return logging.getLogger(name)
