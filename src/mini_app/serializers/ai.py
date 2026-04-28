from __future__ import annotations

from typing import Any

from application.ai.summaries import TicketAssistSnapshot, TicketReplyDraft
from mini_app.serializers.common import serialize_datetime


def serialize_ticket_ai_snapshot(snapshot: TicketAssistSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "available": snapshot.available,
        "unavailable_reason": snapshot.unavailable_reason,
        "model_id": snapshot.model_id,
        "short_summary": snapshot.short_summary,
        "user_goal": snapshot.user_goal,
        "actions_taken": snapshot.actions_taken,
        "current_status": snapshot.current_status,
        "summary_status": snapshot.summary_status.value,
        "summary_generated_at": serialize_datetime(snapshot.summary_generated_at),
        "status_note": snapshot.status_note,
        "macro_suggestions": [
            {
                "macro_id": item.macro_id,
                "title": item.title,
                "body": item.body,
                "reason": item.reason,
                "confidence": item.confidence.value,
            }
            for item in snapshot.macro_suggestions
        ],
    }


def serialize_ticket_reply_draft(draft: TicketReplyDraft | None) -> dict[str, Any] | None:
    if draft is None:
        return None
    return {
        "available": draft.available,
        "reply_text": draft.reply_text,
        "tone": draft.tone,
        "confidence": draft.confidence,
        "safety_note": draft.safety_note,
        "missing_information": (
            list(draft.missing_information) if draft.missing_information is not None else None
        ),
        "unavailable_reason": draft.unavailable_reason,
        "model_id": draft.model_id,
    }
