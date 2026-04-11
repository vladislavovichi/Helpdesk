from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO

from application.use_cases.tickets.exports import TicketReport

FIELDNAMES = (
    "ticket_public_number",
    "ticket_public_id",
    "ticket_status",
    "ticket_priority",
    "ticket_subject",
    "ticket_category_code",
    "ticket_category_title",
    "ticket_created_at",
    "ticket_updated_at",
    "ticket_first_response_at",
    "ticket_first_response_seconds",
    "ticket_closed_at",
    "ticket_assigned_operator_id",
    "ticket_assigned_operator_name",
    "ticket_assigned_operator_telegram_user_id",
    "ticket_client_chat_id",
    "ticket_tags",
    "feedback_rating",
    "feedback_comment",
    "feedback_submitted_at",
    "record_type",
    "record_sequence",
    "record_timestamp",
    "transcript_index",
    "transcript_timestamp",
    "transcript_sender_role",
    "transcript_sender_name",
    "transcript_text",
    "transcript_attachment_kind",
    "transcript_attachment_file_id",
    "transcript_attachment_file_unique_id",
    "transcript_attachment_filename",
    "transcript_attachment_mime_type",
    "transcript_attachment_storage_path",
    "internal_note_index",
    "internal_note_timestamp",
    "internal_note_author_id",
    "internal_note_author_name",
    "internal_note_text",
)


def render_ticket_report_csv(report: TicketReport) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES)
    writer.writeheader()

    rows = _build_record_rows(report)
    if not rows:
        writer.writerow(_build_base_row(report))
        return buffer.getvalue().encode("utf-8-sig")

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue().encode("utf-8-sig")


def _build_base_row(report: TicketReport) -> dict[str, str | int]:
    return {
        "ticket_public_number": _sanitize_csv_value(report.public_number),
        "ticket_public_id": _sanitize_csv_value(str(report.public_id)),
        "ticket_status": _sanitize_csv_value(report.status.value),
        "ticket_priority": _sanitize_csv_value(report.priority),
        "ticket_subject": _sanitize_csv_value(report.subject),
        "ticket_category_code": _sanitize_csv_value(report.category_code or ""),
        "ticket_category_title": _sanitize_csv_value(report.category_title or ""),
        "ticket_created_at": _format_timestamp(report.created_at),
        "ticket_updated_at": _format_timestamp(report.updated_at),
        "ticket_first_response_at": _format_timestamp(report.first_response_at),
        "ticket_first_response_seconds": report.first_response_seconds or "",
        "ticket_closed_at": _format_timestamp(report.closed_at),
        "ticket_assigned_operator_id": report.assigned_operator_id or "",
        "ticket_assigned_operator_name": _sanitize_csv_value(report.assigned_operator_name or ""),
        "ticket_assigned_operator_telegram_user_id": (
            report.assigned_operator_telegram_user_id or ""
        ),
        "ticket_client_chat_id": report.client_chat_id,
        "ticket_tags": _sanitize_csv_value(", ".join(report.tags)),
        "feedback_rating": report.feedback.rating if report.feedback is not None else "",
        "feedback_comment": (
            _sanitize_csv_value(report.feedback.comment or "")
            if report.feedback is not None
            else ""
        ),
        "feedback_submitted_at": (
            _format_timestamp(report.feedback.submitted_at) if report.feedback is not None else ""
        ),
        "record_type": "",
        "record_sequence": "",
        "record_timestamp": "",
        "transcript_index": "",
        "transcript_timestamp": "",
        "transcript_sender_role": "",
        "transcript_sender_name": "",
        "transcript_text": "",
        "transcript_attachment_kind": "",
        "transcript_attachment_file_id": "",
        "transcript_attachment_file_unique_id": "",
        "transcript_attachment_filename": "",
        "transcript_attachment_mime_type": "",
        "transcript_attachment_storage_path": "",
        "internal_note_index": "",
        "internal_note_timestamp": "",
        "internal_note_author_id": "",
        "internal_note_author_name": "",
        "internal_note_text": "",
    }


