from __future__ import annotations

from http import HTTPStatus
from typing import Any

from domain.enums.roles import UserRole
from mini_app.launch import ResolvedMiniAppLaunch


def handle_session_route(
    handler: Any,
    *,
    method: str,
    path: str,
    launch: ResolvedMiniAppLaunch,
    session: dict[str, Any],
) -> bool:
    if method != "GET" or path != "/api/session":
        return False
    handler._write_json(
        HTTPStatus.OK,
        {
            **session,
            "launch": {
                "source": launch.source,
                "client_source": launch.client_source,
            },
        },
    )
    return True


def require_operator_session(
    handler: Any,
    *,
    path: str,
    session: dict[str, Any],
) -> bool:
    if session["access"]["role"] != UserRole.USER.value:
        return True
    handler._write_json(
        HTTPStatus.FORBIDDEN,
        {
            "error": "Рабочее место доступно только операторам и суперадминистраторам.",
            "code": "forbidden" if _is_ai_path(path) else "access_denied",
        },
    )
    return False


def _is_ai_path(path: str) -> bool:
    from mini_app.routes.ai import is_ai_route

    return is_ai_route(path)
