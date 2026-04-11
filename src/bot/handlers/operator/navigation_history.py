from __future__ import annotations

from math import ceil

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from application.use_cases.tickets.summaries import HistoricalTicketSummary
from backend.grpc.contracts import HelpdeskBackendClientFactory
from bot.adapters.helpdesk import build_request_actor
from bot.callbacks import OperatorArchiveCallback
from bot.formatters.operator_archive_views import (
    ARCHIVE_PAGE_CHUNK,
    format_archive_page,
    format_archived_ticket_surface,
)
from bot.handlers.operator.common import respond_to_operator
from bot.handlers.operator.parsers import parse_ticket_public_id
from bot.keyboards.inline.operator_history import (
    ALL_ARCHIVE_CATEGORIES_ID,
    UNCATEGORIZED_ARCHIVE_CATEGORY_ID,
    build_archive_markup,
    build_archived_ticket_markup,
)
from bot.texts.buttons import ARCHIVE_BUTTON_TEXT
from bot.texts.common import INVALID_TICKET_ID_TEXT, SERVICE_UNAVAILABLE_TEXT, TICKET_NOT_FOUND_TEXT
from bot.texts.operator import (
    ARCHIVE_EMPTY_TEXT,
    build_archive_page_callback_text,
    build_archived_ticket_opened_text,
)
from infrastructure.redis.contracts import GlobalRateLimiter, OperatorPresenceHelper

router = Router(name="operator_navigation_history")


