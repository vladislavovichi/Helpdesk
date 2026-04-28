from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult

from mini_app.auth import TelegramMiniAppUser
from mini_app.request_parsing import parse_analytics_window
from mini_app.responses import write_async_json
from mini_app.routes.exports import handle_analytics_export


def handle_analytics_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    parsed: ParseResult,
    user: TelegramMiniAppUser,
) -> bool:
    if method == "GET" and path == "/api/analytics":
        window = parse_analytics_window(parsed)
        write_async_json(handler, handler.gateway.get_analytics(user=user, window=window))
        return True
    if method == "GET" and path == "/api/analytics/export":
        handle_analytics_export(handler, user=user, parsed=parsed)
        return True
    return False
