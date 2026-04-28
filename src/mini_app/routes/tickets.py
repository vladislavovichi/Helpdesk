from __future__ import annotations

import re
from typing import Any
from urllib.parse import ParseResult
from uuid import UUID

from application.contracts.actors import OperatorIdentity
from mini_app.auth import TelegramMiniAppUser
from mini_app.request_parsing import (
    optional_string,
    read_json_body,
    require_int,
    require_string,
)
from mini_app.responses import write_async_json
from mini_app.routes.ai import TICKET_AI_REPLY_DRAFT_ROUTE, TICKET_AI_SUMMARY_ROUTE
from mini_app.routes.exports import handle_ticket_export

TICKET_ROUTE = re.compile(r"^/api/tickets/([0-9a-fA-F-]{36})$")
TICKET_ACTION_ROUTE = re.compile(
    r"^/api/tickets/([0-9a-fA-F-]{36})/(take|close|escalate|assign|notes)$"
)
TICKET_MACRO_ROUTE = re.compile(r"^/api/tickets/([0-9a-fA-F-]{36})/macros/(\d+)$")
TICKET_EXPORT_ROUTE = re.compile(r"^/api/tickets/([0-9a-fA-F-]{36})/export$")


def handle_ticket_routes(
    handler: Any,
    *,
    method: str,
    path: str,
    parsed: ParseResult,
    user: TelegramMiniAppUser,
) -> bool:
    ticket_match = TICKET_ROUTE.fullmatch(path)
    if method == "GET" and ticket_match is not None:
        write_async_json(
            handler,
            handler.gateway.get_ticket_workspace(
                user=user,
                ticket_public_id=UUID(ticket_match.group(1)),
            ),
        )
        return True

    action_match = TICKET_ACTION_ROUTE.fullmatch(path)
    if method == "POST" and action_match is not None:
        return handle_ticket_action(
            handler,
            user=user,
            ticket_public_id=UUID(action_match.group(1)),
            action=action_match.group(2),
        )

    ai_summary_match = TICKET_AI_SUMMARY_ROUTE.fullmatch(path)
    if method == "POST" and ai_summary_match is not None:
        write_async_json(
            handler,
            handler.gateway.refresh_ticket_ai_summary(
                user=user,
                ticket_public_id=UUID(ai_summary_match.group(1)),
            ),
        )
        return True

    ai_reply_draft_match = TICKET_AI_REPLY_DRAFT_ROUTE.fullmatch(path)
    if method == "POST" and ai_reply_draft_match is not None:
        write_async_json(
            handler,
            handler.gateway.generate_ticket_reply_draft(
                user=user,
                ticket_public_id=UUID(ai_reply_draft_match.group(1)),
            ),
        )
        return True

    macro_match = TICKET_MACRO_ROUTE.fullmatch(path)
    if method == "POST" and macro_match is not None:
        write_async_json(
            handler,
            handler.gateway.apply_macro(
                user=user,
                ticket_public_id=UUID(macro_match.group(1)),
                macro_id=int(macro_match.group(2)),
            ),
        )
        return True

    export_match = TICKET_EXPORT_ROUTE.fullmatch(path)
    if method == "GET" and export_match is not None:
        handle_ticket_export(
            handler,
            user=user,
            ticket_public_id=UUID(export_match.group(1)),
            parsed=parsed,
        )
        return True

    return False


def handle_ticket_action(
    handler: Any,
    *,
    user: TelegramMiniAppUser,
    ticket_public_id: UUID,
    action: str,
) -> bool:
    if action == "take":
        write_async_json(
            handler,
            handler.gateway.take_ticket(user=user, ticket_public_id=ticket_public_id),
        )
        return True
    if action == "close":
        write_async_json(
            handler,
            handler.gateway.close_ticket(user=user, ticket_public_id=ticket_public_id),
        )
        return True
    if action == "escalate":
        write_async_json(
            handler,
            handler.gateway.escalate_ticket(user=user, ticket_public_id=ticket_public_id),
        )
        return True

    payload = read_json_body(handler)
    if action == "assign":
        operator = OperatorIdentity(
            telegram_user_id=require_int(payload, "telegram_user_id"),
            display_name=require_string(payload, "display_name"),
            username=optional_string(payload, "username"),
        )
        write_async_json(
            handler,
            handler.gateway.assign_ticket(
                user=user,
                ticket_public_id=ticket_public_id,
                operator_identity=operator,
            ),
        )
        return True
    if action == "notes":
        write_async_json(
            handler,
            handler.gateway.add_note(
                user=user,
                ticket_public_id=ticket_public_id,
                text=require_string(payload, "text"),
            ),
        )
        return True
    return False
