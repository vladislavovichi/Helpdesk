from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.use_cases.tickets.archive_browser import ArchiveCategoryFilter
from application.use_cases.tickets.summaries import HistoricalTicketSummary, QueuedTicketSummary
from bot.formatters.operator_archive_views import format_archive_page, format_archive_topic_picker
from bot.formatters.operator_ticket_views import format_queue_page
from bot.keyboards.inline.operator_actions import build_queue_markup
from bot.keyboards.inline.operator_history import build_archive_topic_picker_markup
from domain.enums.tickets import TicketStatus


def test_format_queue_page_returns_compact_paginated_text() -> None:
    tickets = (
        QueuedTicketSummary(
            public_id=uuid4(),
            public_number="HD-AAAA1111",
            subject="Нужен доступ к кабинету",
            priority="high",
            status=TicketStatus.QUEUED,
        ),
        QueuedTicketSummary(
            public_id=uuid4(),
            public_number="HD-BBBB2222",
            subject="Не приходит письмо",
            priority="normal",
            status=TicketStatus.QUEUED,
        ),
    )

    result = format_queue_page(tickets, current_page=2, total_pages=3)

    assert "Очередь" in result
    assert "Страница 2 / 3" in result
    assert "1. HD-AAAA1111" in result
    assert "   В очереди • высокий приоритет" in result
    assert "   Не приходит письмо" in result
    assert "Откройте заявку, чтобы посмотреть историю и действия." in result


def test_format_archive_page_returns_case_list_with_mini_titles() -> None:
    tickets = (
        HistoricalTicketSummary(
            public_id=uuid4(),
            public_number="HD-ARCH0001",
            status=TicketStatus.CLOSED,
            created_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
            closed_at=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
            mini_title="Не могу войти в кабинет после смены пароля",
            category_id=2,
            category_title="Доступ и вход",
        ),
    )

    result = format_archive_page(
        tickets,
        current_page=1,
        total_pages=2,
        selected_category_title="Доступ и вход",
        total_filtered_tickets=1,
    )

    assert "Архив · Доступ и вход" in result
    assert "Дела: 1 · страница 1 / 2" in result
    assert "1. HD-ARCH0001 · Доступ и вход" in result
    assert "Закрыта • Создана" in result
    assert "Не могу войти в кабинет после смены пароля" in result


def test_format_archive_topic_picker_lists_available_topics() -> None:
    result = format_archive_topic_picker(
        filters=(
            ArchiveCategoryFilter(id=0, title="Все темы", ticket_count=6),
            ArchiveCategoryFilter(id=2, title="Доступ и вход", ticket_count=4),
            ArchiveCategoryFilter(id=3, title="Оплата", ticket_count=2),
        ),
        selected_category_title="Доступ и вход",
    )

    assert "Темы архива" in result
    assert "Сейчас выбрано: Доступ и вход" in result
    assert "1. Доступ и вход · 4" in result
    assert "2. Оплата · 2" in result


def test_build_queue_markup_contains_ticket_actions_and_pagination() -> None:
    tickets = (
        QueuedTicketSummary(
            public_id=uuid4(),
            public_number="HD-AAAA1111",
            subject="Нужен доступ к кабинету",
            priority="high",
            status=TicketStatus.QUEUED,
        ),
        QueuedTicketSummary(
            public_id=uuid4(),
            public_number="HD-BBBB2222",
            subject="Не приходит письмо",
            priority="normal",
            status=TicketStatus.QUEUED,
        ),
    )

    markup = build_queue_markup(tickets=tickets, current_page=2, total_pages=4)
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("HD-AAAA1111",), ("HD-BBBB2222",), ("‹ Назад", "2 / 4", "Далее ›"))


def test_build_archive_topic_picker_markup_keeps_clean_return_path() -> None:
    markup = build_archive_topic_picker_markup(
        filters=(
            ArchiveCategoryFilter(id=0, title="Все темы", ticket_count=6),
            ArchiveCategoryFilter(id=2, title="Доступ и вход", ticket_count=4),
            ArchiveCategoryFilter(id=3, title="Оплата", ticket_count=2),
        ),
        current_page=2,
        selected_category_id=2,
    )
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("• Доступ и вход · 4",), ("Оплата · 2",), ("К архиву",))
