from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from aiogram.types import CallbackQuery, Chat, Message, User

from application.services.authorization import AuthorizationService, AuthorizationServiceFactory
from bot.middlewares.authorization import AuthorizationMiddleware
from bot.presentation import build_main_menu
from domain.enums.roles import UserRole


class FakeOperatorRepository:
    def __init__(self, active_operator_ids: set[int]) -> None:
        self.active_operator_ids = active_operator_ids

    async def exists_active_by_telegram_user_id(self, *, telegram_user_id: int) -> bool:
        return telegram_user_id in self.active_operator_ids


def build_authorization_service_factory(
    *,
    active_operator_ids: set[int],
    super_admin_telegram_user_id: int = 42,
) -> AuthorizationServiceFactory:
    service = AuthorizationService(
        operator_repository=FakeOperatorRepository(active_operator_ids=active_operator_ids),
        super_admin_telegram_user_id=super_admin_telegram_user_id,
    )

    @asynccontextmanager
    async def provide() -> AsyncIterator[AuthorizationService]:
        yield service

    return provide


def build_message(*, user_id: int, text: str) -> Message:
    message = Message.model_construct(
        message_id=1,
        date=None,
        chat=Chat.model_construct(id=user_id, type="private"),
        from_user=User.model_construct(id=user_id, is_bot=False, first_name="Test"),
        text=text,
    )
    object.__setattr__(message, "answer", AsyncMock())
    return message


def build_callback(*, user_id: int, data: str) -> CallbackQuery:
    callback = CallbackQuery.model_construct(
        id="callback-id",
        from_user=User.model_construct(id=user_id, is_bot=False, first_name="Test"),
        chat_instance="chat-instance",
        data=data,
        message=build_message(user_id=user_id, text="stub"),
    )
    object.__setattr__(callback, "answer", AsyncMock())
    return callback


async def test_authorization_middleware_denies_regular_user_operator_command() -> None:
    middleware = AuthorizationMiddleware()
    handler = AsyncMock()
    message = build_message(user_id=2002, text="/queue")

    result = await middleware(
        handler,
        message,
        {
            "authorization_service_factory": build_authorization_service_factory(
                active_operator_ids=set()
            ),
            "event_user_id": 2002,
            "state": None,
        },
    )

    assert result is None
    handler.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Это действие доступно только операторам и супер администратору.",
        reply_markup=build_main_menu(UserRole.USER),
    )


async def test_authorization_middleware_denies_regular_user_operator_callback() -> None:
    middleware = AuthorizationMiddleware()
    handler = AsyncMock()
    callback = build_callback(user_id=2002, data="operator:take:ticket-public-id")

    result = await middleware(
        handler,
        callback,
        {
            "authorization_service_factory": build_authorization_service_factory(
                active_operator_ids=set()
            ),
            "event_user_id": 2002,
            "state": None,
        },
    )

    assert result is None
    handler.assert_not_awaited()
    callback.answer.assert_awaited_once_with(
        "Это действие доступно только операторам и супер администратору.",
        show_alert=True,
    )


async def test_authorization_middleware_allows_operator_command_and_sets_role_context() -> None:
    middleware = AuthorizationMiddleware()
    handler = AsyncMock(return_value="handled")
    message = build_message(user_id=1001, text="/queue")
    data = {
        "authorization_service_factory": build_authorization_service_factory(
            active_operator_ids={1001}
        ),
        "event_user_id": 1001,
        "state": None,
    }

    result = await middleware(handler, message, data)

    assert result == "handled"
    handler.assert_awaited_once()
    message.answer.assert_not_awaited()
    assert data["event_user_role"] == UserRole.OPERATOR
    assert data["event_is_super_admin"] is False


async def test_authorization_middleware_marks_super_admin_context() -> None:
    middleware = AuthorizationMiddleware()
    handler = AsyncMock(return_value="handled")
    message = build_message(user_id=42, text="/operators")
    data = {
        "authorization_service_factory": build_authorization_service_factory(
            active_operator_ids={1001},
            super_admin_telegram_user_id=42,
        ),
        "event_user_id": 42,
        "state": None,
    }

    result = await middleware(handler, message, data)

    assert result == "handled"
    handler.assert_awaited_once()
    assert data["event_user_role"] == UserRole.SUPER_ADMIN
    assert data["event_is_super_admin"] is True
