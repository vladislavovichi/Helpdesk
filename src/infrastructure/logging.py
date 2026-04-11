from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from infrastructure.config.settings import AppConfig, LoggingConfig
from infrastructure.runtime_context import get_correlation_id

PLAIN_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__.keys())


class RuntimeContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, *, app_name: str, environment: str) -> None:
        super().__init__()
        self.app_name = app_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": self.app_name,
            "environment": self.environment,
            "correlation_id": getattr(record, "correlation_id", "-"),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        extra = {
            key: _normalize_log_value(value)
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS
            and key not in {"message", "asctime", "correlation_id"}
        }
        if extra:
            payload["context"] = extra

        return json.dumps(payload, ensure_ascii=True)


def configure_logging(config: LoggingConfig, *, app: AppConfig) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RuntimeContextFilter())
    handler.setFormatter(
        JsonFormatter(app_name=app.name, environment=app.environment)
        if config.structured
        else logging.Formatter(PLAIN_LOG_FORMAT)
    )
    logging.basicConfig(
        level=getattr(logging, config.level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )


def _normalize_log_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_normalize_log_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_log_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_log_value(item) for key, item in value.items()}
    return str(value)
