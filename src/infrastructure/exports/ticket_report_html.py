import base64
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from application.use_cases.tickets.exports import (
    TicketReport,
    TicketReportAttachment,
    TicketReportEvent,
    TicketReportInternalNote,
    TicketReportMessage,
)
from domain.enums.tickets import (
    TicketAttachmentKind,
    TicketEventType,
    TicketMessageSenderType,
    TicketSentiment,
    TicketStatus,
)
from infrastructure.assets.storage import LocalTicketAssetStorage
from infrastructure.config.settings import get_settings
from infrastructure.exports.html_templates import render_html_template

EMBEDDED_PHOTO_MAX_BYTES = 8 * 1024 * 1024
SAFE_EMBEDDED_IMAGE_MIME_TYPES = frozenset({"image/gif", "image/jpeg", "image/png", "image/webp"})


def render_ticket_report_html(report: TicketReport) -> bytes:
    generated_at = _format_timestamp(datetime.now(UTC))
    attachment_count = sum(1 for message in report.messages if message.attachment is not None)
    duplicate_count = sum(message.duplicate_count for message in report.messages)
    html = render_html_template(
        "ticket_report.html.j2",
        {
            "css": _DOCUMENT_CSS,
            "generated_at": generated_at,
            "report": {
                "public_number": report.public_number,
                "subject": report.subject,
                "status_css": _status_css(report.status),
                "status_label": _status_label(report.status),
                "priority_css": f"priority-{report.priority}",
                "priority_label": _priority_label(report.priority),
                "message_count": len(report.messages),
                "attachment_count": attachment_count,
                "duplicate_count": duplicate_count,
                "internal_note_count": len(report.internal_notes),
                "event_count": len(report.events),
                "operator_href": _build_operator_link(report),
                "operator_identity": _plain_operator_identity(report),
                "metadata": _report_metadata(report),
                "summary_cards": _summary_cards(report, attachment_count, duplicate_count),
                "context_cards": _context_cards(report),
                "messages": _message_items(report.messages),
                "attachments": _attachment_gallery_items(report.messages),
                "internal_notes": _internal_note_items(report.internal_notes),
                "events": _event_items(report.events),
            },
        },
    )
    return html.encode("utf-8")


