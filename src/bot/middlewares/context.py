from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from infrastructure.runtime_context import (
    bind_correlation_id,
    ensure_correlation_id,
    reset_correlation_id,
)


class UpdateContextMiddleware(BaseMiddleware):
    """Attach the current chat and user ids to handler context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            data["event_chat_id"] = event.chat.id
            data["event_user_id"] = event.from_user.id if event.from_user is not None else None
            correlation_id = ensure_correlation_id(
                f"telegram-message:{event.chat.id}:{event.message_id}"
            )
        elif isinstance(event, CallbackQuery):
            data["event_chat_id"] = event.message.chat.id if event.message is not None else None
            data["event_user_id"] = event.from_user.id
            correlation_id = ensure_correlation_id(
                f"telegram-callback:{event.from_user.id}:{event.id}"
            )
        else:
            correlation_id = ensure_correlation_id(event.__class__.__name__)

        token = bind_correlation_id(correlation_id)
        data["correlation_id"] = correlation_id
        try:
            return await handler(event, data)
        finally:
            reset_correlation_id(token)
