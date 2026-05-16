from __future__ import annotations

from typing import Protocol
from uuid import UUID

from application.contracts.tickets import ClientTicketMessageCommand
from application.errors import InternalApplicationError
from application.use_cases.tickets.common import (
    build_status_payload,
    build_ticket_summary,
)
from application.use_cases.tickets.message_content import build_ticket_subject
from application.use_cases.tickets.summaries import TicketSummary
from domain.contracts.repositories import (
    TicketEventRepository,
    TicketRepository,
)
from domain.entities.ticket import TicketAttachmentDetails
from domain.enums.tickets import TicketEventType, TicketMessageSenderType, TicketStatus


class AddMessageToTicketDependency(Protocol):
    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
        telegram_message_id: int,
        sender_type: TicketMessageSenderType,
        text: str | None,
        attachment: TicketAttachmentDetails | None = None,
    ) -> TicketSummary | None: ...


class CreateTicketFromClientMessageUseCase:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        ticket_event_repository: TicketEventRepository,
        add_message_to_ticket: AddMessageToTicketDependency,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_event_repository = ticket_event_repository
        self._add_message_to_ticket = add_message_to_ticket

    async def __call__(
        self,
        command: ClientTicketMessageCommand,
    ) -> TicketSummary:
        active_ticket = await self.ticket_repository.get_active_by_client_chat_id(
            command.client_chat_id
        )
        if active_ticket is not None:
            result = await self._add_message_to_ticket(
                ticket_public_id=active_ticket.public_id,
                telegram_message_id=command.telegram_message_id,
                sender_type=TicketMessageSenderType.CLIENT,
                text=command.text,
                attachment=command.attachment,
            )
            if result is None:
                raise InternalApplicationError("Не удалось добавить сообщение в активную заявку.")
            return result

        ticket = await self.ticket_repository.create(
            client_chat_id=command.client_chat_id,
            subject=build_ticket_subject(
                text=command.text,
                attachment=command.attachment,
            ),
            category_id=command.category_id,
        )
        if ticket.id is None:
            raise InternalApplicationError("Не удалось сгенерировать идентификатор заявки.")

        await self.ticket_event_repository.add(
            ticket_id=ticket.id,
            event_type=TicketEventType.CREATED,
            payload_json={
                "status": ticket.status.value,
                "subject": ticket.subject,
                "client_chat_id": ticket.client_chat_id,
                "category_id": command.category_id,
            },
        )

        queued_ticket = await self.ticket_repository.enqueue(ticket_public_id=ticket.public_id)
        if queued_ticket is None:
            raise InternalApplicationError("Не удалось поставить заявку в очередь.")

        await self.ticket_event_repository.add(
            ticket_id=ticket.id,
            event_type=TicketEventType.QUEUED,
            payload_json=build_status_payload(
                from_status=TicketStatus.NEW,
                to_status=queued_ticket.status,
                assigned_operator_id=queued_ticket.assigned_operator_id,
            ),
        )

        added_message = await self._add_message_to_ticket(
            ticket_public_id=ticket.public_id,
            telegram_message_id=command.telegram_message_id,
            sender_type=TicketMessageSenderType.CLIENT,
            text=command.text,
            attachment=command.attachment,
        )
        if added_message is None:
            raise InternalApplicationError("Не удалось сохранить первое сообщение заявки.")

        return build_ticket_summary(
            queued_ticket,
            created=True,
            event_type=TicketEventType.QUEUED,
        )


class GetActiveClientTicketUseCase:
    def __init__(self, ticket_repository: TicketRepository) -> None:
        self.ticket_repository = ticket_repository

    async def __call__(self, *, client_chat_id: int) -> TicketSummary | None:
        ticket = await self.ticket_repository.get_active_by_client_chat_id(client_chat_id)
        if ticket is None:
            return None
        return build_ticket_summary(ticket)
