from __future__ import annotations

from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider
from application.ai.summaries import AIPredictionConfidence
from application.contracts.ai import AICategoryOption, AIPredictTicketCategoryCommand
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
