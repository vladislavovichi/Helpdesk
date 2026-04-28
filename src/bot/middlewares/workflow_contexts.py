from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.handlers.user.intake_context import ClientIntakeContext, TicketRuntimeContext


class WorkflowContextMiddleware(BaseMiddleware):
    """Build typed handler contexts from aiogram workflow_data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if _has_ticket_runtime_data(data):
            data.setdefault("ticket_runtime_context", _build_ticket_runtime_context(data))
        if "ticket_runtime_context" in data and _has_client_intake_data(data):
            data.setdefault("client_intake_context", _build_client_intake_context(data))
        return await handler(event, data)


def _build_ticket_runtime_context(data: dict[str, Any]) -> TicketRuntimeContext:
    existing = data.get("ticket_runtime_context")
    if isinstance(existing, TicketRuntimeContext):
        return existing
    return TicketRuntimeContext(
        helpdesk_backend_client_factory=data["helpdesk_backend_client_factory"],
        operator_active_ticket_store=data["operator_active_ticket_store"],
        ticket_live_session_store=data["ticket_live_session_store"],
        ticket_stream_publisher=data["ticket_stream_publisher"],
        logger=logging.getLogger("bot.handlers.user.workflow"),
    )


def _build_client_intake_context(data: dict[str, Any]) -> ClientIntakeContext:
    existing = data.get("client_intake_context")
    if isinstance(existing, ClientIntakeContext):
        return existing
    return ClientIntakeContext(
        ticket_runtime=data["ticket_runtime_context"],
        global_rate_limiter=data["global_rate_limiter"],
        chat_rate_limiter=data["chat_rate_limiter"],
    )


def _has_ticket_runtime_data(data: dict[str, Any]) -> bool:
    return all(
        key in data
        for key in (
            "helpdesk_backend_client_factory",
            "operator_active_ticket_store",
            "ticket_live_session_store",
            "ticket_stream_publisher",
        )
    )


def _has_client_intake_data(data: dict[str, Any]) -> bool:
    return "global_rate_limiter" in data and "chat_rate_limiter" in data
