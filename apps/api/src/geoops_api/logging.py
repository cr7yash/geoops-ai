"""Structured JSON logging helpers."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Serialize standard records and selected telemetry fields as JSON."""

    _telemetry_fields = (
        "request_id",
        "method",
        "path",
        "status_code",
        "latency_ms",
        "error_type",
        "trace_id",
        "session_id",
        "agent_run_id",
        "tool",
        "retrieval_count",
        "success",
        "approval_id",
        "ticket_id",
        "approval_status",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self._telemetry_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Configure the root logger once for local and container runtimes."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
