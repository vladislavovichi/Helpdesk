from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from application.services.helpdesk.service import HelpdeskServiceFactory
from bot.formatters.macros import (
    format_macro_library,
    format_operator_macro_picker,
    paginate_macros,
)
from bot.handlers.operator.parsers import parse_ticket_public_id
from bot.keyboards.inline.macros import build_operator_macro_picker_markup
from bot.texts.common import SERVICE_UNAVAILABLE_TEXT, TICKET_NOT_FOUND_TEXT
from bot.texts.operator import MACROS_EMPTY_TEXT, invalid_macros_usage_text
from infrastructure.redis.contracts import GlobalRateLimiter, OperatorPresenceHelper

router = Router(name="operator_command_macros")


@router.message(Command("macros"))
async def handle_macros(
    message: Message,
    command: CommandObject,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    ticket_public_id = None
    if command.args is not None and command.args.strip():
        ticket_public_id = parse_ticket_public_id(command.args.strip())
        if ticket_public_id is None:
            await message.answer(invalid_macros_usage_text())
            return

    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)

    actor_telegram_user_id = message.from_user.id if message.from_user is not None else None
    async with helpdesk_service_factory() as helpdesk_service:
        macros = await helpdesk_service.list_macros(actor_telegram_user_id=actor_telegram_user_id)
        ticket_details = None
        if ticket_public_id is not None:
            ticket_details = await helpdesk_service.get_ticket_details(
                ticket_public_id=ticket_public_id,
                actor_telegram_user_id=actor_telegram_user_id,
            )

    if ticket_public_id is not None and ticket_details is None:
        await message.answer(TICKET_NOT_FOUND_TEXT)
        return
    if not macros:
        await message.answer(MACROS_EMPTY_TEXT)
        return

    if ticket_public_id is None:
        await message.answer(format_macro_library(macros))
        return

    assert ticket_details is not None
    page_macros, current_page, total_pages = paginate_macros(macros, page=1)
    await message.answer(
        format_operator_macro_picker(
            ticket_public_number=ticket_details.public_number,
            macros=page_macros,
            current_page=current_page,
            total_pages=total_pages,
        ),
        reply_markup=build_operator_macro_picker_markup(
            ticket_public_id=ticket_public_id,
            macros=page_macros,
            current_page=current_page,
            total_pages=total_pages,
        ),
    )
