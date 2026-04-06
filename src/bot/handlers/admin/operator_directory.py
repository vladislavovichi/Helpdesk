from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from application.services.helpdesk.service import HelpdeskServiceFactory
from bot.callbacks import AdminOperatorCallback
from bot.formatters.operator import format_operator_list_response
from bot.handlers.operator.common import respond_to_operator
from bot.keyboards.inline.admin import build_operator_management_markup
from bot.texts.buttons import OPERATORS_BUTTON_TEXT
from bot.texts.common import SERVICE_UNAVAILABLE_TEXT
from bot.texts.operator import OPERATORS_REFRESHED_TEXT
from infrastructure.config.settings import Settings
from infrastructure.redis.contracts import GlobalRateLimiter, OperatorPresenceHelper

router = Router(name="admin_operator_directory")


@router.message(Command("operators"))
@router.message(F.text == OPERATORS_BUTTON_TEXT)
async def handle_operators(
    message: Message,
    settings: Settings,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)

    async with helpdesk_service_factory() as helpdesk_service:
        operators = await helpdesk_service.list_operators(
            actor_telegram_user_id=message.from_user.id if message.from_user is not None else None
        )

    await message.answer(
        format_operator_list_response(
            operators=operators,
            super_admin_telegram_user_ids=settings.authorization.super_admin_telegram_user_ids,
        ),
        reply_markup=build_operator_management_markup(operators=operators),
    )


@router.callback_query(AdminOperatorCallback.filter(F.action == "refresh"))
async def handle_refresh_operators(
    callback: CallbackQuery,
    settings: Settings,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    if not await global_rate_limiter.allow():
        await respond_to_operator(callback, SERVICE_UNAVAILABLE_TEXT)
        return

    await operator_presence.touch(operator_id=callback.from_user.id)

    async with helpdesk_service_factory() as helpdesk_service:
        operators = await helpdesk_service.list_operators(
            actor_telegram_user_id=callback.from_user.id
        )

    await callback.answer(OPERATORS_REFRESHED_TEXT)
    if callback.message is None:
        return

    await callback.message.answer(
        format_operator_list_response(
            operators=operators,
            super_admin_telegram_user_ids=settings.authorization.super_admin_telegram_user_ids,
        ),
        reply_markup=build_operator_management_markup(operators=operators),
    )
