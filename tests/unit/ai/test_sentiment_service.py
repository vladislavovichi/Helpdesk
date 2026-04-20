from __future__ import annotations

from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider
from application.contracts.ai import AnalyzeTicketSentimentCommand
from domain.enums.tickets import TicketSentiment, TicketSignalConfidence
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
