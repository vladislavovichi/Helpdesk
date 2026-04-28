from __future__ import annotations

from typing import Any
from urllib.parse import ParseResult

from domain.enums.roles import UserRole
from mini_app.auth import TelegramMiniAppUser
from mini_app.request_parsing import read_json_body
from mini_app.responses import write_async_json


def handle_admin_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    parsed: ParseResult,
    user: TelegramMiniAppUser,
    session: dict[str, Any],
) -> bool:
    del parsed
    if method == "GET" and path == "/api/admin/operators":
        require_admin(session)
        write_async_json(handler, handler.gateway.list_operators(user=user))
        return True
    if method == "GET" and path == "/api/admin/ai-settings":
        require_admin(session)
        write_async_json(handler, handler.gateway.get_ai_settings(user=user))
        return True
    if method == "PUT" and path == "/api/admin/ai-settings":
        require_admin(session)
        write_async_json(
            handler,
            handler.gateway.update_ai_settings(
                user=user,
                payload=read_json_body(handler),
            ),
        )
        return True
    if method == "POST" and path == "/api/admin/invites":
        require_admin(session)
        write_async_json(handler, handler.gateway.create_operator_invite(user=user))
        return True
    return False


def require_admin(session: dict[str, Any]) -> None:
    if session["access"]["role"] != UserRole.SUPER_ADMIN.value:
        raise PermissionError("Доступно только суперадминистраторам.")
