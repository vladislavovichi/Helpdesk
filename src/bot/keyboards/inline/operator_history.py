from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from application.use_cases.tickets.summaries import HistoricalTicketSummary
from bot.callbacks import OperatorActionCallback, OperatorArchiveCallback
from bot.formatters.operator_primitives import shorten_text

ALL_ARCHIVE_CATEGORIES_ID = 0
UNCATEGORIZED_ARCHIVE_CATEGORY_ID = -1


def build_archive_markup(
    *,
    available_tickets: Sequence[HistoricalTicketSummary],
    tickets: Sequence[HistoricalTicketSummary],
    current_page: int,
    total_pages: int,
    selected_category_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for button in _build_filter_buttons(
        tickets=available_tickets,
        selected_category_id=selected_category_id,
    ):
        builder.row(*button)

    for ticket in tickets:
        builder.row(
            InlineKeyboardButton(
                text=_build_ticket_button_text(ticket),
                callback_data=OperatorArchiveCallback(
                    action="view",
                    page=current_page,
                    category_id=selected_category_id,
                    ticket_public_id=str(ticket.public_id),
                ).pack(),
            )
        )

    if total_pages > 1:
        pagination_row: list[InlineKeyboardButton] = []
        if current_page > 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="‹ Назад",
                    callback_data=OperatorArchiveCallback(
                        action="page",
                        page=current_page - 1,
                        category_id=selected_category_id,
                        ticket_public_id="0",
                    ).pack(),
                )
            )
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page} / {total_pages}",
                callback_data=OperatorArchiveCallback(
                    action="noop",
                    page=current_page,
                    category_id=selected_category_id,
                    ticket_public_id="0",
                ).pack(),
            )
        )
        if current_page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(
                    text="Далее ›",
                    callback_data=OperatorArchiveCallback(
                        action="page",
                        page=current_page + 1,
                        category_id=selected_category_id,
                        ticket_public_id="0",
                    ).pack(),
                )
            )
        builder.row(*pagination_row)

    return builder.as_markup()


def build_archived_ticket_markup(
    *,
    ticket_public_id: str,
    page: int,
    category_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="HTML отчёт",
            callback_data=OperatorActionCallback(
                action="export_html",
                ticket_public_id=ticket_public_id,
            ).pack(),
        ),
        InlineKeyboardButton(
            text="CSV",
            callback_data=OperatorActionCallback(
                action="export_csv",
                ticket_public_id=ticket_public_id,
            ).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="К архиву",
            callback_data=OperatorArchiveCallback(
                action="back",
                page=page,
                category_id=category_id,
                ticket_public_id=ticket_public_id,
            ).pack(),
        )
    )
    return builder.as_markup()


def _build_filter_buttons(
    *,
    tickets: Sequence[HistoricalTicketSummary],
    selected_category_id: int,
) -> tuple[tuple[InlineKeyboardButton, ...], ...]:
    options: list[tuple[int, str]] = [(ALL_ARCHIVE_CATEGORIES_ID, "Все темы")]
    seen_category_ids = {ALL_ARCHIVE_CATEGORIES_ID}

    for ticket in tickets:
        category_id = ticket.category_id
        if category_id is None:
            if UNCATEGORIZED_ARCHIVE_CATEGORY_ID not in seen_category_ids:
                options.append((UNCATEGORIZED_ARCHIVE_CATEGORY_ID, "Без темы"))
                seen_category_ids.add(UNCATEGORIZED_ARCHIVE_CATEGORY_ID)
            continue
        if category_id in seen_category_ids:
            continue
        options.append((category_id, ticket.category_title or "Без названия"))
        seen_category_ids.add(category_id)

    rows: list[tuple[InlineKeyboardButton, ...]] = []
    current_row: list[InlineKeyboardButton] = []
    for category_id, title in options:
        label = (
            f"• {shorten_text(title, 16)}"
            if category_id == selected_category_id
            else shorten_text(title, 16)
        )
        current_row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=OperatorArchiveCallback(
                    action="filter",
                    page=1,
                    category_id=category_id,
                    ticket_public_id="0",
                ).pack(),
            )
        )
        if len(current_row) == 2:
            rows.append(tuple(current_row))
            current_row = []
    if current_row:
        rows.append(tuple(current_row))
    return tuple(rows)


def _build_ticket_button_text(ticket: HistoricalTicketSummary) -> str:
    prefix = ticket.public_number
    if ticket.category_title:
        prefix = f"{prefix} · {shorten_text(ticket.category_title, 14)}"
    return shorten_text(prefix, 32)