_DOCUMENT_CSS = """
    :root {
      color-scheme: light;
      --bg: #f3eee7;
      --paper: rgba(255, 255, 255, 0.86);
      --paper-strong: #fffdf9;
      --surface: rgba(255, 255, 255, 0.72);
      --surface-muted: rgba(248, 243, 237, 0.82);
      --line: rgba(38, 45, 53, 0.09);
      --line-strong: rgba(38, 45, 53, 0.16);
      --text: #1b222b;
      --muted: #66727d;
      --accent: #1f2834;
      --accent-soft: rgba(31, 40, 52, 0.07);
      --success: #315b4b;
      --warning: #8a6229;
      --danger: #8c3f3f;
      --info: #405d73;
      --shadow-sm: 0 8px 18px rgba(26, 33, 41, 0.05);
      --shadow-md: 0 18px 42px rgba(26, 33, 41, 0.08);
      --shadow-lg: 0 32px 84px rgba(26, 33, 41, 0.12);
      --radius-sm: 10px;
      --radius-md: 16px;
      --radius-lg: 22px;
      --radius-xl: 34px;
    }
    * { box-sizing: border-box; }
    html { background: #e5dbcf; }
    body {
      margin: 0;
      min-width: 0;
      background:
        radial-gradient(circle at 10% -6%, rgba(180, 151, 110, 0.24), transparent 34%),
        radial-gradient(circle at 94% 2%, rgba(64, 93, 115, 0.14), transparent 30%),
        radial-gradient(circle at 50% 104%, rgba(255, 255, 255, 0.88), transparent 40%),
        linear-gradient(180deg, #fbf8f3 0%, var(--bg) 54%, #e5dbcf 100%);
      color: var(--text);
      font-family: "SF Pro Text", "Inter", "Segoe UI", system-ui, sans-serif;
      line-height: 1.62;
      padding: 32px 16px 54px;
    }
    a { color: var(--accent); text-decoration: none; }
    a:focus-visible {
      outline: 3px solid rgba(31, 40, 52, 0.18);
      outline-offset: 3px;
      border-radius: 8px;
    }
    .page { width: min(1160px, 100%); margin: 0 auto; }
    .cover, .report-section, .summary-card, .context-card, .message, .asset-card, .note, .event {
      border: 1px solid var(--line);
      background: var(--paper);
      box-shadow: var(--shadow-sm);
    }
    .cover {
      position: relative;
      overflow: hidden;
      border-color: rgba(255, 255, 255, 0.74);
      border-radius: var(--radius-xl);
      background:
        radial-gradient(circle at top right, rgba(31, 40, 52, 0.08), transparent 38%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(243, 235, 225, 0.82));
      box-shadow: var(--shadow-lg);
      padding: 34px;
      margin-bottom: 18px;
    }
    .cover-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.75fr);
      gap: 28px;
      align-items: start;
    }
    .eyebrow {
      margin: 0 0 10px;
      color: #756249;
      font-size: 12px;
      font-weight: 760;
      text-transform: uppercase;
    }
    h1, h2, h3 {
      margin: 0;
      color: var(--text);
      font-weight: 680;
      line-height: 1.08;
      letter-spacing: 0;
    }
    h1 { font-size: clamp(34px, 5vw, 56px); }
    h2 { font-size: 25px; }
    h3 { font-size: 17px; }
    .subject {
      max-width: 780px;
      margin: 14px 0 0;
      color: #3c4652;
      font-size: 18px;
      line-height: 1.56;
      overflow-wrap: anywhere;
    }
    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }
    .chip, .status-chip, .priority-chip {
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 32px;
      padding: 7px 12px;
      border: 1px solid rgba(38, 45, 53, 0.08);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.62);
      color: #4b5662;
      font-size: 13px;
      font-weight: 680;
      overflow-wrap: anywhere;
    }
    .status-closed { color: var(--success); background: rgba(49, 91, 75, 0.12); }
    .status-escalated { color: var(--danger); background: rgba(140, 63, 63, 0.12); }
    .status-assigned { color: var(--success); background: rgba(49, 91, 75, 0.10); }
    .status-queued { color: #756249; background: rgba(122, 99, 72, 0.11); }
    .status-new { color: var(--info); background: rgba(64, 93, 115, 0.11); }
    .priority-high, .priority-urgent { color: var(--warning); background: rgba(138, 98, 41, 0.13); }
    .priority-urgent { color: var(--danger); background: rgba(140, 63, 63, 0.12); }
    .cover-aside {
      display: grid;
      gap: 12px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.58);
    }
    .meta-grid, .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }
    .meta-item, .summary-card, .context-card {
      min-width: 0;
      padding: 15px;
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.66);
    }
    .meta-label, .summary-label {
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 720;
      text-transform: uppercase;
    }
    .meta-value, .summary-value {
      color: var(--text);
      font-size: 15px;
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    .summary-note { margin-top: 4px; color: var(--muted); font-size: 13px; }
    .report-section {
      border-radius: var(--radius-xl);
      padding: 28px;
      margin-bottom: 16px;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 18px;
      margin-bottom: 18px;
    }
    .section-copy {
      margin: -4px 0 18px;
      color: var(--muted);
      max-width: 760px;
    }
    .context-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }
    .context-card h3 { margin-bottom: 9px; }
    .context-card p {
      margin: 0;
      color: #4b5662;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .transcript, .notes, .event-timeline, .gallery {
      display: grid;
      gap: 14px;
    }
    .message {
      position: relative;
      padding: 18px 18px 18px 22px;
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.74);
    }
    .message::before, .event::before {
      content: "";
      position: absolute;
      top: 18px;
      bottom: 18px;
      left: 0;
      width: 3px;
      border-radius: 0 999px 999px 0;
      background: rgba(31, 40, 52, 0.16);
    }
    .message-customer::before { background: var(--info); }
    .message-operator::before { background: var(--success); }
    .message-system::before { background: var(--muted); }
    .message-head, .note-head, .event-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
    }
    .message-role, .note-role, .event-title { font-weight: 760; }
    .message-time, .note-time, .event-time, .asset-meta {
      color: var(--muted);
      font-size: 13px;
    }
    .message-body, .note-body, .event-detail {
      color: #3f4a55;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .message-flags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .flag {
      display: inline-flex;
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(138, 98, 41, 0.12);
      color: var(--warning);
      font-size: 12px;
      font-weight: 700;
    }
    .gallery {
      grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
    }
    .asset-card {
      overflow: hidden;
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.72);
    }
    .asset-media {
      display: grid;
      place-items: center;
      min-height: 220px;
      padding: 14px;
      background:
        radial-gradient(circle at top left, rgba(64, 93, 115, 0.10), transparent 42%),
        linear-gradient(180deg, rgba(244, 239, 232, 0.92), rgba(255, 253, 249, 0.98));
    }
    .asset-image {
      display: block;
      width: 100%;
      max-height: 420px;
      object-fit: contain;
      border-radius: var(--radius-md);
      background: #efe7de;
    }
    .asset-body { padding: 16px; }
    .asset-title {
      margin-bottom: 6px;
      font-weight: 760;
      overflow-wrap: anywhere;
    }
    .asset-meta {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .message-attachment {
      margin-top: 14px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: rgba(250, 247, 242, 0.78);
    }
    .note {
      padding: 18px;
      border-color: rgba(138, 98, 41, 0.15);
      border-radius: var(--radius-lg);
      background: rgba(250, 246, 240, 0.82);
    }
    .chip-internal { color: #756249; background: rgba(122, 99, 72, 0.11); }
    .event {
      position: relative;
      padding: 16px 16px 16px 22px;
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.66);
    }
    .event-created::before { background: var(--info); }
    .event-assignment::before { background: var(--success); }
    .event-escalation::before, .event-sla::before { background: var(--danger); }
    .event-tag::before { background: #756249; }
    .event-closed::before { background: var(--accent); }
    .event-sentiment::before, .event-duplicate::before { background: var(--warning); }
    .empty-state {
      padding: 18px;
      border: 1px dashed var(--line-strong);
      border-radius: var(--radius-lg);
      background: var(--surface-muted);
      color: var(--muted);
    }
    .report-footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px 18px;
      padding: 18px 4px 0;
      color: var(--muted);
      font-size: 12px;
    }
    @media (max-width: 760px) {
      body { padding: 18px 12px 34px; }
      .cover, .report-section { padding: 22px; border-radius: 24px; }
      .cover-grid, .section-head { grid-template-columns: 1fr; flex-direction: column; }
      .cover-grid { display: grid; }
      h1 { font-size: 32px; }
      h2 { font-size: 22px; }
      .subject { font-size: 16px; }
      .summary-grid { grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); }
      .asset-media { min-height: 180px; padding: 12px; }
      .asset-image { max-height: 320px; }
    }
    @media (max-width: 390px) {
      body { padding-inline: 10px; }
      .cover, .report-section { padding: 18px; }
      .summary-grid, .meta-grid, .context-grid, .gallery { grid-template-columns: 1fr; }
      .chip, .status-chip, .priority-chip { white-space: normal; }
    }
    @page { margin: 16mm; }
    @media print {
      html, body { background: #fff !important; }
      body { padding: 0; color: #111827; font-size: 11pt; }
      .cover, .report-section, .summary-card, .context-card, .message, .asset-card, .note, .event {
        box-shadow: none !important;
        background: #fff !important;
        border-color: #d6d3ce !important;
      }
      .cover, .report-section { page-break-inside: avoid; break-inside: avoid; }
      .message, .asset-card, .note, .event, .summary-card {
        page-break-inside: avoid;
        break-inside: avoid;
      }
      .asset-image { max-height: 95mm; }
      .report-footer { border-top: 1px solid #d6d3ce; margin-top: 10mm; }
    }
"""


