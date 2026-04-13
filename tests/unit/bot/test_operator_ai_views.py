from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.ai.summaries import (
    AIPredictionConfidence,
    TicketAssistSnapshot,
    TicketMacroSuggestion,
    TicketSummaryStatus,
)
from application.use_cases.tickets.summaries import TicketDetailsSummary
from bot.formatters.operator_ai import format_ticket_assist_snapshot
from bot.keyboards.inline.operator_actions import build_ticket_assist_markup
from domain.enums.tickets import TicketStatus


def test_format_ticket_assist_snapshot_marks_stale_summary_explicitly() -> None:
    ticket = TicketDetailsSummary(
        public_id=uuid4(),
        public_number="HD-AAAA1111",
        client_chat_id=1001,
        status=TicketStatus.ASSIGNED,
        priority="high",
        subject="Не могу войти после смены пароля",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 7, 12, 30, tzinfo=UTC),
        message_history=(),
    )
    snapshot = TicketAssistSnapshot(
        available=True,
        summary_status=TicketSummaryStatus.STALE,
        summary_generated_at=datetime(2026, 4, 7, 12, 40, tzinfo=UTC),
        short_summary="Клиент потерял доступ после смены пароля.",
        user_goal="Восстановить вход без повторной регистрации.",
        actions_taken="Оператор проверил профиль и готовит сброс.",
        current_status="После сводки появилось новое сообщение клиента.",
        macro_suggestions=(
            TicketMacroSuggestion(
                macro_id=1,
                title="Сброс доступа",
                body="Сбросили пароль и обновили ссылку.",
                reason="В диалоге нужен готовый ответ про восстановление входа.",
                confidence=AIPredictionConfidence.HIGH,
            ),
        ),
        status_note="После последней сводки появились 2 сообщения. Обновите её по переписке.",
        model_id="Qwen/Qwen3.5-4B",
    )

    result = format_ticket_assist_snapshot(ticket=ticket, snapshot=snapshot)

    assert result.startswith("AI-подсказки · HD-AAAA1111")
    assert "Сводка устарела после новых изменений." in result
    assert "Основание: В диалоге нужен готовый ответ про восстановление входа." in result
    assert "После последней сводки появились 2 сообщения. Обновите её по переписке." in result


def test_build_ticket_assist_markup_uses_refresh_wording_for_existing_summary() -> None:
    markup = build_ticket_assist_markup(
        ticket_public_id=uuid4(),
        summary_status=TicketSummaryStatus.STALE,
        suggested_macro_ids=((1, "Сброс доступа"),),
    )
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows[0] == ("Обновить по переписке",)
    assert rows[1] == ("Сброс доступа",)
    assert rows[2] == ("Все макросы",)


def test_build_ticket_assist_markup_uses_generate_wording_without_summary() -> None:
    markup = build_ticket_assist_markup(
        ticket_public_id=uuid4(),
        summary_status=TicketSummaryStatus.MISSING,
        suggested_macro_ids=(),
    )
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows[0] == ("Собрать сводку",)
