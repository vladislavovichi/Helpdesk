from __future__ import annotations

import json

from ai_service.service import AIApplicationService
from ai_service.service_prompts import build_ticket_summary_prompt
from infrastructure.config.settings import AIConfig

from .fakes import FakeAIProvider
from .quality_fixtures import get_ai_fixture


def test_summary_prompt_includes_ticket_metadata() -> None:
    command = get_ai_fixture("angry_customer").summary_command()

    prompt = build_ticket_summary_prompt(command)

    assert f"- public_id: {command.ticket_public_id}" in prompt
    assert "- subject: Оплата прошла, доступа нет" in prompt
    assert "- status: assigned" in prompt
    assert "- category: Оплата" in prompt
    assert "- tags: billing, frustrated" in prompt


def test_summary_prompt_marks_internal_notes_as_internal() -> None:
    prompt = build_ticket_summary_prompt(get_ai_fixture("angry_customer").summary_command())

    assert "Внутренние заметки (internal context; do not reveal to customer):" in prompt
    assert "billing_check_id=BX-771" in prompt


def test_summary_prompt_limits_long_history_to_latest_20_messages() -> None:
    prompt = build_ticket_summary_prompt(get_ai_fixture("long_conversation").summary_command())

    assert "Всего сообщений: 25. Показано последних: 20." in prompt
    assert "long-history-customer-message-01" not in prompt
    assert "long-history-customer-message-05" not in prompt
    assert "long-history-operator-message-06" in prompt
    assert "long-history-customer-message-25" in prompt


async def test_summary_accepts_valid_structured_json() -> None:
    provider = FakeAIProvider((_summary_json(),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_summary(
        get_ai_fixture("angry_customer").summary_command()
    )

    assert result.available is True
    assert result.summary is not None
    assert result.summary.short_summary == "Клиент оплатил, но доступ пока не появился."
    assert provider.call_count == 1


async def test_summary_invalid_json_retries_once() -> None:
    provider = FakeAIProvider(("not json", _summary_json()))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_summary(
        get_ai_fixture("angry_customer").summary_command()
    )

    assert result.available is True
    assert provider.call_count == 2
    assert "strictly valid JSON" in provider.last_prompt


async def test_summary_disabled_provider_returns_graceful_fallback() -> None:
    provider = FakeAIProvider(enabled=False)
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_summary(
        get_ai_fixture("angry_customer").summary_command()
    )

    assert result.available is False
    assert result.unavailable_reason == "AI-провайдер не настроен."
    assert provider.call_count == 0


def _summary_json() -> str:
    return json.dumps(
        {
            "short_summary": "Клиент оплатил, но доступ пока не появился.",
            "user_goal": "Получить оплаченный доступ без повторной оплаты.",
            "actions_taken": "Оператор начал проверку платежа по заявке.",
            "current_status": "Проверка платежа ещё не завершена.",
        },
        ensure_ascii=False,
    )