def _report_metadata(report: TicketReport) -> list[dict[str, str]]:
    return [
        {"label": "Client chat id", "value": str(report.client_chat_id)},
        {"label": "Assigned operator", "value": _plain_operator_identity(report)},
        {"label": "Created", "value": _format_timestamp(report.created_at)},
        {"label": "Updated", "value": _format_timestamp(report.updated_at)},
        {"label": "Closed", "value": _format_timestamp(report.closed_at)},
        {"label": "Category", "value": _category_text(report)},
        {"label": "Tags", "value": _tags_text(report)},
        {"label": "Sentiment", "value": _ticket_sentiment_text(report)},
        {"label": "First response", "value": _format_duration(report.first_response_seconds)},
        {"label": "Closure summary", "value": _closure_summary(report)},
    ]


def _summary_cards(
    report: TicketReport,
    attachment_count: int,
    duplicate_count: int,
) -> list[dict[str, str]]:
    return [
        {
            "label": "Current status",
            "value": _status_label(report.status),
            "note": _status_hint(report.status),
        },
        {
            "label": "Category",
            "value": _category_text(report),
            "note": report.category_code or "No category code",
        },
        {
            "label": "Priority",
            "value": _priority_label(report.priority),
            "note": "Ticket priority at export time",
        },
        {
            "label": "Sentiment",
            "value": _ticket_sentiment_text(report),
            "note": "Customer tone signal",
        },
        {
            "label": "First response",
            "value": _format_duration(report.first_response_seconds),
            "note": "Time to first operator reply",
        },
        {"label": "Messages", "value": str(len(report.messages)), "note": "Conversation items"},
        {"label": "Attachments", "value": str(attachment_count), "note": "Photos and files"},
        {"label": "Duplicates", "value": str(duplicate_count), "note": "Collapsed repeats"},
        {
            "label": "Internal notes",
            "value": str(len(report.internal_notes)),
            "note": "Included operator notes",
        },
        {"label": "Events", "value": str(len(report.events)), "note": "Lifecycle events"},
        {
            "label": "Feedback",
            "value": _feedback_rating(report),
            "note": "Customer rating when available",
        },
    ]