def _build_record_rows(report: TicketReport) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    sequence = 1
    note_indexes = {id(note): index for index, note in enumerate(report.internal_notes, start=1)}

    records = sorted(
        (
            *(
                ("message", index, message.created_at, message)
                for index, message in enumerate(report.messages, start=1)
            ),
            *(
                ("internal_note", note_indexes[id(note)], note.created_at, note)
                for note in report.internal_notes
            ),
        ),
        key=lambda item: (item[2], 0 if item[0] == "message" else 1, item[1]),
    )

    for record_type, index, created_at, payload in records:
        base_row = {
            **_build_base_row(report),
            "record_type": record_type,
            "record_sequence": sequence,
            "record_timestamp": _format_timestamp(created_at),
        }
        if record_type == "message":
            rows.append(
                {
                    **base_row,
                    **_build_message_row(index=index, message=payload),
                }
            )
        else:
            rows.append(
                {
                    **base_row,
                    **_build_internal_note_row(index=index, note=payload),
                }
            )
        sequence += 1

    return rows


def _build_message_row(*, index: int, message: object) -> dict[str, str]:
    from application.use_cases.tickets.exports import TicketReportMessage

    assert isinstance(message, TicketReportMessage)
    return {
        "transcript_index": str(index),
        "transcript_timestamp": _format_timestamp(message.created_at),
        "transcript_sender_role": message.sender_type.value,
        "transcript_sender_name": _sanitize_csv_value(message.sender_operator_name or ""),
        "transcript_text": _sanitize_csv_value(message.text or ""),
        "transcript_attachment_kind": (
            _sanitize_csv_value(message.attachment.kind.value)
            if message.attachment is not None
            else ""
        ),
        "transcript_attachment_file_id": (
            _sanitize_csv_value(message.attachment.telegram_file_id)
            if message.attachment is not None
            else ""
        ),
        "transcript_attachment_file_unique_id": (
            _sanitize_csv_value(message.attachment.telegram_file_unique_id or "")
            if message.attachment is not None
            and message.attachment.telegram_file_unique_id is not None
            else ""
        ),
        "transcript_attachment_filename": (
            _sanitize_csv_value(message.attachment.filename or "")
            if message.attachment is not None and message.attachment.filename is not None
            else ""
        ),
        "transcript_attachment_mime_type": (
            _sanitize_csv_value(message.attachment.mime_type or "")
            if message.attachment is not None and message.attachment.mime_type is not None
            else ""
        ),
        "transcript_attachment_storage_path": (
            _sanitize_csv_value(message.attachment.storage_path or "")
            if message.attachment is not None and message.attachment.storage_path is not None
            else ""
        ),
        "internal_note_index": "",
        "internal_note_timestamp": "",
        "internal_note_author_id": "",
        "internal_note_author_name": "",
        "internal_note_text": "",
    }


def _build_internal_note_row(*, index: int, note: object) -> dict[str, str]:
    from application.use_cases.tickets.exports import TicketReportInternalNote

    assert isinstance(note, TicketReportInternalNote)
    return {
        "transcript_index": "",
        "transcript_timestamp": "",
        "transcript_sender_role": "",
        "transcript_sender_name": "",
        "transcript_text": "",
        "transcript_attachment_kind": "",
        "transcript_attachment_file_id": "",
        "transcript_attachment_file_unique_id": "",
        "transcript_attachment_filename": "",
        "transcript_attachment_mime_type": "",
        "transcript_attachment_storage_path": "",
        "internal_note_index": str(index),
        "internal_note_timestamp": _format_timestamp(note.created_at),
        "internal_note_author_id": str(note.author_operator_id),
        "internal_note_author_name": _sanitize_csv_value(note.author_operator_name or ""),
        "internal_note_text": _sanitize_csv_value(note.text),
    }


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat()


def _sanitize_csv_value(value: str) -> str:
    if not value:
        return value
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if normalized[0] in {"=", "+", "-", "@", "\t"}:
        return f"'{normalized}"
    return normalized
