from __future__ import annotations

from datetime import datetime
from typing import Any

from application.use_cases.tickets.summaries import (
    HistoricalTicketSummary,
    MacroSummary,
    OperatorTicketSummary,
    QueuedTicketSummary,
    TicketDetailsSummary,
)
from domain.enums.tickets import TicketMessageSenderType, TicketSentiment
from mini_app.serializers.common import serialize_attachment, serialize_datetime


def serialize_queue_ticket(ticket: QueuedTicketSummary) -> dict[str, Any]:
    return {
        "public_id": str(ticket.public_id),
        "public_number": ticket.public_number,
        "subject": ticket.subject,
        "priority": ticket.priority,
        "status": ticket.status.value,
        "category_title": ticket.category_title,
    }


def serialize_operator_ticket(ticket: OperatorTicketSummary) -> dict[str, Any]:
    return {
        "public_id": str(ticket.public_id),
        "public_number": ticket.public_number,
        "subject": ticket.subject,
        "priority": ticket.priority,
        "status": ticket.status.value,
        "category_title": ticket.category_title,
    }


def serialize_dashboard_ticket_preview(
    ticket: TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary,
) -> dict[str, Any]:
    return {
        "public_id": str(ticket.public_id),
        "public_number": ticket.public_number,
        "subject": ticket.subject,
        "status": ticket.status.value,
        "priority": getattr(ticket, "priority", None),
        "category": getattr(ticket, "category_title", None),
        "category_title": getattr(ticket, "category_title", None),
        "assigned_operator": _serialize_assigned_operator(ticket),
        "last_activity_at": serialize_datetime(_resolve_ticket_last_activity(ticket)),
        "sla_state": _serialize_sla_state(ticket),
        "sentiment": _serialize_ticket_sentiment(ticket),
        "last_message_sender_type": (
            ticket.last_message_sender_type.value
            if isinstance(ticket, TicketDetailsSummary) and ticket.last_message_sender_type
            else None
        ),
    }


def serialize_dashboard_bucket(
    *,
    key: str,
    label: str,
    tickets: list[TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary],
    route: str,
    severity: str = "neutral",
    empty_label: str = "Сейчас пусто.",
    unavailable_reason: str | None = None,
    preview_limit: int = 5,
) -> dict[str, Any]:
    sorted_tickets = sorted(tickets, key=_ticket_activity_sort_value, reverse=True)
    return {
        "key": key,
        "label": label,
        "count": len(tickets),
        "tickets": [
            serialize_dashboard_ticket_preview(ticket) for ticket in sorted_tickets[:preview_limit]
        ],
        "route": route,
        "severity": severity,
        "empty_label": empty_label,
        "unavailable_reason": unavailable_reason,
    }


def is_negative_dashboard_sentiment(ticket: TicketDetailsSummary | object) -> bool:
    return getattr(ticket, "sentiment", None) in {
        TicketSentiment.FRUSTRATED,
        TicketSentiment.ESCALATION_RISK,
    }


def needs_operator_reply(ticket: TicketDetailsSummary | object) -> bool:
    if not isinstance(ticket, TicketDetailsSummary):
        return False
    if ticket.last_message_sender_type == TicketMessageSenderType.CLIENT:
        return True
    return not any(
        message.sender_type == TicketMessageSenderType.OPERATOR
        for message in ticket.message_history
    )


def serialize_archived_ticket(ticket: HistoricalTicketSummary) -> dict[str, Any]:
    return {
        "public_id": str(ticket.public_id),
        "public_number": ticket.public_number,
        "status": ticket.status.value,
        "created_at": serialize_datetime(ticket.created_at),
        "closed_at": serialize_datetime(ticket.closed_at),
        "mini_title": ticket.mini_title,
        "category_id": ticket.category_id,
        "category_code": ticket.category_code,
        "category_title": ticket.category_title,
    }


