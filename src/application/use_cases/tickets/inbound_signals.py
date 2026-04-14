from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from application.contracts.ai import AIContextAttachment, AIContextMessage
from domain.entities.ticket import TicketAttachmentDetails, TicketMessageDetails
from domain.enums.tickets import (
    TicketAttachmentKind,
    TicketMessageSenderType,
    TicketPriority,
    TicketSentiment,
)

_DUPLICATE_WINDOW = timedelta(minutes=3)
_PUNCTUATION_ONLY_RE = re.compile(r"^[\W_]+$", re.UNICODE)
_REPEATED_PUNCTUATION_RE = re.compile(r"([!?.,])\1+")


@dataclass(slots=True, frozen=True)
class DuplicateMessageDecision:
    canonical_message: TicketMessageDetails
    reason_code: str


def detect_duplicate_client_message(
    *,
    recent_messages: tuple[TicketMessageDetails, ...],
    incoming_text: str | None,
    incoming_attachment: TicketAttachmentDetails | None,
    current_time: datetime,
) -> DuplicateMessageDecision | None:
    if not recent_messages:
        return None

    candidate = recent_messages[-1]
    if candidate.sender_type != TicketMessageSenderType.CLIENT:
        return None
    if current_time - candidate.created_at > _DUPLICATE_WINDOW:
        return None

    candidate_text_signature = _build_text_signature(candidate.text)
    incoming_text_signature = _build_text_signature(incoming_text)
    candidate_attachment_signature = _build_attachment_signature(candidate.attachment)
    incoming_attachment_signature = _build_attachment_signature(incoming_attachment)

    if (
        candidate_text_signature is not None
        and incoming_text_signature is not None
        and candidate_text_signature == incoming_text_signature
        and candidate_attachment_signature == incoming_attachment_signature
    ):
        return DuplicateMessageDecision(
            canonical_message=candidate,
            reason_code="exact_text",
        )

    if (
        candidate_attachment_signature is not None
        and incoming_attachment_signature is not None
        and candidate_attachment_signature == incoming_attachment_signature
        and _normalize_text(candidate.text) == _normalize_text(incoming_text)
    ):
        return DuplicateMessageDecision(
            canonical_message=candidate,
            reason_code="exact_attachment",
        )

    if (
        incoming_attachment_signature is None
        and candidate_attachment_signature is None
        and _punctuation_signature(candidate.text) is not None
        and _punctuation_signature(candidate.text) == _punctuation_signature(incoming_text)
    ):
        return DuplicateMessageDecision(
            canonical_message=candidate,
            reason_code="punctuation_burst",
        )

    return None


def build_recent_ai_message_context(
    *,
    recent_messages: tuple[TicketMessageDetails, ...],
    limit: int = 5,
) -> tuple[AIContextMessage, ...]:
    return tuple(_build_ai_context_message(message) for message in recent_messages[-limit:])


def next_priority_for_sentiment(
    *,
    current_priority: TicketPriority,
    sentiment: TicketSentiment,
) -> TicketPriority | None:
    if sentiment != TicketSentiment.ESCALATION_RISK:
        return None
    if current_priority in {TicketPriority.HIGH, TicketPriority.URGENT}:
        return None
    return TicketPriority.HIGH


def sentiment_severity(sentiment: TicketSentiment | None) -> int:
    if sentiment == TicketSentiment.ESCALATION_RISK:
        return 2
    if sentiment == TicketSentiment.FRUSTRATED:
        return 1
    return 0


def format_duplicate_note(*, duplicate_count: int) -> str | None:
    if duplicate_count <= 0:
        return None
    if duplicate_count == 1:
        return "Повторено ещё 1 раз"
    if duplicate_count < 5:
        return f"Повторено ещё {duplicate_count} раза"
    return f"Повторено ещё {duplicate_count} раз"


def _build_ai_context_message(message: TicketMessageDetails) -> AIContextMessage:
    return AIContextMessage(
        sender_type=message.sender_type,
        sender_label=message.sender_operator_name,
        text=message.text,
        created_at=message.created_at,
        attachment=(
            AIContextAttachment(
                kind=message.attachment.kind,
                filename=message.attachment.filename,
                mime_type=message.attachment.mime_type,
            )
            if message.attachment is not None
            else None
        ),
    )


def _build_text_signature(text: str | None) -> str | None:
    normalized = _normalize_text(text)
    if normalized is None:
        return None
    if _PUNCTUATION_ONLY_RE.match(normalized):
        return _punctuation_signature(normalized)
    return normalized.casefold()


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = " ".join(text.replace("\u00a0", " ").split())
    return normalized or None


def _punctuation_signature(text: str | None) -> str | None:
    normalized = _normalize_text(text)
    if normalized is None or not _PUNCTUATION_ONLY_RE.match(normalized):
        return None
    return _REPEATED_PUNCTUATION_RE.sub(r"\1", normalized)


def _build_attachment_signature(
    attachment: TicketAttachmentDetails | None,
) -> tuple[TicketAttachmentKind, str] | None:
    if attachment is None:
        return None
    fingerprint = (
        attachment.telegram_file_unique_id or attachment.storage_path or attachment.telegram_file_id
    )
    if not fingerprint:
        return None
    return attachment.kind, fingerprint
