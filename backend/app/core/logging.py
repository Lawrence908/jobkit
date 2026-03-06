"""Structured JSON logging with redaction of sensitive fields."""
import json
import logging
import re
from typing import Any

# Keys (and key substrings) whose values should be redacted in log output
REDACT_KEYS = frozenset({"resume", "description", "cover_letter", "job_text", "raw_text", "body"})


def _should_redact(key: str) -> bool:
    key_lower = key.lower()
    return any(r in key_lower for r in REDACT_KEYS)


def _redact_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: "[REDACTED]" if _should_redact(k) else _redact_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_dict(x) for x in obj]
    return obj


class RedactingFormatter(logging.Formatter):
    """JSON formatter that redacts sensitive field values."""

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)
        # Redact any extra attributes that look sensitive
        for key, value in record.__dict__.items():
            if key not in ("name", "msg", "args", "created", "filename", "funcName", "levelname", "levelno", "lineno", "module", "msecs", "pathname", "process", "processName", "relativeCreated", "stack_info", "exc_info", "exc_text", "thread", "threadName", "message", "taskName"):
                log_dict[key] = _redact_dict(value) if _should_redact(key) else value
        return json.dumps(log_dict, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with redacting JSON formatter."""
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter())
    root.addHandler(handler)
