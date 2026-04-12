from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from application.ai.contracts import AIMessage, AIProvider
from application.ai.summaries import AIPredictionConfidence
from application.contracts.ai import PredictTicketCategoryCommand
from application.use_cases.ai.assist import (
    AIGenerationProfile,
    BuildTicketAssistSnapshotUseCase,
    PredictTicketCategoryUseCase,
)
from domain.contracts.repositories import (
    MacroRepository,
    TicketCategoryRepository,
    TicketRepository,
)
from domain.entities.ticket import (
    TicketDetails,
    TicketInternalNoteDetails,
    TicketMessageDetails,
)
from domain.enums.tickets import TicketMessageSenderType, TicketPriority, TicketStatus


class StubAIProvider(AIProvider):
    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)

    @property
    def is_enabled(self) -> bool:
        return True

    @property
    def model_id(self) -> str | None:
        return "Qwen/Qwen3.5-4B"

    async def complete(
        self,
        *,
        messages: Sequence[AIMessage],
        max_output_tokens: int,
        temperature: float,
    ) -> str:
        del messages, max_output_tokens, temperature
        if not self._responses:
            raise RuntimeError("No more stub responses configured.")
        return self._responses.pop(0)


class StubTicketRepository:
    def __init__(self, ticket: TicketDetails | None) -> None:
        self.ticket = ticket

    async def get_details_by_public_id(self, public_id: object) -> TicketDetails | None:
        del public_id
        return self.ticket


class StubMacroRepository:
    async def list_all(self) -> tuple[SimpleNamespace, ...]:
        return (
            SimpleNamespace(
                id=1,
                title="Сброс доступа",
                body="Сбросили пароль и обновили ссылку.",
            ),
            SimpleNamespace(
                id=2,
                title="Проверка платежа",
                body="Проверяем платёж и возвращаемся.",
            ),
        )


class StubCategoryRepository:
    async def list_all(self, *, include_inactive: bool = True) -> tuple[SimpleNamespace, ...]:
        assert include_inactive is False
        return (
            SimpleNamespace(
                id=1,
                code="access",
                title="Доступ и вход",
                is_active=True,
                sort_order=10,
            ),
            SimpleNamespace(
                id=2,
                code="billing",
                title="Оплата и баланс",
                is_active=True,
                sort_order=20,
            ),
        )


def _build_ticket() -> TicketDetails:
    return TicketDetails(
        id=1,
        public_id=uuid4(),
        client_chat_id=2002,
        status=TicketStatus.ASSIGNED,
        priority=TicketPriority.NORMAL,
        subject="Не могу войти в кабинет после смены пароля",
        assigned_operator_id=7,
        assigned_operator_name="Иван Петров",
        assigned_operator_telegram_user_id=1001,
        created_at=datetime(2026, 4, 12, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 12, 10, 15, tzinfo=UTC),
        first_response_at=datetime(2026, 4, 12, 10, 5, tzinfo=UTC),
        closed_at=None,
        category_id=1,
        category_code="access",
        category_title="Доступ и вход",
        tags=("vip",),
        message_history=(
            TicketMessageDetails(
                telegram_message_id=1,
                sender_type=TicketMessageSenderType.CLIENT,
                sender_operator_id=None,
                sender_operator_name=None,
                text="После смены пароля кабинет пишет, что логин недействителен.",
                created_at=datetime(2026, 4, 12, 10, 1, tzinfo=UTC),
            ),
            TicketMessageDetails(
                telegram_message_id=2,
                sender_type=TicketMessageSenderType.OPERATOR,
                sender_operator_id=7,
                sender_operator_name="Иван Петров",
                text="Проверяем профиль и готовим сброс доступа.",
                created_at=datetime(2026, 4, 12, 10, 5, tzinfo=UTC),
            ),
        ),
        internal_notes=(
            TicketInternalNoteDetails(
                id=1,
                author_operator_id=7,
                author_operator_name="Иван Петров",
                text="Похоже на рассинхрон после смены пароля в legacy-форме.",
                created_at=datetime(2026, 4, 12, 10, 8, tzinfo=UTC),
            ),
        ),
    )


async def test_build_ticket_assist_snapshot_returns_summary_and_macro_suggestions() -> None:
    use_case = BuildTicketAssistSnapshotUseCase(
        ticket_repository=cast(TicketRepository, StubTicketRepository(_build_ticket())),
        macro_repository=cast(MacroRepository, StubMacroRepository()),
        ai_provider=StubAIProvider(
            (
                '{"short_summary":"Клиент потерял доступ после смены пароля.",'
                '"user_goal":"Восстановить вход без повторной регистрации.",'
                '"actions_taken":"Оператор проверил профиль и готовит сброс.",'
                '"current_status":"Ожидается финальное подтверждение после сброса."}'
            ),
            '{"macro_ids":[{"macro_id":1,"reason":"Нужен готовый ответ про сброс доступа."}]}',
        ),
        profile=AIGenerationProfile(),
    )

    snapshot = await use_case(ticket_public_id=uuid4())

    assert snapshot is not None
    assert snapshot.available is True
    assert snapshot.short_summary == "Клиент потерял доступ после смены пароля."
    assert snapshot.macro_suggestions[0].macro_id == 1
    assert snapshot.model_id == "Qwen/Qwen3.5-4B"


async def test_predict_ticket_category_returns_valid_prediction() -> None:
    use_case = PredictTicketCategoryUseCase(
        ticket_category_repository=cast(TicketCategoryRepository, StubCategoryRepository()),
        ai_provider=StubAIProvider(
            '{"category_id":1,"confidence":"high",'
            '"reason":"Есть явные признаки проблемы со входом."}'
        ),
        profile=AIGenerationProfile(),
    )

    prediction = await use_case(
        PredictTicketCategoryCommand(
            text="Не могу войти после смены пароля",
        )
    )

    assert prediction.available is True
    assert prediction.category_id == 1
    assert prediction.category_title == "Доступ и вход"
    assert prediction.confidence == AIPredictionConfidence.HIGH
