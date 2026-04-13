# mypy: disable-error-code="attr-defined,name-defined"
from __future__ import annotations

from uuid import UUID

from application.contracts.ai import PredictTicketCategoryCommand
from application.contracts.tickets import (
    ApplyMacroToTicketCommand,
    AssignNextQueuedTicketCommand,
    ClientTicketMessageCommand,
    OperatorTicketReplyCommand,
    TicketAssignmentCommand,
)
from backend.grpc.generated import helpdesk_pb2
from backend.grpc.translators_shared import (
    _has,
    deserialize_attachment,
    deserialize_operator_identity,
    serialize_attachment,
    serialize_operator_identity,
)
from domain.enums.tickets import TicketAttachmentKind


def serialize_client_ticket_message_command(
    command: ClientTicketMessageCommand,
) -> helpdesk_pb2.ClientTicketMessageCommand:
    message = helpdesk_pb2.ClientTicketMessageCommand(
        client_chat_id=command.client_chat_id,
        telegram_message_id=command.telegram_message_id,
    )
    if command.text is not None:
        message.text = command.text
    if command.attachment is not None:
        message.attachment.CopyFrom(serialize_attachment(command.attachment))
    if command.category_id is not None:
        message.category_id = command.category_id
    return message


def deserialize_client_ticket_message_command(
    command: helpdesk_pb2.ClientTicketMessageCommand,
) -> ClientTicketMessageCommand:
    return ClientTicketMessageCommand(
        client_chat_id=command.client_chat_id,
        telegram_message_id=command.telegram_message_id,
        text=command.text if _has(command, "text") else None,
        attachment=(
            deserialize_attachment(command.attachment) if command.HasField("attachment") else None
        ),
        category_id=command.category_id if _has(command, "category_id") else None,
    )


def serialize_operator_reply_command(
    command: OperatorTicketReplyCommand,
) -> helpdesk_pb2.OperatorTicketReplyCommand:
    message = helpdesk_pb2.OperatorTicketReplyCommand(
        ticket_public_id=str(command.ticket_public_id),
        telegram_message_id=command.telegram_message_id,
    )
    message.operator.CopyFrom(serialize_operator_identity(command.operator))
    if command.text is not None:
        message.text = command.text
    if command.attachment is not None:
        message.attachment.CopyFrom(serialize_attachment(command.attachment))
    return message


def deserialize_operator_reply_command(
    command: helpdesk_pb2.OperatorTicketReplyCommand,
) -> OperatorTicketReplyCommand:
    return OperatorTicketReplyCommand(
        ticket_public_id=UUID(command.ticket_public_id),
        operator=deserialize_operator_identity(command.operator),
        telegram_message_id=command.telegram_message_id,
        text=command.text if _has(command, "text") else None,
        attachment=(
            deserialize_attachment(command.attachment) if command.HasField("attachment") else None
        ),
    )


def serialize_ticket_assignment_command(
    command: TicketAssignmentCommand,
) -> helpdesk_pb2.TicketAssignmentCommand:
    message = helpdesk_pb2.TicketAssignmentCommand(ticket_public_id=str(command.ticket_public_id))
    message.operator.CopyFrom(serialize_operator_identity(command.operator))
    return message


def deserialize_ticket_assignment_command(
    command: helpdesk_pb2.TicketAssignmentCommand,
) -> TicketAssignmentCommand:
    return TicketAssignmentCommand(
        ticket_public_id=UUID(command.ticket_public_id),
        operator=deserialize_operator_identity(command.operator),
    )


def serialize_assign_next_command(
    command: AssignNextQueuedTicketCommand,
) -> helpdesk_pb2.AssignNextQueuedTicketCommand:
    message = helpdesk_pb2.AssignNextQueuedTicketCommand(
        prioritize_priority=command.prioritize_priority
    )
    message.operator.CopyFrom(serialize_operator_identity(command.operator))
    return message


def deserialize_assign_next_command(
    command: helpdesk_pb2.AssignNextQueuedTicketCommand,
) -> AssignNextQueuedTicketCommand:
    return AssignNextQueuedTicketCommand(
        operator=deserialize_operator_identity(command.operator),
        prioritize_priority=command.prioritize_priority,
    )


def serialize_apply_macro_command(
    command: ApplyMacroToTicketCommand,
) -> helpdesk_pb2.ApplyMacroToTicketCommand:
    message = helpdesk_pb2.ApplyMacroToTicketCommand(
        ticket_public_id=str(command.ticket_public_id),
        macro_id=command.macro_id,
    )
    message.operator.CopyFrom(serialize_operator_identity(command.operator))
    return message


def deserialize_apply_macro_command(
    command: helpdesk_pb2.ApplyMacroToTicketCommand,
) -> ApplyMacroToTicketCommand:
    return ApplyMacroToTicketCommand(
        ticket_public_id=UUID(command.ticket_public_id),
        macro_id=command.macro_id,
        operator=deserialize_operator_identity(command.operator),
    )


def serialize_predict_ticket_category_command(
    command: PredictTicketCategoryCommand,
) -> helpdesk_pb2.PredictTicketCategoryCommand:
    message = helpdesk_pb2.PredictTicketCategoryCommand()
    if command.text is not None:
        message.text = command.text
    if command.attachment_kind is not None:
        message.attachment_kind = command.attachment_kind.value
    if command.attachment_filename is not None:
        message.attachment_filename = command.attachment_filename
    if command.attachment_mime_type is not None:
        message.attachment_mime_type = command.attachment_mime_type
    return message


def deserialize_predict_ticket_category_command(
    command: helpdesk_pb2.PredictTicketCategoryCommand,
) -> PredictTicketCategoryCommand:
    return PredictTicketCategoryCommand(
        text=command.text if _has(command, "text") else None,
        attachment_kind=TicketAttachmentKind(command.attachment_kind)
        if _has(command, "attachment_kind")
        else None,
        attachment_filename=(
            command.attachment_filename if _has(command, "attachment_filename") else None
        ),
        attachment_mime_type=(
            command.attachment_mime_type if _has(command, "attachment_mime_type") else None
        ),
    )
