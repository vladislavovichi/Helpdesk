from __future__ import annotations

from typing import Any

from mini_app.auth import TelegramMiniAppUser
from mini_app.responses import write_async_json


def handle_queue_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    user: TelegramMiniAppUser,
) -> bool:
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
    return False
