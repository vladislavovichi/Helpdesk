from __future__ import annotations

from uuid import uuid4

from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider
from application.contracts.ai import GenerateTicketSummaryCommand
from domain.enums.tickets import TicketStatus
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
