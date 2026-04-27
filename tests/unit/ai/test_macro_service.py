from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider
from application.contracts.ai import AIContextMessage, MacroCandidate, SuggestMacrosCommand
from domain.enums.tickets import TicketMessageSenderType, TicketStatus
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
            message_history=(
                AIContextMessage(
                    sender_type=TicketMessageSenderType.CLIENT,
                    sender_label=None,
                    text="Не вижу оплату после платежа.",
                    created_at=datetime(2026, 4, 20, 10, 0, tzinfo=UTC),
                ),
            ),
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