def _context_cards(report: TicketReport) -> list[dict[str, str]]:
    first_message = (
        _first_client_message(report.messages) or "Клиентское сообщение не зафиксировано."
    )
    feedback = _feedback_text(report)
    sentiment_reason = report.sentiment_reason or "Отдельная причина не зафиксирована."
    return [
        {"title": "Первое сообщение", "text": first_message},
        {"title": "Клиент", "text": f"Telegram chat ID {report.client_chat_id}"},
        {"title": "Причина сигнала", "text": sentiment_reason},
        {"title": "Обратная связь", "text": feedback},
    ]


def _event_items(events: tuple[TicketReportEvent, ...]) -> list[dict[str, str | None]]:
    return [
        {
            "css": _event_css(event.event_type),
            "title": _event_title(event.event_type),
            "time": _format_timestamp(event.created_at),
            "detail": _event_detail(event),
        }
        for event in sorted(events, key=lambda item: item.created_at)
    ]


def _attachment_gallery_items(
    messages: tuple[TicketReportMessage, ...],
) -> list[dict[str, str | None]]:
    attachments = [
        (index, message.created_at, message.attachment)
        for index, message in enumerate(messages, start=1)
        if message.attachment is not None
    ]
    return [
        _attachment_card_item(
            attachment,
            title=f"{index}. {_attachment_label(attachment)}",
            timestamp=created_at,
            embedded=True,
        )
        for index, created_at, attachment in attachments
        if attachment is not None
    ]


def _message_items(
    messages: tuple[TicketReportMessage, ...],
) -> list[dict[str, object]]:
    return [
        {
            "css": _message_css(message.sender_type),
            "sender_label": _message_sender_label(message),
            "time": _format_timestamp(message.created_at),
            "text": message.text,
            "flags": _message_flags(message),
            "attachment": _message_attachment_item(message.attachment),
        }
        for message in messages
    ]


def _message_attachment_item(
    attachment: TicketReportAttachment | None,
) -> dict[str, str | None] | None:
    if attachment is None:
        return None
    return _attachment_card_item(attachment, title=_attachment_label(attachment), embedded=True)


def _attachment_card_item(
    attachment: TicketReportAttachment,
    *,
    title: str,
    timestamp: datetime | None = None,
    embedded: bool,
) -> dict[str, str | None]:
    embedded_photo = (
        _load_embedded_photo(attachment)
        if embedded and attachment.kind == TicketAttachmentKind.PHOTO
        else None
    )
    return {
        "title": title,
        "timestamp": _format_timestamp(timestamp) if timestamp is not None else None,
        "meta": _attachment_meta_text(attachment),
        "embedded_photo": embedded_photo,
        "alt": _attachment_label(attachment),
    }


