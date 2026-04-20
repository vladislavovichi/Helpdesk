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
            f"Заявка: {command.ticket_public_id}",
            f"Тема: {command.subject}",
            f"Статус: {command.status.value}",
            f"Категория: {command.category_title or 'не указана'}",
            f"Теги: {', '.join(command.tags) if command.tags else 'нет'}",
            "",
            "Полная история сообщений:",
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

    lines: list[str] = []
    for index, message in enumerate(messages, start=1):
        sender = message.sender_label or message.sender_type.value
        attachment_hint = ""
        if message.attachment is not None:
            attachment_hint = (
                f" [вложение: {message.attachment.kind.value}"
                f"{f', {message.attachment.filename}' if message.attachment.filename else ''}]"
            )
        body = message.text or "Сообщение без текста"
        lines.append(f"{index}. {sender}: {normalize_inline(body, 400)}{attachment_hint}")
    return "\n".join(lines)


def format_internal_notes(notes: Sequence[AIContextInternalNote]) -> str:
    if not notes:
        return "Заметок нет."
    return "\n".join(
        f"{index}. {note.author_name or 'оператор'}: {normalize_inline(note.text, 280)}"
        for index, note in enumerate(notes, start=1)
    )


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
