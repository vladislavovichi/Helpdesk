from __future__ import annotations

from application.ai.summaries import TicketAssistSnapshot
from application.use_cases.tickets.summaries import TicketDetailsSummary


def format_ticket_assist_snapshot(
    *,
    ticket: TicketDetailsSummary,
    snapshot: TicketAssistSnapshot,
) -> str:
    lines = [f"Подсказки по заявке {ticket.public_number}", "", ticket.subject]

    if snapshot.available:
        if snapshot.short_summary:
            lines.extend(["", "Краткая суть", snapshot.short_summary])
        if snapshot.user_goal:
            lines.extend(["", "Что хотел пользователь", snapshot.user_goal])
        if snapshot.actions_taken:
            lines.extend(["", "Что уже сделано", snapshot.actions_taken])
        if snapshot.current_status:
            lines.extend(["", "Текущее состояние", snapshot.current_status])
    else:
        lines.extend(
            [
                "",
                "AI-помощь сейчас недоступна.",
                snapshot.unavailable_reason
                or "Продолжайте работу через карточку и библиотеку макросов.",
            ]
        )

    lines.extend(["", "Рекомендуемые макросы"])
    if snapshot.macro_suggestions:
        for index, suggestion in enumerate(snapshot.macro_suggestions, start=1):
            lines.extend([f"{index}. {suggestion.title}", f"   {suggestion.reason}", ""])
    else:
        lines.append(
            "Подходящих подсказок пока нет. "
            "Библиотека макросов остаётся доступной вручную."
        )

    if snapshot.model_id:
        lines.extend(["", f"Модель: {snapshot.model_id}"])
    return "\n".join(lines)
