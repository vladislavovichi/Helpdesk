from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.contracts.actors import OperatorIdentity
from domain.entities.ticket import TicketAttachmentDetails


@dataclass(slots=True, frozen=True)
class ClientTicketMessageCommand:
    client_chat_id: int
    telegram_message_id: int
    text: str | None
    attachment: TicketAttachmentDetails | None = None
    category_id: int | None = None


@dataclass(slots=True, frozen=True)
class TicketAssignmentCommand:
    ticket_public_id: UUID
    operator: OperatorIdentity


@dataclass(slots=True, frozen=True)
class AssignNextQueuedTicketCommand:
    operator: OperatorIdentity
    prioritize_priority: bool = False


@dataclass(slots=True, frozen=True)
class OperatorTicketReplyCommand:
    ticket_public_id: UUID
    operator: OperatorIdentity
    telegram_message_id: int
    text: str | None
    attachment: TicketAttachmentDetails | None = None


@dataclass(slots=True, frozen=True)
class AddInternalNoteCommand:
    ticket_public_id: UUID
    author: OperatorIdentity
    text: str


@dataclass(slots=True, frozen=True)
class ApplyMacroToTicketCommand:
    ticket_public_id: UUID
    macro_id: int
    operator: OperatorIdentity
