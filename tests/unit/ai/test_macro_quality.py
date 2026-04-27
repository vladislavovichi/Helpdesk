from __future__ import annotations

import json

from ai_service.service import AIApplicationService
from ai_service.service_results import has_macro_suggestion_signal, has_prediction_signal
from application.ai.summaries import AIPredictionConfidence
from application.contracts.ai import (
    AICategoryOption,
    AIPredictTicketCategoryCommand,
    AISuggestedMacro,
)
from application.use_cases.ai.assist import _resolve_macro_suggestions
from application.use_cases.tickets.summaries import MacroSummary
from infrastructure.config.settings import AIConfig

from .fakes import FakeAIProvider
from .quality_fixtures import get_ai_fixture


async def test_macro_suggestions_require_meaningful_signal() -> None:
    provider = FakeAIProvider((_macro_json(),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.suggest_macros(get_ai_fixture("no_prediction_signal").macro_command())

    assert result.available is True
    assert result.suggestions == ()
    assert provider.call_count == 0


def test_macro_signal_accepts_attachment_only_ticket() -> None:
    assert (
        has_macro_suggestion_signal(get_ai_fixture("attachment_only_ticket").macro_command())
        is True
    )


def test_categories_alone_are_not_prediction_signal() -> None:
    assert (
        has_prediction_signal(
            AIPredictTicketCategoryCommand(
                text=" ",
                categories=(AICategoryOption(id=2, code="billing", title="Оплата"),),
            )
        )
        is False
    )


async def test_macro_suggestions_preserve_reason_and_confidence() -> None:
    provider = FakeAIProvider((_macro_json(),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.suggest_macros(get_ai_fixture("angry_customer").macro_command())

    assert tuple(item.macro_id for item in result.suggestions) == (20,)
    assert result.suggestions[0].reason == "Нужна ручная проверка платежа без обещаний."
    assert result.suggestions[0].confidence is AIPredictionConfidence.HIGH
    assert provider.call_count == 1


def test_invalid_macro_ids_are_ignored_by_assist_resolution() -> None:
    suggestions = _resolve_macro_suggestions(
        macros=(MacroSummary(id=20, title="Проверим вручную", body="Проверим и вернёмся."),),
        suggestions=(
            AISuggestedMacro(
                macro_id=999,
                reason="Несуществующий макрос не должен попадать в UI.",
                confidence=AIPredictionConfidence.HIGH,
            ),
            AISuggestedMacro(
                macro_id=20,
                reason="Подходит для запроса ручной проверки.",
                confidence=AIPredictionConfidence.MEDIUM,
            ),
        ),
    )

    assert tuple(item.macro_id for item in suggestions) == (20,)


def _macro_json() -> str:
    return json.dumps(
        {
            "macro_ids": [
                {
                    "macro_id": 20,
                    "reason": "Нужна ручная проверка платежа без обещаний.",
                    "confidence": "high",
                }
            ]
        },
        ensure_ascii=False,
    )
