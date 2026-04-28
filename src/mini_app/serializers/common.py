from __future__ import annotations

from datetime import datetime
from typing import Any

from application.use_cases.tickets.summaries import TicketAttachmentSummary


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def serialize_attachment(attachment: TicketAttachmentSummary | None) -> dict[str, Any] | None:
    if attachment is None:
        return None
    return {
        "kind": attachment.kind.value,
        "telegram_file_id": attachment.telegram_file_id,
        "telegram_file_unique_id": attachment.telegram_file_unique_id,
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "storage_path": attachment.storage_path,
    }


def normalize_bot_username(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().removeprefix("@").strip()
    return normalized or None
