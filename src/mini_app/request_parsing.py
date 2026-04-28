from __future__ import annotations

import json
from typing import Any
from urllib.parse import ParseResult, parse_qs

from application.errors import ValidationAppError
from application.services.stats import AnalyticsWindow


def parse_analytics_window(parsed: ParseResult) -> AnalyticsWindow:
    query = parse_qs(parsed.query)
    return AnalyticsWindow(query.get("window", ["7d"])[0])


def read_json_body(handler: Any) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    payload = handler.rfile.read(content_length) if content_length > 0 else b"{}"
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationAppError("Не удалось разобрать JSON payload.") from exc
    if not isinstance(decoded, dict):
        raise ValidationAppError("JSON payload должен быть объектом.")
    return decoded


def require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValidationAppError(f"Поле {key} должно быть строкой.")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValidationAppError(f"Поле {key} не должно быть пустым.")
    return normalized


def optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationAppError(f"Поле {key} должно быть строкой.")
    normalized = value.strip()
    return normalized or None


def require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValidationAppError(f"Поле {key} должно быть числом.")
    return value
