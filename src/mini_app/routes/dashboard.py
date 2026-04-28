from __future__ import annotations

from typing import Any

from mini_app.auth import TelegramMiniAppUser
from mini_app.responses import write_async_json


def handle_dashboard_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    user: TelegramMiniAppUser,
) -> bool:
    if method == "GET" and path == "/api/dashboard":
        write_async_json(handler, handler.gateway.get_dashboard(user=user))
        return True
    if method == "GET" and path == "/api/dashboard/operator":
        write_async_json(handler, handler.gateway.get_operator_dashboard(user=user))
        return True
    return False
