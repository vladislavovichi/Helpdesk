from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult

from mini_app.auth import TelegramMiniAppUser
from mini_app.request_parsing import parse_analytics_window
from mini_app.responses import write_async_json
from mini_app.routes.exports import handle_analytics_export


def handle_dashboard_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    parsed: ParseResult,
    user: TelegramMiniAppUser,
) -> bool:
    if method == "GET" and path == "/api/dashboard":
        write_async_json(handler, handler.gateway.get_dashboard(user=user))
        return True
    if method == "GET" and path == "/api/dashboard/operator":
        write_async_json(handler, handler.gateway.get_operator_dashboard(user=user))
        return True
    if method == "GET" and path == "/api/queue":
        write_async_json(handler, handler.gateway.list_queue(user=user))
        return True
    if method == "POST" and path == "/api/queue/take-next":
        write_async_json(handler, handler.gateway.take_next_ticket(user=user))
        return True
    if method == "GET" and path == "/api/my-tickets":
        write_async_json(handler, handler.gateway.list_my_tickets(user=user))
        return True
    if method == "GET" and path == "/api/archive":
        write_async_json(handler, handler.gateway.list_archive(user=user))
        return True
    if method == "GET" and path == "/api/analytics":
        window = parse_analytics_window(parsed)
        write_async_json(handler, handler.gateway.get_analytics(user=user, window=window))
        return True
    if method == "GET" and path == "/api/analytics/export":
        handle_analytics_export(handler, user=user, parsed=parsed)
        return True
    return False
