from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from uuid import UUID

from domain.contracts.repositories import (
    OperatorRepository,
    TagRepository,
    TicketMessageRepository,
    TicketRepository,
)
from domain.enums.tickets import TicketMessageSenderType
from application.use_cases.tickets import (
    AddMessageToTicketUseCase,
    AssignTicketToOperatorUseCase,
    BasicStatsUseCase,
    CloseTicketUseCase,
    CreateTicketFromClientMessageUseCase,
    TicketStats,
    TicketSummary,
    format_public_ticket_number,
)

HelpdeskServiceFactory = Callable[[], AbstractAsyncContextManager["HelpdeskService"]]


@dataclass(slots=True)
class HelpdeskService:
    ticket_repository: TicketRepository
    ticket_message_repository: TicketMessageRepository
    operator_repository: OperatorRepository
    tag_repository: TagRepository

    async def create_ticket_from_client_message(
        self,
        *,
        client_chat_id: int,
        telegram_message_id: int,
        text: str,
    ) -> TicketSummary:
        use_case = CreateTicketFromClientMessageUseCase(
            ticket_repository=self.ticket_repository,
            ticket_message_repository=self.ticket_message_repository,
        )
        return await use_case(
            client_chat_id=client_chat_id,
            telegram_message_id=telegram_message_id,
            text=text,
        )

    async def add_message_to_ticket(
        self,
        *,
        ticket_public_id: UUID,
        telegram_message_id: int,
        sender_type: TicketMessageSenderType,
        text: str,
        sender_operator_id: int | None = None,
    ) -> TicketSummary | None:
        use_case = AddMessageToTicketUseCase(
            ticket_repository=self.ticket_repository,
            ticket_message_repository=self.ticket_message_repository,
        )
        return await use_case(
            ticket_public_id=ticket_public_id,
            telegram_message_id=telegram_message_id,
            sender_type=sender_type,
            text=text,
            sender_operator_id=sender_operator_id,
        )

    async def assign_ticket_to_operator(
        self,
        *,
        ticket_public_id: UUID,
        telegram_user_id: int,
        display_name: str,
        username: str | None = None,
    ) -> TicketSummary | None:
        use_case = AssignTicketToOperatorUseCase(
            ticket_repository=self.ticket_repository,
            operator_repository=self.operator_repository,
        )
        return await use_case(
            ticket_public_id=ticket_public_id,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )

    async def close_ticket(self, *, ticket_public_id: UUID) -> TicketSummary | None:
        use_case = CloseTicketUseCase(ticket_repository=self.ticket_repository)
        return await use_case(ticket_public_id=ticket_public_id)

    async def get_basic_stats(self) -> TicketStats:
        use_case = BasicStatsUseCase(ticket_repository=self.ticket_repository)
        return await use_case()

    async def acknowledge_reply_action(self, *, ticket_public_id: UUID) -> str:
        ticket = await self.ticket_repository.get_by_public_id(ticket_public_id)
        if ticket is None:
            return "Ticket not found."

        return (
            f"Reply flow for ticket {format_public_ticket_number(ticket.public_id)} "
            "is not implemented yet."
        )

    async def acknowledge_escalate_action(self, *, ticket_public_id: UUID) -> str:
        ticket = await self.ticket_repository.get_by_public_id(ticket_public_id)
        if ticket is None:
            return "Ticket not found."

        return (
            f"Escalation flow for ticket {format_public_ticket_number(ticket.public_id)} "
            "is not implemented yet."
        )
