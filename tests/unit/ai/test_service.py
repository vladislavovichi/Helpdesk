from __future__ import annotations

from uuid import uuid4

from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider
from application.ai.summaries import AIPredictionConfidence
from application.contracts.ai import (
    AICategoryOption,
    AIPredictTicketCategoryCommand,
    AnalyzeTicketSentimentCommand,
    GenerateTicketSummaryCommand,
    MacroCandidate,
    SuggestMacrosCommand,
)
from domain.enums.tickets import TicketSentiment, TicketSignalConfidence, TicketStatus
from infrastructure.config.settings import AIConfig


class StubProvider(AIProvider):
    def __init__(
        self,
        raw: str,
        *,
        enabled: bool = True,
        model_id: str | None = "test-model",
    ) -> None:
        self._raw = raw
        self._enabled = enabled
        self._model_id = model_id

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def model_id(self) -> str | None:
        return self._model_id

    async def complete(
        self,
        *,
        messages: object,
        max_output_tokens: int,
        temperature: float,
    ) -> str:
        del messages, max_output_tokens, temperature
        return self._raw


async def test_generate_ticket_summary_rejects_low_value_payload() -> None:
    service = AIApplicationService(
        provider=StubProvider(
            '{"short_summary":"Подходит","user_goal":"Подходит","actions_taken":"Подходит","current_status":"Подходит"}'
        ),
        config=AIConfig(),
    )

    result = await service.generate_ticket_summary(
        GenerateTicketSummaryCommand(
            ticket_public_id=uuid4(),
            subject="Не могу войти",
            status=TicketStatus.ASSIGNED,
            category_title=None,
        )
    )

    assert result.available is False
    assert result.unavailable_reason == "Не удалось подготовить достаточно надёжную сводку."


async def test_suggest_macros_filters_generic_reasoning() -> None:
    raw = (
        '{"macro_ids":[{"macro_id":1,"reason":"по теме","confidence":"high"},'
        '{"macro_id":2,"reason":"Подходит для спокойного ответа про проверку платежа.",'
        '"confidence":"high"}]}'
    )
    service = AIApplicationService(
        provider=StubProvider(raw),
        config=AIConfig(),
    )

    result = await service.suggest_macros(
        SuggestMacrosCommand(
            ticket_public_id=uuid4(),
            subject="Не вижу платёж",
            status=TicketStatus.ASSIGNED,
            category_title=None,
            macros=(
                MacroCandidate(
                    id=1,
                    title="Сброс доступа",
                    body="Проверьте почту для сброса.",
                ),
                MacroCandidate(
                    id=2,
                    title="Проверка платежа",
                    body="Проверяем платёж и вернёмся с ответом.",
                ),
            ),
        )
    )

    assert tuple(item.macro_id for item in result.suggestions) == (2,)


async def test_predict_ticket_category_requires_medium_or_high_confidence() -> None:
    service = AIApplicationService(
        provider=StubProvider('{"category_id":2,"confidence":"low","reason":"Похоже на оплату"}'),
        config=AIConfig(),
    )

    result = await service.predict_ticket_category(
        AIPredictTicketCategoryCommand(
            text="Не вижу оплату",
            categories=(
                AICategoryOption(
                    id=2,
                    code="billing",
                    title="Оплата",
                ),
            ),
        )
    )

    assert result.available is False
    assert result.confidence is AIPredictionConfidence.NONE


async def test_analyze_ticket_sentiment_detects_escalation_risk_without_provider() -> None:
    service = AIApplicationService(
        provider=StubProvider("{}", enabled=False, model_id=None),
        config=AIConfig(),
    )

    result = await service.analyze_ticket_sentiment(
        AnalyzeTicketSentimentCommand(
            text="Это уже безобразие, сколько можно, верните деньги немедленно!!!"
        )
    )

    assert result.available is True
    assert result.sentiment is TicketSentiment.ESCALATION_RISK
    assert result.confidence in {
        TicketSignalConfidence.MEDIUM,
        TicketSignalConfidence.HIGH,
    }
