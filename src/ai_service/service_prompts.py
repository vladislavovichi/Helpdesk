from __future__ import annotations

from collections.abc import Sequence
from html import escape

from application.contracts.ai import (
    AIContextAttachment,
    AIContextInternalNote,
    AIContextMessage,
    AIPredictTicketCategoryCommand,
    GenerateTicketSummaryCommand,
    SuggestMacrosCommand,
)

MAX_HISTORY_MESSAGES = 20

SUMMARY_INSTRUCTIONS = (
    "Ты помогаешь оператору русскоязычного helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Тон деловой, спокойный, короткий. "
    "Пиши как внутреннюю support-сводку. Не выдумывай факты. "
    "Если уверенности не хватает, опирайся только на подтверждённые детали из переписки."
)
MACRO_INSTRUCTIONS = (
    "Ты подбираешь операторские макросы для helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Выбирай только из переданного списка макросов. Не придумывай новые. "
    "Если уверенность слабая, не предлагай макрос. "
    "Причина должна быть одной короткой фразой на русском."
)
CATEGORY_INSTRUCTIONS = (
    "Ты помогаешь предсказать тему нового обращения в helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Выбирай только из переданного списка тем. "
    "Если уверенность низкая, верни отсутствие предсказания. "
    "Значения medium и high используй только при явных признаках."
)


def build_ticket_summary_prompt(command: GenerateTicketSummaryCommand) -> str:
    return "\n".join(
        [
            "Сформируй краткую сводку по заявке helpdesk.",
            "Нужен JSON вида:",
            (
                '{"short_summary":"...","user_goal":"...",'
                '"actions_taken":"...","current_status":"..."}'
            ),
            "",
            "Метаданные заявки:",
            f"- public_id: {command.ticket_public_id}",
            f"- subject: {command.subject}",
            f"- status: {command.status.value}",
            f"- category: {command.category_title or 'не указана'}",
            f"- tags: {', '.join(command.tags) if command.tags else 'нет'}",
            "",
            "История сообщений:",
            format_ticket_history(command.message_history),
            "",
            "Внутренние заметки:",
            format_internal_notes(command.internal_notes),
        ]
    )


def build_macro_suggestion_prompt(command: SuggestMacrosCommand) -> str:
    macro_lines = [
        f"- id={macro.id}; title={macro.title}; body={normalize_inline(macro.body, 180)}"
        for macro in command.macros
    ]
    return "\n".join(
        [
            "Подбери до трёх макросов для оператора.",
            "Нужен JSON вида:",
            (
                '{"macro_ids":[{"macro_id":1,"reason":"...","confidence":"high"},'
                '{"macro_id":2,"reason":"...","confidence":"medium"}]}'
            ),
            "Если ничего не подходит, верни пустой массив.",
            "",
            f"Тема: {command.subject}",
            f"Статус: {command.status.value}",
            f"Категория: {command.category_title or 'не указана'}",
            f"Теги: {', '.join(command.tags) if command.tags else 'нет'}",
            "",
            "Контекст переписки:",
            format_ticket_history(command.message_history),
            "",
            "Доступные макросы:",
            "\n".join(macro_lines),
        ]
    )


def build_category_prediction_prompt(command: AIPredictTicketCategoryCommand) -> str:
    category_lines = [
        f"- id={category.id}; code={category.code}; title={category.title}"
        for category in command.categories
    ]
    return "\n".join(
        [
            "Определи наиболее вероятную тему нового обращения.",
            "Нужен JSON вида:",
            '{"category_id":2,"confidence":"medium","reason":"..."}',
            'Если тема неочевидна, верни {"category_id":null,"confidence":"none","reason":"..."}',
            "",
            f"Текст: {command.text or 'нет текста'}",
            "Вложение: " + format_attachment_hint(command.attachment),
            "",
            "Темы:",
            "\n".join(category_lines),
        ]
    )


def format_ticket_history(messages: Sequence[AIContextMessage]) -> str:
    if not messages:
        return "История сообщений пуста."

    total_count = len(messages)
    shown_messages = tuple(messages[-MAX_HISTORY_MESSAGES:])
    lines: list[str] = [
        f"Всего сообщений: {total_count}. Показано последних: {len(shown_messages)}."
    ]
    for index, message in enumerate(shown_messages, start=total_count - len(shown_messages) + 1):
        role = format_message_role(message)
        sender = f"; sender_label={message.sender_label}" if message.sender_label else ""
        created = message.created_at.isoformat()
        body = normalize_inline(message.text or "Сообщение без текста", 400)
        lines.append(f"{index}. role={role}{sender}; created_at={created}")
        lines.append(f"   text: {body}")
        if message.attachment is not None:
            lines.append(f"   attachment_hint: {format_attachment_hint(message.attachment)}")
    return "\n".join(lines)


def format_internal_notes(notes: Sequence[AIContextInternalNote]) -> str:
    if not notes:
        return "Заметок нет."
    return "\n".join(
        (
            f"{index}. author={note.author_name or 'оператор'}; "
            f"created_at={note.created_at.isoformat()}; "
            f"text={normalize_inline(note.text, 280)}"
        )
        for index, note in enumerate(notes, start=1)
    )


def format_message_role(message: AIContextMessage) -> str:
    if message.sender_type.value == "client":
        return "customer"
    if message.sender_type.value == "operator":
        return "operator"
    return "system"


def format_attachment_hint(attachment: AIContextAttachment | None) -> str:
    if attachment is None:
        return "нет"
    parts = [attachment.kind.value]
    if attachment.filename:
        parts.append(attachment.filename)
    if attachment.mime_type:
        parts.append(attachment.mime_type)
    return ", ".join(parts)


def normalize_inline(value: str, limit: int) -> str:
    normalized = " ".join(escape(value).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"
