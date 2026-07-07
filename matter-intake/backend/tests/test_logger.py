"""Tests for structured JSONL logging."""

import json
import logging

from logger import StructuredJSONFormatter, get_logger, setup_logging


class TestStructuredJSONFormatter:
    """Verify the JSONL formatter produces valid, complete log records."""

    def test_output_is_valid_json(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_required_fields_present(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        record.event_type = "test_event"
        record.context = {"key": "value"}
        record.data = {"result": 42}
        record.duration_ms = 1234

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert parsed["event_type"] == "test_event"
        assert parsed["context"] == {"key": "value"}
        assert parsed["data"] == {"result": 42}
        assert parsed["duration_ms"] == 1234
        assert parsed["schema_version"] == 1

    def test_missing_extra_fields_default_to_none(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["context"] is None
        assert parsed["data"] is None
        assert parsed["duration_ms"] is None
        assert parsed["event_type"] == "info"  # falls back to levelname

    def test_timestamp_is_iso8601(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        # Should be ISO 8601 with timezone
        assert "T" in parsed["timestamp"]
        assert "+" in parsed["timestamp"] or "Z" in parsed["timestamp"]


class TestSetupAndGetLogger:
    """Verify setup_logging and get_logger work correctly."""

    def test_setup_logging_adds_handler(self):
        setup_logging("INFO")
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, StructuredJSONFormatter)

    def test_get_logger_returns_logger(self):
        log = get_logger("test_module")
        assert isinstance(log, logging.Logger)
        assert log.name == "test_module"
