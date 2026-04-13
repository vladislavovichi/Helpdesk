from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.use_cases.tickets.summaries import TicketDetailsSummary, TicketMessageSummary
from bot.formatters.operator_ticket_views import (
    format_active_ticket_context,
    format_ticket_details,
    format_ticket_export_actions,
    format_ticket_history_chunks,
    format_ticket_more_actions,
)
from bot.keyboards.inline.operator_actions import (
    build_ticket_actions_markup,
    build_ticket_export_actions_markup,
    build_ticket_more_actions_markup,
)
from domain.enums.tickets import TicketMessageSenderType, TicketStatus


def test_format_ticket_details_returns_calm_operator_card() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти в личный кабинет",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        category_title="Доступ и вход",
        tags=("billing", "vip"),
        last_message_text="Проблема началась после смены пароля и теперь доступ не работает.",
        last_message_sender_type=TicketMessageSenderType.CLIENT,
        message_history=(),
    )

    result = format_ticket_details(ticket)

    assert "Заявка HD-AAAA1111" in result
    assert "В работе • высокий приоритет" in result
    assert "\nТема\nНе могу войти в личный кабинет" in result
    assert "\nКатегория\nДоступ и вход" in result
    assert "\nОператор\nИван Петров" in result
    assert "\nСоздана\n07.04.2026 12:30 UTC" in result
    assert "\nТеги\nbilling, vip" in result
    assert "\nПоследнее сообщение\nКлиент — Проблема началась после смены пароля" in result


def test_build_ticket_actions_markup_adds_macro_action_for_active_ticket() -> None:
    markup = build_ticket_actions_markup(ticket_public_id=uuid4(), status=TicketStatus.ASSIGNED)
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("Закрыть", "Макросы"), ("Экспорт", "Ещё"))


def test_build_ticket_actions_markup_hides_transfer_for_queued_ticket() -> None:
    markup = build_ticket_actions_markup(ticket_public_id=uuid4(), status=TicketStatus.QUEUED)
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert ("Взять", "Экспорт") in rows
    assert all("Передать" not in row for row in rows)


def test_build_ticket_more_actions_markup_groups_secondary_actions() -> None:
    markup = build_ticket_more_actions_markup(
        ticket_public_id=uuid4(),
        status=TicketStatus.ASSIGNED,
    )
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (
        ("Метки", "Передать"),
        ("Подсказки",),
        ("Заметки",),
        ("Экспорт",),
        ("Эскалация", "Карточка"),
        ("Назад",),
    )


def test_build_ticket_export_actions_markup_offers_two_formats() -> None:
    markup = build_ticket_export_actions_markup(ticket_public_id=uuid4())
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("HTML отчёт", "CSV выгрузка"), ("Назад",))


def test_format_active_ticket_context_stays_compact_and_obvious() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти в личный кабинет",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        category_title="Доступ и вход",
        tags=("billing", "vip"),
        last_message_text="Проблема началась после смены пароля и теперь доступ не работает.",
        last_message_sender_type=TicketMessageSenderType.CLIENT,
        message_history=(),
    )

    result = format_active_ticket_context(ticket)

    assert result.startswith("Текущий диалог")
    assert "HD-AAAA1111 · В работе • высокий приоритет" in result
    assert "Не могу войти в личный кабинет" in result
    assert "Категория · Доступ и вход" in result
    assert "Оператор · Иван Петров" in result
    assert "Теги · billing, vip" in result


def test_format_ticket_more_actions_reads_like_structured_secondary_surface() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти в личный кабинет",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        tags=(),
        last_message_text="Уже проверяем доступ.",
        last_message_sender_type=TicketMessageSenderType.OPERATOR,
        message_history=(),
    )

    result = format_ticket_more_actions(ticket, is_active=True)

    assert result.startswith("Текущий диалог")
    assert "\nЕщё" in result
    assert "\nИзменить\nМетки · Передать" in result
    assert "\nОтчёт\nЭкспорт" in result
    assert "\nСтатус и детали\nЭскалация · Карточка" in result


def test_format_ticket_export_actions_reads_like_report_surface() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти в личный кабинет",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        tags=("vip",),
        last_message_text="Уже проверяем доступ.",
        last_message_sender_type=TicketMessageSenderType.OPERATOR,
        message_history=(),
    )

    result = format_ticket_export_actions(ticket, is_active=True)

    assert result.startswith("Текущий диалог")
    assert "\nЭкспорт" in result
    assert (
        "\nФорматы\nHTML отчёт — спокойный case file с карточкой, перепиской и материалами дела."
        in result
    )
    assert "\nCSV выгрузка — структурированный слой для анализа, handoff и сверки." in result
    assert "Обе выгрузки доступны сразу из этого экрана." in result


def test_format_ticket_history_chunks_returns_calm_conversation_blocks() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти в личный кабинет",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        tags=(),
        last_message_text="Уже проверяем доступ.",
        last_message_sender_type=TicketMessageSenderType.OPERATOR,
        message_history=(
            TicketMessageSummary(
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_id=None,
                sender_operator_name=None,
                text="Не могу войти в личный кабинет.",
                created_at=datetime(2026, 4, 7, 12, 31, tzinfo=UTC),
            ),
            TicketMessageSummary(
                sender_type=TicketMessageSenderType.OPERATOR,
                sender_operator_id=7,
                sender_operator_name="Иван Петров",
                text="Уже проверяем доступ.",
                created_at=datetime(2026, 4, 7, 12, 35, tzinfo=UTC),
            ),
        ),
    )

    result = format_ticket_history_chunks(ticket)

    assert result[0].startswith("Переписка")
    assert "Клиент · 07.04.2026 12:31 UTC\nНе могу войти в личный кабинет." in result[0]
    assert "Оператор Иван Петров · 07.04.2026 12:35 UTC\nУже проверяем доступ." in result[0]
