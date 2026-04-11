from __future__ import annotations

from collections.abc import Sequence

from application.use_cases.tickets.summaries import HistoricalTicketSummary, TicketDetailsSummary
from bot.formatters.operator_primitives import format_status, format_timestamp, shorten_text

ARCHIVE_PAGE_CHUNK = 6


def format_archive_page(
    tickets: Sequence[HistoricalTicketSummary],
    *,
    current_page: int,
    total_pages: int,
    selected_category_title: str | None = None,
) -> str:
    title = "Архив"
    if selected_category_title:
        title = f"Архив · {selected_category_title}"
    lines = [title, f"Страница {current_page} / {total_pages}", ""]

    if not tickets:
        lines.extend(
            [
                "По выбранной теме закрытых заявок пока нет.",
                "",
                "Смените фильтр или вернитесь к общему архиву.",
            ]
        )
        return "\n".join(lines)

    for index, ticket in enumerate(tickets, start=1):
        lines.extend(
            [
                f"{index}. {ticket.public_number}",
                f"   {_build_archive_meta(ticket)}",
                f"   {shorten_text(ticket.mini_title, 84)}",
                "",
            ]
        )

    lines.append(
        "Откройте архивное дело, чтобы посмотреть карточку и сразу выгрузить CSV или HTML."
    )
    return "\n".join(lines)


def format_archived_ticket_surface(ticket: TicketDetailsSummary) -> str:
    lines = [
        f"Архивное дело {ticket.public_number}",
        "",
        "Статус",
        format_status(ticket.status).capitalize(),
        "",
        "Тема",
        ticket.subject,
    ]
    if ticket.category_title:
        lines.extend(["", "Тема обращения", ticket.category_title])
    lines.extend(
        [
            "",
            "Создана",
            format_timestamp(ticket.created_at),
        ]
    )
    if ticket.closed_at is not None:
        lines.extend(["", "Закрыта", format_timestamp(ticket.closed_at)])
    if ticket.assigned_operator_name:
        lines.extend(["", "Ответственный", ticket.assigned_operator_name])
    if ticket.tags:
        lines.extend(["", "Теги", ", ".join(ticket.tags)])
    lines.extend(
        [
            "",
            "Материалы дела",
            _build_archive_case_digest(ticket),
            "",
            "Экспорт",
            "HTML — спокойный case file с перепиской и вложениями.",
            "CSV — машинная выгрузка для отчёта и сверки.",
        ]
    )
    return "\n".join(lines)


def _build_archive_meta(ticket: HistoricalTicketSummary) -> str:
    parts = [format_status(ticket.status).capitalize()]
    if ticket.category_title:
        parts.append(ticket.category_title)
    parts.append(f"Создана {format_timestamp(ticket.created_at)}")
    if ticket.closed_at is not None:
        parts.append(f"Закрыта {format_timestamp(ticket.closed_at)}")
    return " • ".join(parts)


def _build_archive_case_digest(ticket: TicketDetailsSummary) -> str:
    messages_count = len(ticket.message_history)
    notes_count = len(ticket.internal_notes)
    first_client_text = next(
        (
            message.text
            for message in ticket.message_history
            if message.sender_type.value == "client" and message.text
        ),
        None,
    )
    latest_text = ticket.last_message_text
    lines = [
        f"Сообщений · {messages_count}",
        f"Заметок · {notes_count}",
    ]
    if first_client_text:
        lines.append(f"Старт · {shorten_text(' '.join(first_client_text.split()), 120)}")
    if latest_text:
        lines.append(f"Финал · {shorten_text(' '.join(latest_text.split()), 120)}")
    return "\n".join(lines)