@router.message(F.text == ARCHIVE_BUTTON_TEXT)
async def handle_archive(
    message: Message,
    state: FSMContext,
    helpdesk_backend_client_factory: HelpdeskBackendClientFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    if not await global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    if message.from_user is not None:
        await operator_presence.touch(operator_id=message.from_user.id)
    await state.clear()

    async with helpdesk_backend_client_factory() as helpdesk_backend:
        tickets = await helpdesk_backend.list_archived_tickets(
            actor=build_request_actor(message.from_user),
        )

    if not tickets:
        await message.answer(ARCHIVE_EMPTY_TEXT)
        return

    archive_text, archive_markup = build_archive_page_response(
        tickets=tickets,
        page=1,
        category_id=ALL_ARCHIVE_CATEGORIES_ID,
    )
    await message.answer(archive_text, reply_markup=archive_markup)


@router.callback_query(OperatorArchiveCallback.filter(F.action.in_({"page", "filter", "back"})))
async def handle_archive_navigation(
    callback: CallbackQuery,
    callback_data: OperatorArchiveCallback,
    state: FSMContext,
    helpdesk_backend_client_factory: HelpdeskBackendClientFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    if not await global_rate_limiter.allow():
        await respond_to_operator(callback, SERVICE_UNAVAILABLE_TEXT)
        return

    await operator_presence.touch(operator_id=callback.from_user.id)
    await state.clear()

    async with helpdesk_backend_client_factory() as helpdesk_backend:
        tickets = await helpdesk_backend.list_archived_tickets(
            actor=build_request_actor(callback.from_user),
        )

    if not tickets:
        await respond_to_operator(callback, ARCHIVE_EMPTY_TEXT, ARCHIVE_EMPTY_TEXT)
        return

    archive_text, archive_markup = build_archive_page_response(
        tickets=tickets,
        page=callback_data.page,
        category_id=callback_data.category_id,
    )
    category_title = resolve_archive_category_title(
        tickets=tickets,
        category_id=callback_data.category_id,
    )

    if not isinstance(callback.message, Message):
        await callback.answer(
            build_archive_page_callback_text(callback_data.page, category_title=category_title)
        )
        return

    await callback.answer(
        build_archive_page_callback_text(callback_data.page, category_title=category_title)
    )
    await callback.message.edit_text(archive_text, reply_markup=archive_markup)


@router.callback_query(OperatorArchiveCallback.filter(F.action == "view"))
async def handle_archived_ticket_view(
    callback: CallbackQuery,
    callback_data: OperatorArchiveCallback,
    helpdesk_backend_client_factory: HelpdeskBackendClientFactory,
    global_rate_limiter: GlobalRateLimiter,
    operator_presence: OperatorPresenceHelper,
) -> None:
    ticket_public_id = parse_ticket_public_id(callback_data.ticket_public_id)
    if ticket_public_id is None:
        await respond_to_operator(callback, INVALID_TICKET_ID_TEXT)
        return
    if not await global_rate_limiter.allow():
        await respond_to_operator(callback, SERVICE_UNAVAILABLE_TEXT)
        return

    await operator_presence.touch(operator_id=callback.from_user.id)
    async with helpdesk_backend_client_factory() as helpdesk_backend:
        ticket_details = await helpdesk_backend.get_ticket_details(
            ticket_public_id=ticket_public_id,
            actor=build_request_actor(callback.from_user),
        )

    if ticket_details is None:
        await respond_to_operator(callback, TICKET_NOT_FOUND_TEXT)
        return

    if not isinstance(callback.message, Message):
        await callback.answer(build_archived_ticket_opened_text(ticket_details.public_number))
        return

    await callback.answer(build_archived_ticket_opened_text(ticket_details.public_number))
    await callback.message.edit_text(
        format_archived_ticket_surface(ticket_details),
        reply_markup=build_archived_ticket_markup(
            ticket_public_id=str(ticket_details.public_id),
            page=callback_data.page,
            category_id=callback_data.category_id,
        ),
    )


@router.callback_query(OperatorArchiveCallback.filter(F.action == "noop"))
async def handle_archive_noop(
    callback: CallbackQuery,
    callback_data: OperatorArchiveCallback,
    helpdesk_backend_client_factory: HelpdeskBackendClientFactory,
) -> None:
    async with helpdesk_backend_client_factory() as helpdesk_backend:
        tickets = await helpdesk_backend.list_archived_tickets(
            actor=build_request_actor(callback.from_user),
        )
    category_title = resolve_archive_category_title(
        tickets=tickets,
        category_id=callback_data.category_id,
    )
    await callback.answer(
        build_archive_page_callback_text(callback_data.page, category_title=category_title)
    )


def build_archive_page_response(
    *,
    tickets: tuple[HistoricalTicketSummary, ...] | list[HistoricalTicketSummary],
    page: int,
    category_id: int,
) -> tuple[str, object]:
    filtered_tickets = filter_archived_tickets(tickets=tickets, category_id=category_id)
    total_pages = max(1, ceil(len(filtered_tickets) / ARCHIVE_PAGE_CHUNK))
    safe_page = min(max(page, 1), total_pages)
    start = (safe_page - 1) * ARCHIVE_PAGE_CHUNK
    end = start + ARCHIVE_PAGE_CHUNK
    page_tickets = filtered_tickets[start:end]
    category_title = resolve_archive_category_title(tickets=tickets, category_id=category_id)
    return (
        format_archive_page(
            page_tickets,
            current_page=safe_page,
            total_pages=total_pages,
            selected_category_title=category_title,
        ),
        build_archive_markup(
            available_tickets=tickets,
            tickets=page_tickets,
            current_page=safe_page,
            total_pages=total_pages,
            selected_category_id=category_id,
        ),
    )


def filter_archived_tickets(
    *,
    tickets: tuple[HistoricalTicketSummary, ...] | list[HistoricalTicketSummary],
    category_id: int,
) -> list[HistoricalTicketSummary]:
    if category_id == ALL_ARCHIVE_CATEGORIES_ID:
        return list(tickets)
    if category_id == UNCATEGORIZED_ARCHIVE_CATEGORY_ID:
        return [ticket for ticket in tickets if ticket.category_id is None]
    return [ticket for ticket in tickets if ticket.category_id == category_id]


def resolve_archive_category_title(
    *,
    tickets: tuple[HistoricalTicketSummary, ...] | list[HistoricalTicketSummary],
    category_id: int,
) -> str | None:
    if category_id == ALL_ARCHIVE_CATEGORIES_ID:
        return None
    if category_id == UNCATEGORIZED_ARCHIVE_CATEGORY_ID:
        return "Без темы"
    for ticket in tickets:
        if ticket.category_id == category_id:
            return ticket.category_title or "Без темы"
    return None
