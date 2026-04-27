from __future__ import annotations

import json

from ai_service.service import AIApplicationService
from ai_service.service_prompts import build_reply_draft_prompt
from infrastructure.config.settings import AIConfig

from .fakes import FakeAIProvider
from .quality_fixtures import get_ai_fixture


async def test_reply_draft_does_not_expose_internal_notes() -> None:
    provider = FakeAIProvider(
        (
            _draft_json(
                reply_text="Здравствуйте! Проверим оплату по заявке и вернёмся с ответом.",
                safety_note="Не раскрывает внутренние данные проверки.",
            ),
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())
    command = get_ai_fixture("angry_customer").reply_draft_command()

    prompt = build_reply_draft_prompt(command)
    result = await service.generate_ticket_reply_draft(command)

    assert "billing_check_id=BX-771" in prompt
    assert "не раскрывай клиенту" in prompt
    assert result.available is True
    assert result.reply_text is not None
    assert "billing_check_id" not in result.reply_text
    assert "BX-771" not in result.reply_text


async def test_reply_draft_asks_for_missing_information_when_context_is_insufficient() -> None:
    provider = FakeAIProvider(
        (
            _draft_json(
                reply_text="Здравствуйте! Уточните, пожалуйста, что именно не работает.",
                missing_information=["описание проблемы", "номер заказа или аккаунта"],
                confidence=0.55,
            ),
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_reply_draft(
        get_ai_fixture("short_ticket_missing_details").reply_draft_command(include_summary=False)
    )

    assert result.available is True
    assert result.reply_text is not None
    assert "Уточните" in result.reply_text
    assert result.missing_information == ("описание проблемы", "номер заказа или аккаунта")


async def test_reply_draft_does_not_promise_sensitive_actions_without_context() -> None:
    provider = FakeAIProvider(
        (
            _draft_json(
                reply_text=(
                    "Здравствуйте! Мы проверим запрос на изменение данных аккаунта "
                    "и сообщим результат после проверки."
                ),
                safety_note="Не обещает изменение аккаунта до проверки.",
            ),
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_reply_draft(
        get_ai_fixture("escalation_required").reply_draft_command()
    )

    assert result.available is True
    assert result.reply_text is not None
    lowered = result.reply_text.lower()
    assert "возврат" not in lowered
    assert "компенса" not in lowered
    assert "уже изменили" not in lowered
    assert "уже решили" not in lowered


async def test_reply_draft_requires_strict_validated_structure() -> None:
    provider = FakeAIProvider(
        (
            json.dumps(
                {
                    "reply_text": "Здравствуйте! Проверим обращение.",
                    "tone": "polite",
                    "confidence": 2,
                    "safety_note": None,
                    "missing_information": None,
                },
                ensure_ascii=False,
            ),
            '{"still":"bad"}',
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_reply_draft(
        get_ai_fixture("angry_customer").reply_draft_command()
    )

    assert result.available is False
    assert result.unavailable_reason == "Не удалось подготовить черновик ответа."
    assert provider.call_count == 2


async def test_reply_draft_invalid_json_retries_once() -> None:
    provider = FakeAIProvider(
        (
            "```json\nnot-json\n```",
            _draft_json(
                reply_text="Здравствуйте! Проверим вашу заявку и вернёмся с ответом.",
                confidence=0.74,
            ),
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.generate_ticket_reply_draft(
        get_ai_fixture("angry_customer").reply_draft_command()
    )

    assert result.available is True
    assert result.reply_text == "Здравствуйте! Проверим вашу заявку и вернёмся с ответом."
    assert provider.call_count == 2
    assert "strictly valid JSON" in provider.last_prompt


def _draft_json(
    *,
    reply_text: str,
    tone: str = "polite",
    confidence: float | None = 0.8,
    safety_note: str | None = None,
    missing_information: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "reply_text": reply_text,
            "tone": tone,
            "confidence": confidence,
            "safety_note": safety_note,
            "missing_information": missing_information,
        },
        ensure_ascii=False,
    )
