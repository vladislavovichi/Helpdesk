from __future__ import annotations

from application.services.stats import HelpdeskOperationalStats
from bot.formatters.operator_primitives import format_duration


def format_operational_stats(stats: HelpdeskOperationalStats) -> str:
    lines = [
        "Статистика",
        f"Открытые заявки: {stats.total_open_tickets}",
        f"В очереди: {stats.queued_tickets_count}",
        f"В работе: {stats.assigned_tickets_count}",
        f"На эскалации: {stats.escalated_tickets_count}",
        f"Закрытые: {stats.closed_tickets_count}",
        "",
        "Нагрузка по операторам",
    ]

    if not stats.tickets_per_operator:
        lines.append("- активных назначений нет")
    else:
        for item in stats.tickets_per_operator:
            lines.append(f"- {item.display_name} (id={item.operator_id}): {item.ticket_count}")

    lines.extend(
        [
            "",
            "Среднее время",
            f"Первый ответ: {format_duration(stats.average_first_response_time_seconds)}",
            f"Решение: {format_duration(stats.average_resolution_time_seconds)}",
        ]
    )
    return "\n".join(lines)
