from __future__ import annotations

import json

from ai_service.service import AIApplicationService
from application.ai.summaries import AIPredictionConfidence
from infrastructure.config.settings import AIConfig

from .fakes import FakeAIProvider
from .quality_fixtures import get_ai_fixture


async def test_blank_text_without_attachment_does_not_trigger_prediction() -> None:
    provider = FakeAIProvider((_category_json(category_id=2),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.predict_ticket_category(
        get_ai_fixture("no_prediction_signal").category_command()
    )

    assert result.available is False
    assert provider.call_count == 0


async def test_attachment_counts_as_prediction_signal() -> None:
    provider = FakeAIProvider((_category_json(category_id=4),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.predict_ticket_category(
        get_ai_fixture("attachment_only_ticket").category_command()
    )

    assert result.available is True
    assert result.category_id == 4
    assert result.confidence is AIPredictionConfidence.HIGH
    assert provider.call_count == 1


async def test_text_counts_as_prediction_signal() -> None:
    provider = FakeAIProvider((_category_json(category_id=2),))
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.predict_ticket_category(
        get_ai_fixture("angry_customer").category_command()
    )

    assert result.available is True
    assert result.category_id == 2
    assert provider.call_count == 1


async def test_ambiguous_category_returns_safe_fallback() -> None:
    provider = FakeAIProvider(
        (
            json.dumps(
                {
                    "category_id": None,
                    "confidence": "none",
                    "reason": "Подходят и оплата, и доставка.",
                },
                ensure_ascii=False,
            ),
        )
    )
    service = AIApplicationService(provider=provider, config=AIConfig())

    result = await service.predict_ticket_category(
        get_ai_fixture("ambiguous_category").category_command()
    )

    assert result.available is False
    assert result.confidence is AIPredictionConfidence.NONE
    assert provider.call_count == 1


def _category_json(*, category_id: int) -> str:
    return json.dumps(
        {
            "category_id": category_id,
            "confidence": "high",
            "reason": "Есть явные признаки выбранной темы.",
        },
        ensure_ascii=False,
    )
