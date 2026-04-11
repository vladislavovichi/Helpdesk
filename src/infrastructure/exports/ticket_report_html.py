from __future__ import annotations

import base64
import mimetypes
from collections.abc import Iterable
from datetime import UTC, datetime
from html import escape
from pathlib import Path

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
    TicketStatus,
)
from infrastructure.assets.storage import LocalTicketAssetStorage
from infrastructure.config.settings import get_settings

EMBEDDED_PHOTO_MAX_BYTES = 8 * 1024 * 1024


def render_ticket_report_html(report: TicketReport) -> bytes:
    generated_at = _format_timestamp(datetime.now(UTC))
    attachment_count = sum(1 for message in report.messages if message.attachment is not None)
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Отчёт по заявке {escape(report.public_number)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe8;
      --panel: rgba(255, 255, 255, 0.92);
      --panel-strong: #fffdfa;
      --border: #ddd2c5;
      --text: #20252f;
      --muted: #6a7280;
      --accent: #204652;
      --accent-soft: #e5eef1;
      --accent-line: rgba(32, 70, 82, 0.18);
      --good: #326b51;
      --warn: #9e6b45;
      --danger: #9d4a43;
      --shadow: 0 20px 48px rgba(32, 37, 47, 0.08);
      --radius-xl: 28px;
      --radius-lg: 22px;
      --radius-md: 18px;
      --radius-sm: 14px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(32, 70, 82, 0.10), transparent 34%),
        linear-gradient(180deg, #f9f4ed 0%, var(--bg) 100%);
      color: var(--text);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      line-height: 1.58;
      padding: 32px 18px 52px;
    }}
    .page {{ max-width: 1120px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(135deg, var(--panel-strong), #f6f1ea);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow);
      padding: 30px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 12px;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.1;
    }}
    .hero-subtitle {{
      max-width: 760px;
      color: var(--text);
      font-size: 17px;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 14px;
      font-weight: 600;
    }}
    .pill.status-closed {{ background: #e5efe8; color: var(--good); }}
    .pill.status-escalated {{ background: #f6ebe2; color: var(--warn); }}
    .pill.status-new {{ background: #eef1f5; color: #455164; }}
    .pill.status-assigned {{ background: #e7eff4; color: #2b5a6b; }}
    .pill.status-queued {{ background: #f2ede6; color: #6a5a4e; }}
    .section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      box-shadow: 0 10px 28px rgba(32, 37, 47, 0.05);
      padding: 22px 24px;
      margin-bottom: 16px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}
    .section h3 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 16px;
    }}
    .card {{
      background: rgba(255, 255, 255, 0.86);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
    }}
    .metric {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .metric-value {{
      font-size: 22px;
      font-weight: 700;
      line-height: 1.2;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .meta-list {{
      display: grid;
      gap: 12px;
    }}
    .meta-item {{
      padding-top: 12px;
      border-top: 1px solid rgba(221, 210, 197, 0.75);
    }}
    .meta-item:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .value {{
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 15px;
    }}
    .summary-copy {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .summary-block {{
      background: rgba(255, 255, 255, 0.75);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
    }}
    .timeline {{
      display: grid;
      gap: 14px;
    }}
    .timeline-item {{
      position: relative;
      padding-left: 18px;
      border-left: 3px solid var(--accent-line);
    }}
    .timeline-title {{
      font-weight: 700;
      margin-bottom: 2px;
    }}
    .timeline-time {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .timeline-detail {{
      color: var(--text);
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .transcript {{
      display: grid;
      gap: 14px;
    }}
    .message {{
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 18px;
    }}
    .message-head {{
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .message-role {{
      font-weight: 700;
    }}
    .message-time {{
      color: var(--muted);
      font-size: 13px;
    }}
    .message-body {{
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .message-attachment {{
      margin-top: 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: rgba(245, 239, 232, 0.72);
      padding: 14px;
    }}
    .attachment-title {{
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .attachment-photo {{
      overflow: hidden;
      padding: 0;
      background: #faf8f4;
    }}
    .attachment-photo img {{
      display: block;
      width: 100%;
      height: auto;
      max-height: 420px;
      object-fit: contain;
      background: #faf8f4;
    }}
    .attachment-photo figcaption {{
      padding: 12px 14px 14px;
    }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .gallery-item {{
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      overflow: hidden;
    }}
    .gallery-item img {{
      width: 100%;
      height: 190px;
      object-fit: cover;
      background: #f6f1ea;
      display: block;
    }}
    .gallery-body {{
      padding: 14px;
    }}
    .muted {{
      color: var(--muted);
    }}
    @media (max-width: 720px) {{
      body {{ padding: 18px 12px 34px; }}
      .hero {{ padding: 22px 18px; border-radius: 22px; }}
      .section {{ padding: 18px; }}
      h1 {{ font-size: 28px; }}
      .hero-subtitle {{ font-size: 16px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    {_render_hero(report, generated_at)}
    <section class="grid">
      {_metric_card("Статус", _status_label(report.status), _status_hint(report.status))}
      {_metric_card("Сообщения", str(len(report.messages)), "Полная хронология переписки")}
      {_metric_card("Вложения", str(attachment_count), "Фото и файлы внутри материалов дела")}
      {_metric_card("Заметки", str(len(report.internal_notes)), "Внутренний контекст и handoff")}
    </section>
    <section class="section">
      <h2>Сводка дела</h2>
      <div class="summary-copy">
        <div class="summary-block">
          <h3>Картина по обращению</h3>
          {_render_case_summary(report)}
        </div>
        <div class="summary-block">
          <h3>Обратная связь и итог</h3>
          {_render_feedback_summary(report)}
        </div>
      </div>
    </section>
    <section class="section">
      <h2>Метаданные</h2>
      <div class="meta-grid">
        <div class="card">
          <h3>Карточка</h3>
          <div class="meta-list">
            {_meta_item("Публичный ID", str(report.public_id))}
            {_meta_item("Клиент", f"Telegram chat ID {report.client_chat_id}")}
            {_meta_item("Категория", report.category_title or "Не указана")}
            {_meta_item("Код категории", report.category_code or "Не указан")}
            {_meta_item("Ответственный", _assigned_operator(report))}
            {_meta_item("Теги", ", ".join(report.tags) if report.tags else "Нет")}
          </div>
        </div>
        <div class="card">
          <h3>Сроки</h3>
          <div class="meta-list">
            {_meta_item("Создана", _format_timestamp(report.created_at))}
            {_meta_item("Обновлена", _format_timestamp(report.updated_at))}
            {_meta_item("Первый ответ", _format_timestamp(report.first_response_at))}
            {_meta_item("Время до первого ответа", _format_duration(report.first_response_seconds))}
            {_meta_item("Закрыта", _format_timestamp(report.closed_at))}
          </div>
        </div>
      </div>
    </section>
    <section class="section">
      <h2>Ход заявки</h2>
      {_render_timeline(report.events)}
    </section>
    <section class="section">
      <h2>Материалы дела</h2>
      {_render_attachment_gallery(report.messages)}
    </section>
    <section class="section">
      <h2>Переписка</h2>
      {_render_transcript(report.messages)}
    </section>
    <section class="section">
      <h2>Внутренние заметки</h2>
      {_render_internal_notes(report.internal_notes)}
    </section>
  </div>
</body>
</html>
"""
    return html.encode("utf-8")


def _render_hero(report: TicketReport, generated_at: str) -> str:
    status_label = escape(_status_label(report.status))
    status_pill = (
        f'<span class="pill {_status_css(report.status)}">'
        f"{status_label}</span>"
    )
    return (
        '<section class="hero">'
        '<div class="eyebrow">Archived Case File</div>'
        f"<h1>{escape(report.public_number)}</h1>"
        f'<div class="hero-subtitle">{escape(report.subject)}</div>'
        '<div class="hero-meta">'
        f"{status_pill}"
        f'<span class="pill">Приоритет: {escape(_priority_label(report.priority))}</span>'
        f'<span class="pill">Подготовлен: {escape(generated_at)}</span>'
        f'<span class="pill">Экспорт: HTML</span>'
        "</div>"
        "</section>"
    )


def _metric_card(title: str, value: str, hint: str) -> str:
    return (
        '<article class="card">'
        f'<div class="metric">{escape(title)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="muted">{escape(hint)}</div>'
        "</article>"
    )


def _render_case_summary(report: TicketReport) -> str:
    first_client_message = _first_client_message(report.messages)
    last_message = report.messages[-1] if report.messages else None
    parts = [
        _meta_item("Суть обращения", first_client_message or report.subject),
        _meta_item("Последний зафиксированный шаг", _message_summary(last_message)),
        _meta_item(
            "Итог по делу",
            _closure_summary(report),
        ),
    ]
    return '<div class="meta-list">' + "".join(parts) + "</div>"


def _render_feedback_summary(report: TicketReport) -> str:
    if report.feedback is None:
        return (
            '<div class="meta-list">'
            f"{_meta_item('Оценка', 'Не получена')}"
            f"{_meta_item('Комментарий', 'Клиент не оставил комментарий.')}"
            f"{_meta_item('Фиксация', 'Дело закрыто без отдельной оценки.')}"
            "</div>"
        )
    return (
        '<div class="meta-list">'
        f"{_meta_item('Оценка', f'{report.feedback.rating} / 5')}"
        f"{_meta_item('Комментарий', report.feedback.comment or 'Без комментария')}"
        f"{_meta_item('Получена', _format_timestamp(report.feedback.submitted_at))}"
        "</div>"
    )


def _meta_item(label: str, value: str) -> str:
    return (
        '<div class="meta-item">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        "</div>"
    )


def _render_timeline(events: tuple[TicketReportEvent, ...]) -> str:
    if not events:
        return '<div class="muted">Значимых событий не найдено.</div>'

    items = []
    for event in events:
        detail = _event_detail(event)
        detail_html = (
            f'<div class="timeline-detail">{escape(detail)}</div>' if detail is not None else ""
        )
        items.append(
            '<div class="timeline-item">'
            f'<div class="timeline-title">{escape(_event_title(event.event_type))}</div>'
            f'<div class="timeline-time">{escape(_format_timestamp(event.created_at))}</div>'
            f"{detail_html}"
            "</div>"
        )
    return f'<div class="timeline">{"".join(items)}</div>'


def _render_transcript(messages: tuple[TicketReportMessage, ...]) -> str:
    if not messages:
        return '<div class="muted">Сообщений пока нет.</div>'

    items = []
    for index, message in enumerate(messages, start=1):
        attachment_html = _render_message_attachment(message.attachment)
        body = escape(message.text) if message.text else '<span class="muted">Без текста</span>'
        message_title = escape(f"{index}. {_message_sender_label(message)}")
        items.append(
            '<article class="message">'
            '<div class="message-head">'
            f'<div class="message-role">{message_title}</div>'
            f'<div class="message-time">{escape(_format_timestamp(message.created_at))}</div>'
            "</div>"
            f'<div class="message-body">{body}</div>'
            f"{attachment_html}"
            "</article>"
        )
    return f'<div class="transcript">{"".join(items)}</div>'


def _render_message_attachment(attachment: TicketReportAttachment | None) -> str:
    if attachment is None:
        return ""

    if attachment.kind == TicketAttachmentKind.PHOTO:
        embedded_photo = _load_embedded_photo(attachment)
        if embedded_photo is not None:
            return (
                '<figure class="message-attachment attachment-photo">'
                f'<img src="{embedded_photo}" alt="{escape(_attachment_label(attachment))}">'
                "<figcaption>"
                f'<div class="attachment-title">{escape(_attachment_label(attachment))}</div>'
                f'<div class="muted">{escape(_attachment_meta_text(attachment))}</div>'
                "</figcaption>"
                "</figure>"
            )

    return (
        '<div class="message-attachment">'
        f'<div class="attachment-title">{escape(_attachment_label(attachment))}</div>'
        f'<div class="muted">{escape(_attachment_meta_text(attachment))}</div>'
        "</div>"
    )


def _render_attachment_gallery(messages: Iterable[TicketReportMessage]) -> str:
    attachments = [
        (index, message.created_at, message.attachment)
        for index, message in enumerate(messages, start=1)
        if message.attachment is not None
    ]
    if not attachments:
        return '<div class="muted">Вложений в переписке нет.</div>'

    cards: list[str] = []
    for index, created_at, attachment in attachments:
        assert attachment is not None
        embedded_photo = (
            _load_embedded_photo(attachment)
            if attachment.kind == TicketAttachmentKind.PHOTO
            else None
        )
        image_html = ""
        if embedded_photo is not None:
            image_html = (
                f'<img src="{embedded_photo}" alt="{escape(_attachment_label(attachment))}">'
            )
        attachment_title = escape(f"{index}. {_attachment_label(attachment)}")
        cards.append(
            '<article class="gallery-item">'
            f"{image_html}"
            '<div class="gallery-body">'
            f'<div class="attachment-title">{attachment_title}</div>'
            f'<div class="muted">{escape(_format_timestamp(created_at))}</div>'
            f'<div class="muted">{escape(_attachment_meta_text(attachment))}</div>'
            "</div>"
            "</article>"
        )
    return f'<div class="gallery">{"".join(cards)}</div>'


def _render_internal_notes(notes: tuple[TicketReportInternalNote, ...]) -> str:
    if not notes:
        return '<div class="muted">Заметок пока нет.</div>'

    items = []
    for note in notes:
        items.append(
            '<article class="message">'
            '<div class="message-head">'
            f'<div class="message-role">{escape(_internal_note_author(note))}</div>'
            f'<div class="message-time">{escape(_format_timestamp(note.created_at))}</div>'
            "</div>"
            f'<div class="message-body">{escape(note.text)}</div>'
            "</article>"
        )
    return f'<div class="transcript">{"".join(items)}</div>'


def _assigned_operator(report: TicketReport) -> str:
    if report.assigned_operator_id is None:
        return "Не назначен"
    if report.assigned_operator_name:
        return report.assigned_operator_name
    return f"Оператор #{report.assigned_operator_id}"


def _message_sender_label(message: TicketReportMessage) -> str:
    if message.sender_type == TicketMessageSenderType.CLIENT:
        return "Клиент"
    if message.sender_operator_name:
        return f"Оператор {message.sender_operator_name}"
    if message.sender_type == TicketMessageSenderType.SYSTEM:
        return "Система"
    return "Оператор"


def _message_summary(message: TicketReportMessage | None) -> str:
    if message is None:
        return "Переписка ещё не велась."
    if message.text:
        return " ".join(message.text.split())
    if message.attachment is not None:
        return _attachment_label(message.attachment)
    return "Сообщение без текста."


def _attachment_label(attachment: TicketReportAttachment) -> str:
    if attachment.kind == TicketAttachmentKind.PHOTO:
        return "Фото"
    if attachment.kind == TicketAttachmentKind.VOICE:
        return "Голосовое сообщение"
    if attachment.kind == TicketAttachmentKind.VIDEO:
        return "Видео"
    if attachment.filename:
        return f"Файл · {attachment.filename}"
    return "Файл"


def _attachment_meta_text(attachment: TicketReportAttachment) -> str:
    parts = [f"Тип: {attachment.kind.value}"]
    if attachment.filename:
        parts.append(f"Имя: {attachment.filename}")
    if attachment.mime_type:
        parts.append(f"MIME: {attachment.mime_type}")
    if attachment.storage_path:
        parts.append(f"Хранилище: {attachment.storage_path}")
    return " · ".join(parts)


def _internal_note_author(note: TicketReportInternalNote) -> str:
    if note.author_operator_name:
        return f"Заметка · {note.author_operator_name}"
    return f"Заметка · оператор #{note.author_operator_id}"


def _event_title(event_type: TicketEventType) -> str:
    mapping = {
        TicketEventType.CREATED: "Заявка создана",
        TicketEventType.QUEUED: "Поставлена в очередь",
        TicketEventType.ASSIGNED: "Назначена оператору",
        TicketEventType.REASSIGNED: "Передана другому оператору",
        TicketEventType.AUTO_REASSIGNED: "Автоматически передана",
        TicketEventType.ESCALATED: "Переведена на эскалацию",
        TicketEventType.AUTO_ESCALATED: "Автоматически эскалирована",
        TicketEventType.SLA_BREACHED_FIRST_RESPONSE: "Нарушен SLA первого ответа",
        TicketEventType.SLA_BREACHED_RESOLUTION: "Нарушен SLA решения",
        TicketEventType.TAG_ADDED: "Добавлена метка",
        TicketEventType.TAG_REMOVED: "Снята метка",
        TicketEventType.CLOSED: "Заявка закрыта",
    }
    return mapping.get(event_type, event_type.value)


def _event_detail(event: TicketReportEvent) -> str | None:
    payload = event.payload_json or {}
    if event.event_type in {TicketEventType.TAG_ADDED, TicketEventType.TAG_REMOVED}:
        tag = payload.get("tag")
        if isinstance(tag, str) and tag:
            return tag
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
        TicketStatus.ESCALATED: "Дело требовало усиленного внимания",
        TicketStatus.CLOSED: "Дело завершено и переведено в архив",
    }
    return hints[status]


def _status_css(status: TicketStatus) -> str:
    return f"status-{status.value}"


def _priority_label(priority: str) -> str:
    return {
        "low": "низкий",
        "normal": "обычный",
        "high": "высокий",
        "urgent": "срочный",
    }.get(priority, priority)


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
    try:
        storage = LocalTicketAssetStorage(get_settings().assets.path)
    except Exception:
        return None
    try:
        return storage.resolve_path(storage_path)
    except Exception:
        return None


def _resolve_photo_mime_type(attachment: TicketReportAttachment, asset_path: Path) -> str:
    if attachment.mime_type:
        return attachment.mime_type
    guessed, _ = mimetypes.guess_type(asset_path.name)
    return guessed or "image/jpeg"
