from __future__ import annotations

from datetime import datetime
from typing import Any

from application.ai.summaries import TicketAssistSnapshot
from application.use_cases.tickets.summaries import TicketDetailsSummary
from domain.enums.tickets import TicketMessageSenderType
from mini_app.serializers.common import serialize_datetime


def serialize_ticket_timeline(
    ticket: TicketDetailsSummary | None,
    ai_snapshot: TicketAssistSnapshot | None = None,
) -> dict[str, Any]:
    if ticket is None:
        return {"items": [], "warning": "Ticket history is temporarily unavailable."}

    items: list[dict[str, Any]] = [
        _build_timeline_item(
            item_id="ticket-created",
            item_type="ticket_created",
            title="Ticket created",
            description=f"{ticket.public_number} was opened.",
            actor_label="Customer",
            created_at=ticket.created_at,
            metadata={
                "status": ticket.status.value,
                "priority": ticket.priority,
                "category": ticket.category_title,
            },
        )
    ]

    if ticket.assigned_operator_name:
        items.append(
            _build_timeline_item(
                item_id="ticket-current-assignment",
                item_type="ticket_assigned",
                title="Current assignment",
                description=f"Ticket is assigned to {ticket.assigned_operator_name}.",
                actor_label=ticket.assigned_operator_name,
                created_at=ticket.created_at,
                metadata={"derived": True},
            )
        )

    for index, message in enumerate(ticket.message_history, start=1):
        is_operator = message.sender_type == TicketMessageSenderType.OPERATOR
        has_attachment = message.attachment is not None
        text = _clip_timeline_text(message.text)
        if text is None and has_attachment:
            text = "Attachment added."
        items.append(
            _build_timeline_item(
                item_id=f"message-{index}",
                item_type="operator_reply" if is_operator else "message_received",
                title="Operator replied" if is_operator else "Customer message received",
                description=text or "Message without text.",
                actor_label=(
                    message.sender_operator_name
                    if is_operator and message.sender_operator_name
                    else ("Operator" if is_operator else "Customer")
                ),
                created_at=message.created_at,
                metadata=(
                    {
                        "attachment_kind": message.attachment.kind.value,
                        "attachment_filename": message.attachment.filename,
                    }
                    if has_attachment and message.attachment is not None
                    else None
                ),
            )
        )

    for note in ticket.internal_notes:
        items.append(
            _build_timeline_item(
                item_id=f"note-{note.id}",
                item_type="internal_note_added",
                title="Internal note added",
                description=_clip_timeline_text(note.text) or "Internal note added.",
                actor_label=note.author_operator_name or "Operator",
                created_at=note.created_at,
                metadata=None,
            )
        )

    if ai_snapshot is not None and ai_snapshot.summary_generated_at is not None:
        items.append(
            _build_timeline_item(
                item_id="ai-summary-generated",
                item_type="ai_summary_generated",
                title="AI summary generated",
                description=ai_snapshot.status_note or "AI assistance summary was generated.",
                actor_label="AI assistant",
                created_at=ai_snapshot.summary_generated_at,
                metadata={
                    "summary_status": ai_snapshot.summary_status.value,
                    "model_id": ai_snapshot.model_id,
                },
            )
        )

    if ticket.closed_at is not None:
        items.append(
            _build_timeline_item(
                item_id="ticket-closed",
                item_type="ticket_closed",
                title="Ticket closed",
                description=f"{ticket.public_number} was closed.",
                actor_label=ticket.assigned_operator_name or "Operator",
                created_at=ticket.closed_at,
                metadata={"status": "closed"},
            )
        )

    return {
        "items": sorted(items, key=lambda item: (item["created_at"] or "", item["id"])),
        "warning": None,
    }


def _build_timeline_item(
    *,
    item_id: str,
    item_type: str,
    title: str,
    description: str,
    actor_label: str | None,
    created_at: datetime | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": item_type,
        "title": title,
        "description": description,
        "actor_label": actor_label,
        "created_at": serialize_datetime(created_at),
        "metadata": _sanitize_timeline_metadata(metadata),
    }


def _clip_timeline_text(value: str | None, *, limit: int = 180) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _sanitize_timeline_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    safe = {
        key: value
        for key, value in metadata.items()
        if value is not None and isinstance(value, str | int | float | bool)
    }
    return safe or None