def _internal_note_items(
    notes: tuple[TicketReportInternalNote, ...],
) -> list[dict[str, str]]:
    return [
        {
            "author": _internal_note_author(note),
            "time": _format_timestamp(note.created_at),
            "text": note.text,
        }
        for note in notes
    ]


def _plain_operator_identity(report: TicketReport) -> str:
    if report.assigned_operator_id is None:
        return "Не назначен"
    if report.assigned_operator_name:
        return report.assigned_operator_name
    return f"Оператор #{report.assigned_operator_id}"


def _build_operator_link(report: TicketReport) -> str | None:
    if report.assigned_operator_username:
        return f"https://t.me/{quote(report.assigned_operator_username, safe='')}"
    if report.assigned_operator_telegram_user_id is not None:
        return f"tg://user?id={report.assigned_operator_telegram_user_id}"
    return None


def _message_sender_label(message: TicketReportMessage) -> str:
    if message.sender_type == TicketMessageSenderType.CLIENT:
        return "Клиент"
    if message.sender_type == TicketMessageSenderType.SYSTEM:
        return "Система"
    if message.sender_operator_name:
        return f"Оператор · {message.sender_operator_name}"
    return "Оператор"


def _message_css(sender_type: TicketMessageSenderType) -> str:
    if sender_type == TicketMessageSenderType.CLIENT:
        return "message-customer"
    if sender_type == TicketMessageSenderType.SYSTEM:
        return "message-system"
    return "message-operator"


def _message_summary(message: TicketReportMessage | None) -> str:
    if message is None:
        return "Переписка ещё не велась."
    if message.text:
        summary = " ".join(message.text.split())
        if message.duplicate_count > 0:
            summary = f"{summary} · ещё {message.duplicate_count} повт."
        return summary
    if message.attachment is not None:
        return _attachment_label(message.attachment)
    return "Сообщение без текста."


def _attachment_label(attachment: TicketReportAttachment) -> str:
    if attachment.kind == TicketAttachmentKind.PHOTO:
        return f"Фото · {attachment.filename}" if attachment.filename else "Фото"
    if attachment.kind == TicketAttachmentKind.VOICE:
        if attachment.filename:
            return f"Голосовое сообщение · {attachment.filename}"
        return "Голосовое сообщение"
    if attachment.kind == TicketAttachmentKind.VIDEO:
        return f"Видео · {attachment.filename}" if attachment.filename else "Видео"
    if attachment.filename:
        return f"Файл · {attachment.filename}"
    return "Файл"


def _attachment_meta_text(attachment: TicketReportAttachment) -> str:
    parts = [f"Тип: {attachment.kind.value}"]
    if attachment.filename:
        parts.append(f"Имя: {attachment.filename}")
    if attachment.mime_type:
        parts.append(f"MIME: {attachment.mime_type}")
    safe_storage_path = _safe_storage_path_text(attachment.storage_path)
    if safe_storage_path:
        parts.append(f"Материал: {safe_storage_path}")
    elif attachment.storage_path:
        parts.append("Материал: путь недоступен")
    return " · ".join(parts)