def serialize_ticket_details(ticket: TicketDetailsSummary) -> dict[str, Any]:
    return {
        "public_id": str(ticket.public_id),
        "public_number": ticket.public_number,
        "client_chat_id": ticket.client_chat_id,
        "status": ticket.status.value,
        "priority": ticket.priority,
        "subject": ticket.subject,
        "assigned_operator_id": ticket.assigned_operator_id,
        "assigned_operator_name": ticket.assigned_operator_name,
        "assigned_operator_telegram_user_id": ticket.assigned_operator_telegram_user_id,
        "assigned_operator_username": ticket.assigned_operator_username,
        "created_at": serialize_datetime(ticket.created_at),
        "closed_at": serialize_datetime(ticket.closed_at),
        "category_id": ticket.category_id,
        "category_code": ticket.category_code,
        "category_title": ticket.category_title,
        "sentiment": ticket.sentiment.value if ticket.sentiment is not None else None,
        "sentiment_confidence": (
            ticket.sentiment_confidence.value if ticket.sentiment_confidence is not None else None
        ),
        "sentiment_reason": ticket.sentiment_reason,
        "sentiment_detected_at": serialize_datetime(ticket.sentiment_detected_at),
        "tags": list(ticket.tags),
        "last_message_text": ticket.last_message_text,
        "last_message_sender_type": (
            ticket.last_message_sender_type.value if ticket.last_message_sender_type else None
        ),
        "last_message_attachment": serialize_attachment(ticket.last_message_attachment),
        "message_history": [
            {
                "sender_type": message.sender_type.value,
                "sender_operator_id": message.sender_operator_id,
                "sender_operator_name": message.sender_operator_name,
                "text": message.text,
                "created_at": serialize_datetime(message.created_at),
                "attachment": serialize_attachment(message.attachment),
                "sentiment": message.sentiment.value if message.sentiment else None,
                "sentiment_confidence": (
                    message.sentiment_confidence.value
                    if message.sentiment_confidence is not None
                    else None
                ),
                "sentiment_reason": message.sentiment_reason,
                "duplicate_count": message.duplicate_count,
                "last_duplicate_at": serialize_datetime(message.last_duplicate_at),
            }
            for message in ticket.message_history
        ],
        "internal_notes": [
            {
                "id": note.id,
                "author_operator_id": note.author_operator_id,
                "author_operator_name": note.author_operator_name,
                "text": note.text,
                "created_at": serialize_datetime(note.created_at),
            }
            for note in ticket.internal_notes
        ],
    }


def serialize_macro(macro: MacroSummary) -> dict[str, Any]:
    return {
        "id": macro.id,
        "title": macro.title,
        "body": macro.body,
    }


def _resolve_ticket_last_activity(
    ticket: TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary,
) -> datetime | None:
    if not isinstance(ticket, TicketDetailsSummary):
        return None
    candidates = [ticket.created_at, ticket.closed_at, ticket.sentiment_detected_at]
    candidates.extend(message.created_at for message in ticket.message_history)
    candidates.extend(note.created_at for note in ticket.internal_notes)
    return max((item for item in candidates if item is not None), default=None)


def _ticket_activity_sort_value(
    ticket: TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary,
) -> float:
    last_activity = _resolve_ticket_last_activity(ticket)
    if last_activity is None:
        return 0.0
    return last_activity.timestamp()


def _serialize_assigned_operator(
    ticket: TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary,
) -> dict[str, Any] | None:
    if not isinstance(ticket, TicketDetailsSummary):
        return None
    if ticket.assigned_operator_id is None and ticket.assigned_operator_name is None:
        return None
    return {
        "id": ticket.assigned_operator_id,
        "name": ticket.assigned_operator_name,
        "telegram_user_id": ticket.assigned_operator_telegram_user_id,
        "username": ticket.assigned_operator_username,
    }


def _serialize_ticket_sentiment(
    ticket: TicketDetailsSummary | QueuedTicketSummary | OperatorTicketSummary,
) -> dict[str, Any] | None:
    if not isinstance(ticket, TicketDetailsSummary) or ticket.sentiment is None:
        return None
    return {
        "value": ticket.sentiment.value,
        "confidence": (
            ticket.sentiment_confidence.value if ticket.sentiment_confidence is not None else None
        ),
        "reason": ticket.sentiment_reason,
        "detected_at": serialize_datetime(ticket.sentiment_detected_at),
    }


def _serialize_sla_state(ticket: object) -> dict[str, Any] | None:
    state = getattr(ticket, "sla_state", None)
    if isinstance(state, dict):
        return state
    if isinstance(state, str):
        return {"status": state}
    return None
