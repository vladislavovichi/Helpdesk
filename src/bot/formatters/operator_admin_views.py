from __future__ import annotations

from collections.abc import Sequence

from application.use_cases.tickets.summaries import OperatorSummary, TagSummary
from bot.formatters.operator_primitives import format_operator_line, format_tags


def format_operator_list_response(
    *,
    operators: Sequence[OperatorSummary],
    super_admin_telegram_user_ids: Sequence[int],
) -> str:
    super_admins = ", ".join(str(item) for item in super_admin_telegram_user_ids) or "-"
    lines = [
        "Операторы",
        f"В команде: {len(operators)}",
        "",
        "Суперадминистраторы",
        super_admins,
        "",
        "Команда",
    ]

    if not operators:
        lines.append("- пока пусто")
    else:
        for operator in operators:
            lines.append(f"- {format_operator_line(operator)}")

    lines.extend(["", "Откройте оператора ниже или добавьте нового."])
    return "\n".join(lines)


def format_operator_detail_response(operator: OperatorSummary) -> str:
    lines = [
        "Оператор",
        "",
        "Имя",
        operator.display_name,
        "",
        "Telegram ID",
        str(operator.telegram_user_id),
    ]
    if operator.username:
        lines.extend(["", "Username", f"@{operator.username}"])
    return "\n".join(lines)


def format_ticket_tags_response(
    public_number: str,
    ticket_tags: Sequence[str],
    available_tags: Sequence[TagSummary],
) -> str:
    lines = [
        f"Заявка {public_number}",
        "",
        "Метки",
        format_tags(ticket_tags),
        "",
        "Каталог",
        format_tags(tuple(tag.name for tag in available_tags)),
        "",
        "Нажмите на метку ниже.",
    ]
    return "\n".join(lines)
