# mypy: disable-error-code="attr-defined,name-defined"
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from google.protobuf.timestamp_pb2 import Timestamp

from application.contracts.actors import OperatorIdentity, RequestActor
from application.use_cases.tickets.summaries import TicketAttachmentSummary
from backend.grpc.generated import helpdesk_pb2
from domain.entities.ticket import TicketAttachmentDetails
from domain.enums.tickets import TicketAttachmentKind


def serialize_request_actor(actor: RequestActor) -> helpdesk_pb2.RequestActor:
    return helpdesk_pb2.RequestActor(telegram_user_id=actor.telegram_user_id)


def deserialize_request_actor(actor: helpdesk_pb2.RequestActor | None) -> RequestActor | None:
    if actor is None:
        return None
    return RequestActor(telegram_user_id=actor.telegram_user_id)


def serialize_operator_identity(operator: OperatorIdentity) -> helpdesk_pb2.OperatorIdentity:
    message = helpdesk_pb2.OperatorIdentity(
        telegram_user_id=operator.telegram_user_id,
        display_name=operator.display_name,
    )
    if operator.username is not None:
        message.username = operator.username
    return message


def deserialize_operator_identity(operator: helpdesk_pb2.OperatorIdentity) -> OperatorIdentity:
    return OperatorIdentity(
        telegram_user_id=operator.telegram_user_id,
        display_name=operator.display_name,
        username=operator.username if _has(operator, "username") else None,
    )


def serialize_attachment(
    attachment: TicketAttachmentDetails | TicketAttachmentSummary | None,
) -> helpdesk_pb2.TicketAttachment | None:
    if attachment is None:
        return None

    message = helpdesk_pb2.TicketAttachment(
        kind=attachment.kind.value,
        telegram_file_id=attachment.telegram_file_id,
    )
    if attachment.telegram_file_unique_id is not None:
        message.telegram_file_unique_id = attachment.telegram_file_unique_id
    if attachment.filename is not None:
        message.filename = attachment.filename
    if attachment.mime_type is not None:
        message.mime_type = attachment.mime_type
    if attachment.storage_path is not None:
        message.storage_path = attachment.storage_path
    return message


def deserialize_attachment(
    attachment: helpdesk_pb2.TicketAttachment | None,
) -> TicketAttachmentDetails | None:
    if attachment is None:
        return None

    return TicketAttachmentDetails(
        kind=TicketAttachmentKind(attachment.kind),
        telegram_file_id=attachment.telegram_file_id,
        telegram_file_unique_id=(
            attachment.telegram_file_unique_id
            if _has(attachment, "telegram_file_unique_id")
            else None
        ),
        filename=attachment.filename if _has(attachment, "filename") else None,
        mime_type=attachment.mime_type if _has(attachment, "mime_type") else None,
        storage_path=attachment.storage_path if _has(attachment, "storage_path") else None,
    )


def _deserialize_attachment_summary(
    attachment: helpdesk_pb2.TicketAttachment,
) -> TicketAttachmentSummary:
    return TicketAttachmentSummary(
        kind=TicketAttachmentKind(attachment.kind),
        telegram_file_id=attachment.telegram_file_id,
        telegram_file_unique_id=(
            attachment.telegram_file_unique_id
            if _has(attachment, "telegram_file_unique_id")
            else None
        ),
        filename=attachment.filename if _has(attachment, "filename") else None,
        mime_type=attachment.mime_type if _has(attachment, "mime_type") else None,
        storage_path=attachment.storage_path if _has(attachment, "storage_path") else None,
    )


def _serialize_timestamp(value: datetime) -> Timestamp:
    message = Timestamp()
    message.FromDatetime(value.astimezone(UTC))
    return message


def _deserialize_timestamp(value: Timestamp) -> datetime:
    return datetime.fromtimestamp(value.ToMilliseconds() / 1000, tz=UTC)


def _has(message: Any, field: str) -> bool:
    return bool(message.HasField(field))