def _safe_storage_path_text(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    if _resolve_asset_path(storage_path) is None:
        return None
    return storage_path


def _internal_note_author(note: TicketReportInternalNote) -> str:
    if note.author_operator_name:
        return f"Внутренняя заметка · {note.author_operator_name}"
    return f"Внутренняя заметка · оператор #{note.author_operator_id}"


def _event_title(event_type: TicketEventType) -> str:
    mapping = {
        TicketEventType.CREATED: "Заявка создана",
        TicketEventType.QUEUED: "Поставлена в очередь",
        TicketEventType.ASSIGNED: "Назначена оператору",
        TicketEventType.REASSIGNED: "Передана другому оператору",
        TicketEventType.AUTO_REASSIGNED: "Автоматически передана",
        TicketEventType.CLIENT_MESSAGE_DUPLICATE_COLLAPSED: "Повтор клиента объединён",
        TicketEventType.CLIENT_SENTIMENT_FLAGGED: "Усилен сигнал по тону клиента",
        TicketEventType.ESCALATED: "Переведена на эскалацию",
        TicketEventType.AUTO_ESCALATED: "Автоматически эскалирована",
        TicketEventType.SLA_BREACHED_FIRST_RESPONSE: "Нарушен SLA первого ответа",
        TicketEventType.SLA_BREACHED_RESOLUTION: "Нарушен SLA решения",
        TicketEventType.TAG_ADDED: "Добавлена метка",
        TicketEventType.TAG_REMOVED: "Снята метка",
        TicketEventType.CLOSED: "Заявка закрыта",
    }
    return mapping.get(event_type, event_type.value)


def _event_css(event_type: TicketEventType) -> str:
    if event_type == TicketEventType.CREATED:
        return "event-created"
    if event_type in {
        TicketEventType.ASSIGNED,
        TicketEventType.REASSIGNED,
        TicketEventType.AUTO_REASSIGNED,
        TicketEventType.QUEUED,
    }:
        return "event-assignment"
    if event_type in {TicketEventType.ESCALATED, TicketEventType.AUTO_ESCALATED}:
        return "event-escalation"
    if event_type in {
        TicketEventType.SLA_BREACHED_FIRST_RESPONSE,
        TicketEventType.SLA_BREACHED_RESOLUTION,
    }:
        return "event-sla"
    if event_type in {TicketEventType.TAG_ADDED, TicketEventType.TAG_REMOVED}:
        return "event-tag"
    if event_type == TicketEventType.CLOSED:
        return "event-closed"
    if event_type == TicketEventType.CLIENT_SENTIMENT_FLAGGED:
        return "event-sentiment"
    if event_type == TicketEventType.CLIENT_MESSAGE_DUPLICATE_COLLAPSED:
        return "event-duplicate"
    return ""


def _event_detail(event: TicketReportEvent) -> str | None:
    payload = event.payload_json or {}
    if event.event_type in {TicketEventType.TAG_ADDED, TicketEventType.TAG_REMOVED}:
        tag = payload.get("tag")
        if isinstance(tag, str) and tag:
            return tag
        return None
    if event.event_type == TicketEventType.CLIENT_MESSAGE_DUPLICATE_COLLAPSED:
        duplicate_count = payload.get("duplicate_count")
        if isinstance(duplicate_count, int) and duplicate_count > 0:
            return f"Сообщение клиента повторено ещё {duplicate_count} раз."
        return "Повтор клиента объединён в каноническое сообщение."
    if event.event_type == TicketEventType.CLIENT_SENTIMENT_FLAGGED:
        sentiment = payload.get("sentiment")
        reason = payload.get("sentiment_reason")
        if isinstance(sentiment, str) and isinstance(reason, str) and reason:
            return f"{_sentiment_label(sentiment)} · {reason}"
        if isinstance(sentiment, str):
            return _sentiment_label(sentiment)
        return None
    if event.event_type in {
        TicketEventType.ASSIGNED,
        TicketEventType.REASSIGNED,
        TicketEventType.AUTO_REASSIGNED,
    }:
        assigned_operator_id = payload.get("assigned_operator_id")
        if isinstance(assigned_operator_id, int):
            return f"Оператор #{assigned_operator_id}"
        return None
    from_status = payload.get("from_status")
    to_status = payload.get("to_status")
    if isinstance(from_status, str) and isinstance(to_status, str):
        return f"{from_status} -> {to_status}"
    return None


def _status_label(status: TicketStatus) -> str:
    return {
        TicketStatus.NEW: "Новая",
        TicketStatus.QUEUED: "В очереди",
        TicketStatus.ASSIGNED: "В работе",
        TicketStatus.ESCALATED: "Эскалация",
        TicketStatus.CLOSED: "Закрыта",
    }[status]


def _status_hint(status: TicketStatus) -> str:
    hints = {
        TicketStatus.NEW: "Карточка создана, работа ещё не начата",
        TicketStatus.QUEUED: "Дело ожидало назначения",
        TicketStatus.ASSIGNED: "Дело велось оператором",
        TicketStatus.ESCALATED: "Требовалось усиленное внимание",
        TicketStatus.CLOSED: "Дело завершено и передано в архив",
    }
    return hints[status]


def _status_css(status: TicketStatus) -> str:
    return f"status-{status.value}"


def _priority_label(priority: str) -> str:
    return {
        "low": "Low",
        "normal": "Normal",
        "high": "High",
        "urgent": "Urgent",
    }.get(priority, priority)


def _ticket_sentiment_text(report: TicketReport) -> str:
    if report.sentiment is None or report.sentiment == TicketSentiment.CALM:
        return "Спокойный"
    label = _sentiment_label(report.sentiment.value).capitalize()
    if report.sentiment_reason:
        return f"{label} · {report.sentiment_reason}"
    return label


def _category_text(report: TicketReport) -> str:
    if report.category_title and report.category_code:
        return f"{report.category_title} · {report.category_code}"
    return report.category_title or report.category_code or "Не указана"


def _tags_text(report: TicketReport) -> str:
    return ", ".join(report.tags) if report.tags else "Нет"


def _feedback_rating(report: TicketReport) -> str:
    if report.feedback is None:
        return "Нет"
    return f"{report.feedback.rating} / 5"


def _feedback_text(report: TicketReport) -> str:
    if report.feedback is None:
        return "Клиент не оставил оценку."
    comment = report.feedback.comment or "Без комментария."
    return (
        f"{report.feedback.rating} / 5 · {comment} · "
        f"{_format_timestamp(report.feedback.submitted_at)}"
    )


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "Нет"
    return value.astimezone(UTC).strftime("%d.%m.%Y %H:%M UTC")


def _format_duration(value: int | None) -> str:
    if value is None:
        return "Нет"
    minutes, seconds = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин {seconds} сек"
    return f"{seconds} сек"


def _closure_summary(report: TicketReport) -> str:
    if report.closed_at is None:
        return "Дело ещё не закрыто."
    return (
        f"Закрыто {_format_timestamp(report.closed_at)}. "
        f"Первый ответ: {_format_duration(report.first_response_seconds)}."
    )


def _message_flags(message: TicketReportMessage) -> list[str]:
    flags: list[str] = []
    if (
        message.sender_type == TicketMessageSenderType.CLIENT
        and message.sentiment is not None
        and message.sentiment != TicketSentiment.CALM
    ):
        flags.append(f"Тон клиента: {_sentiment_label(message.sentiment.value)}")
    if message.duplicate_count > 0:
        flags.append(
            f"Повторено ещё {message.duplicate_count} раз"
            f" · {_format_timestamp(message.last_duplicate_at)}"
        )
    return flags


def _sentiment_label(value: str) -> str:
    return {
        TicketSentiment.CALM.value: "спокойный",
        TicketSentiment.FRUSTRATED.value: "напряжённый",
        TicketSentiment.ESCALATION_RISK.value: "риск эскалации",
    }.get(value, value)


def _first_client_message(messages: tuple[TicketReportMessage, ...]) -> str | None:
    for message in messages:
        if message.sender_type != TicketMessageSenderType.CLIENT:
            continue
        if message.text:
            return " ".join(message.text.split())
        if message.attachment is not None:
            return _attachment_label(message.attachment)
    return None


def _load_embedded_photo(attachment: TicketReportAttachment) -> str | None:
    if attachment.storage_path is None:
        return None
    asset_path = _resolve_asset_path(attachment.storage_path)
    if asset_path is None or not asset_path.exists():
        return None
    try:
        raw = asset_path.read_bytes()
    except OSError:
        return None
    if len(raw) > EMBEDDED_PHOTO_MAX_BYTES:
        return None
    mime_type = _resolve_photo_mime_type(attachment, asset_path)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_asset_path(storage_path: str) -> Path | None:
    storage = LocalTicketAssetStorage(get_settings().assets.path)
    try:
        return storage.resolve_path(storage_path)
    except ValueError:
        return None


def _resolve_photo_mime_type(attachment: TicketReportAttachment, asset_path: Path) -> str:
    if attachment.mime_type:
        mime_type = attachment.mime_type.strip().lower()
        if mime_type in SAFE_EMBEDDED_IMAGE_MIME_TYPES:
            return mime_type
        return "image/jpeg"
    guessed, _ = mimetypes.guess_type(asset_path.name)
    guessed_mime = (guessed or "image/jpeg").lower()
    if guessed_mime not in SAFE_EMBEDDED_IMAGE_MIME_TYPES:
        return "image/jpeg"
    return guessed_mime
