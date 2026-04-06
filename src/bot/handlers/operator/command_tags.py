from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from application.services.helpdesk.service import HelpdeskServiceFactory
from bot.formatters.operator import format_tags, format_ticket_tags_response
from bot.handlers.operator.parsers import parse_ticket_argument_with_text, parse_ticket_public_id
from bot.texts.common import (
    INVALID_TICKET_ID_TEXT,
    SERVICE_UNAVAILABLE_TEXT,
    TICKET_LOCKED_TEXT,
    TICKET_NOT_FOUND_TEXT,
)
from bot.texts.operator import (
    TAGS_EMPTY_TEXT,
    build_available_tags_text,
    build_tag_added_text,
    build_tag_already_added_text,
    build_tag_missing_text,
    build_tag_removed_text,
    invalid_add_tag_usage_text,
    invalid_remove_tag_usage_text,
    invalid_tags_usage_text,
)
from infrastructure.redis.contracts import (
    GlobalRateLimiter,
    OperatorPresenceHelper,
    TicketLockManager,
)

router = Router(name="operator_command_tags")


@router.message(Command("tags"))
async def handle_ticket_tags(
    message: Message,
    command: CommandObject,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    if command.args is None:
        await message.answer(invalid_tags_usage_text())
        return

    ticket_public_id = parse_ticket_public_id(command.args.strip())
    if ticket_public_id is None:
        await message.answer(INVALID_TICKET_ID_TEXT)
        return
    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)

    actor_telegram_user_id = message.from_user.id if message.from_user is not None else None
    async with helpdesk_service_factory() as helpdesk_service:
        tags_result = await helpdesk_service.list_ticket_tags(
            ticket_public_id=ticket_public_id,
            actor_telegram_user_id=actor_telegram_user_id,
        )
        available_tags = await helpdesk_service.list_available_tags(
            actor_telegram_user_id=actor_telegram_user_id,
        )

    if tags_result is None:
        await message.answer(TICKET_NOT_FOUND_TEXT)
        return

    await message.answer(
        format_ticket_tags_response(
            tags_result.public_number,
            tags_result.tags,
            available_tags,
        )
    )


@router.message(Command("alltags"))
async def handle_all_tags(
    message: Message,
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
        available_tags = await helpdesk_service.list_available_tags(
            actor_telegram_user_id=message.from_user.id if message.from_user is not None else None,
        )

    if not available_tags:
        await message.answer(TAGS_EMPTY_TEXT)
        return

    await message.answer(build_available_tags_text(tuple(available_tags)))


@router.message(Command("addtag"))
async def handle_add_tag(
    message: Message,
    command: CommandObject,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
    ticket_lock_manager: TicketLockManager,
) -> None:
    parsed = parse_ticket_argument_with_text(command.args)
    if parsed is None:
        await message.answer(invalid_add_tag_usage_text())
        return

    ticket_public_id, tag_name = parsed
    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)

    actor_telegram_user_id = message.from_user.id if message.from_user is not None else None
    lock = ticket_lock_manager.for_ticket(str(ticket_public_id))
    if not await lock.acquire():
        await message.answer(TICKET_LOCKED_TEXT)
        return

    try:
        async with helpdesk_service_factory() as helpdesk_service:
            result = await helpdesk_service.add_tag_to_ticket(
                ticket_public_id=ticket_public_id,
                tag_name=tag_name,
                actor_telegram_user_id=actor_telegram_user_id,
            )
    finally:
        await lock.release()

    if result is None:
        await message.answer(TICKET_NOT_FOUND_TEXT)
        return

    tag_list = format_tags(result.tags)
    if result.changed:
        await message.answer(
            build_tag_added_text(result.ticket.public_number, result.tag, tag_list)
        )
        return

    await message.answer(
        build_tag_already_added_text(result.ticket.public_number, result.tag, tag_list)
    )


@router.message(Command("rmtag"))
async def handle_remove_tag(
    message: Message,
    command: CommandObject,
    helpdesk_service_factory: HelpdeskServiceFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
    ticket_lock_manager: TicketLockManager,
) -> None:
    parsed = parse_ticket_argument_with_text(command.args)
    if parsed is None:
        await message.answer(invalid_remove_tag_usage_text())
        return

    ticket_public_id, tag_name = parsed
    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)

    actor_telegram_user_id = message.from_user.id if message.from_user is not None else None
    lock = ticket_lock_manager.for_ticket(str(ticket_public_id))
    if not await lock.acquire():
        await message.answer(TICKET_LOCKED_TEXT)
        return

    try:
        async with helpdesk_service_factory() as helpdesk_service:
            result = await helpdesk_service.remove_tag_from_ticket(
                ticket_public_id=ticket_public_id,
                tag_name=tag_name,
                actor_telegram_user_id=actor_telegram_user_id,
            )
    finally:
        await lock.release()

    if result is None:
        await message.answer(TICKET_NOT_FOUND_TEXT)
        return

    tag_list = format_tags(result.tags)
    if result.changed:
        await message.answer(
            build_tag_removed_text(result.ticket.public_number, result.tag, tag_list)
        )
        return

    await message.answer(build_tag_missing_text(result.ticket.public_number, result.tag, tag_list))
