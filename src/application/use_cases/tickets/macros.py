from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from application.use_cases.tickets.messaging import AddMessageToTicketUseCase
from application.use_cases.tickets.summaries import (
    MacroApplicationResult,
    MacroManagementError,
    MacroSummary,
)
from domain.contracts.repositories import (
    MacroRepository,
    OperatorRepository,
    TicketEventRepository,
    TicketMessageRepository,
    TicketRepository,
)
from domain.enums.tickets import TicketMessageSenderType
from domain.tickets import InvalidTicketTransitionError, ensure_operator_replyable


class ListMacrosUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self) -> Sequence[MacroSummary]:
        macros = await self.macro_repository.list_all()
        return [MacroSummary(id=macro.id, title=macro.title, body=macro.body) for macro in macros]


class GetMacroUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self, *, macro_id: int) -> MacroSummary | None:
        macro = await self.macro_repository.get_by_id(macro_id=macro_id)
        if macro is None:
            return None
        return MacroSummary(id=macro.id, title=macro.title, body=macro.body)


class CreateMacroUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self, *, title: str, body: str) -> MacroSummary:
        normalized_title = _normalize_macro_title(title)
        normalized_body = _normalize_macro_body(body)

        existing = await self.macro_repository.get_by_title(title=normalized_title)
        if existing is not None:
            raise MacroManagementError("Макрос с таким названием уже есть.")

        macro = await self.macro_repository.create(
            title=normalized_title,
            body=normalized_body,
        )
        return MacroSummary(id=macro.id, title=macro.title, body=macro.body)


class UpdateMacroTitleUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self, *, macro_id: int, title: str) -> MacroSummary | None:
        normalized_title = _normalize_macro_title(title)
        existing = await self.macro_repository.get_by_title(title=normalized_title)
        if existing is not None and existing.id != macro_id:
            raise MacroManagementError("Макрос с таким названием уже есть.")

        macro = await self.macro_repository.update_title(
            macro_id=macro_id,
            title=normalized_title,
        )
        if macro is None:
            return None
        return MacroSummary(id=macro.id, title=macro.title, body=macro.body)


class UpdateMacroBodyUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self, *, macro_id: int, body: str) -> MacroSummary | None:
        macro = await self.macro_repository.update_body(
            macro_id=macro_id,
            body=_normalize_macro_body(body),
        )
        if macro is None:
            return None
        return MacroSummary(id=macro.id, title=macro.title, body=macro.body)


class DeleteMacroUseCase:
    def __init__(self, macro_repository: MacroRepository) -> None:
        self.macro_repository = macro_repository

    async def __call__(self, *, macro_id: int) -> MacroSummary | None:
        macro = await self.macro_repository.delete(macro_id=macro_id)
        if macro is None:
            return None
        return MacroSummary(id=macro.id, title=macro.title, body=macro.body)


class ApplyMacroToTicketUseCase:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        ticket_message_repository: TicketMessageRepository,
        ticket_event_repository: TicketEventRepository,
        operator_repository: OperatorRepository,
        macro_repository: MacroRepository,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_message_repository = ticket_message_repository
        self.operator_repository = operator_repository
        self.macro_repository = macro_repository
        self._add_message_to_ticket = AddMessageToTicketUseCase(
            ticket_repository=ticket_repository,
            ticket_message_repository=ticket_message_repository,
            ticket_event_repository=ticket_event_repository,
        )

    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
        macro_id: int,
        telegram_user_id: int,
        display_name: str,
        username: str | None,
    ) -> MacroApplicationResult | None:
        ticket_details = await self.ticket_repository.get_details_by_public_id(ticket_public_id)
        if ticket_details is None:
            return None

        macro = await self.macro_repository.get_by_id(macro_id=macro_id)
        if macro is None:
            return None

        ensure_operator_replyable(ticket_details.status)

        operator_id = await self.operator_repository.get_or_create(
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        if (
            ticket_details.assigned_operator_id is not None
            and ticket_details.assigned_operator_id != operator_id
        ):
            raise InvalidTicketTransitionError("С этой заявкой уже работает другой оператор.")

        telegram_message_id = (
            await self.ticket_message_repository.allocate_internal_telegram_message_id(
                ticket_id=ticket_details.id,
                sender_type=TicketMessageSenderType.OPERATOR,
            )
        )
        ticket = await self._add_message_to_ticket(
            ticket_public_id=ticket_public_id,
            telegram_message_id=telegram_message_id,
            sender_type=TicketMessageSenderType.OPERATOR,
            text=macro.body,
            sender_operator_id=operator_id,
            extra_event_payload={
                "macro_id": macro.id,
                "macro_title": macro.title,
            },
        )
        if ticket is None:
            return None

        return MacroApplicationResult(
            ticket=ticket,
            client_chat_id=ticket_details.client_chat_id,
            macro=MacroSummary(id=macro.id, title=macro.title, body=macro.body),
        )


def _normalize_macro_title(title: str) -> str:
    normalized = " ".join(title.strip().split())
    if not normalized:
        raise MacroManagementError("Название макроса не должно быть пустым.")
    return normalized[:150]


def _normalize_macro_body(body: str) -> str:
    normalized = body.strip()
    if not normalized:
        raise MacroManagementError("Текст макроса не должен быть пустым.")
    return normalized
