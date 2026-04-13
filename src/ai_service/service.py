from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from application.ai.contracts import AIMessage, AIProvider, AIProviderError
from application.ai.summaries import AIPredictionConfidence
from application.contracts.ai import (
    AIContextAttachment,
    AIContextInternalNote,
    AIContextMessage,
    AIGeneratedTicketSummary,
    AIPredictedCategoryResult,
    AIPredictTicketCategoryCommand,
    AISuggestedMacro,
    GeneratedTicketSummaryResult,
    GenerateTicketSummaryCommand,
    SuggestedMacrosResult,
    SuggestMacrosCommand,
)
from infrastructure.config.settings import AIConfig

_SUMMARY_INSTRUCTIONS = (
    "Ты помогаешь оператору русскоязычного helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Тон деловой, спокойный, короткий. "
    "Пиши как внутреннюю support-сводку. Не выдумывай факты. "
    "Если уверенности не хватает, опирайся только на подтверждённые детали из переписки."
)
_MACRO_INSTRUCTIONS = (
    "Ты подбираешь операторские макросы для helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Выбирай только из переданного списка макросов. Не придумывай новые. "
    "Если уверенность слабая, не предлагай макрос. "
    "Причина должна быть одной короткой фразой на русском."
)
_CATEGORY_INSTRUCTIONS = (
    "Ты помогаешь предсказать тему нового обращения в helpdesk. "
    "Верни только JSON без пояснений и markdown. "
    "Выбирай только из переданного списка тем. "
    "Если уверенность низкая, верни отсутствие предсказания. "
    "Значения medium и high используй только при явных признаках."
)


class _TicketSummaryPayload(BaseModel):
    short_summary: str = Field(min_length=8, max_length=280)
    user_goal: str = Field(min_length=4, max_length=280)
    actions_taken: str = Field(min_length=4, max_length=280)
    current_status: str = Field(min_length=4, max_length=280)


class _MacroSuggestionItemPayload(BaseModel):
    macro_id: int
    reason: str = Field(min_length=4, max_length=220)
    confidence: AIPredictionConfidence = AIPredictionConfidence.MEDIUM


class _MacroSuggestionPayload(BaseModel):
    macro_ids: list[_MacroSuggestionItemPayload] = Field(default_factory=list, max_length=3)


class _CategoryPredictionPayload(BaseModel):
    category_id: int | None = None
    confidence: AIPredictionConfidence = AIPredictionConfidence.NONE
    reason: str | None = Field(default=None, max_length=220)


_GENERIC_AI_REASON_TEXTS = {
    "...",
    "не знаю",
    "не уверен",
    "подходит",
    "релевантно",
    "по контексту",
    "по теме",
}


@dataclass(slots=True)
class AIApplicationService:
    provider: AIProvider
    config: AIConfig

    async def generate_ticket_summary(
        self,
        command: GenerateTicketSummaryCommand,
    ) -> GeneratedTicketSummaryResult:
        if not self.provider.is_enabled:
            return _unavailable_summary_result(self.provider.model_id)

        payload = await _complete_json(
            provider=self.provider,
            instructions=_SUMMARY_INSTRUCTIONS,
            prompt=_build_ticket_summary_prompt(command),
            schema=_TicketSummaryPayload,
            max_output_tokens=self.config.summary_max_output_tokens,
            temperature=self.config.summary_temperature,
        )
        if payload is None:
            return GeneratedTicketSummaryResult(
                available=False,
                unavailable_reason="Не удалось подготовить сводку.",
                model_id=self.provider.model_id,
            )
        summary = _build_generated_ticket_summary(payload)
        if summary is None:
            return GeneratedTicketSummaryResult(
                available=False,
                unavailable_reason="Не удалось подготовить достаточно надёжную сводку.",
                model_id=self.provider.model_id,
            )
        return GeneratedTicketSummaryResult(
            available=True,
            summary=summary,
            model_id=self.provider.model_id,
        )

    async def suggest_macros(
        self,
        command: SuggestMacrosCommand,
    ) -> SuggestedMacrosResult:
        if not command.macros:
            return SuggestedMacrosResult(available=True, model_id=self.provider.model_id)
        if not self.provider.is_enabled:
            return _unavailable_macros_result(self.provider.model_id)

        payload = await _complete_json(
            provider=self.provider,
            instructions=_MACRO_INSTRUCTIONS,
            prompt=_build_macro_suggestion_prompt(command),
            schema=_MacroSuggestionPayload,
            max_output_tokens=self.config.macros_max_output_tokens,
            temperature=self.config.macros_temperature,
        )
        if payload is None:
            return SuggestedMacrosResult(
                available=False,
                unavailable_reason="Не удалось подобрать макросы.",
                model_id=self.provider.model_id,
            )
        suggestions = _build_suggested_macros(payload)
        return SuggestedMacrosResult(
            available=True,
            suggestions=suggestions,
            model_id=self.provider.model_id,
        )

    async def predict_ticket_category(
        self,
        command: AIPredictTicketCategoryCommand,
    ) -> AIPredictedCategoryResult:
        if not command.categories or not _has_signal(command):
            return AIPredictedCategoryResult(available=False, model_id=self.provider.model_id)
        if not self.provider.is_enabled:
            return _unavailable_category_result(self.provider.model_id)

        payload = await _complete_json(
            provider=self.provider,
            instructions=_CATEGORY_INSTRUCTIONS,
            prompt=_build_category_prediction_prompt(command),
            schema=_CategoryPredictionPayload,
            max_output_tokens=self.config.category_max_output_tokens,
            temperature=self.config.category_temperature,
        )
        prediction = _build_category_prediction(
            payload,
            command=command,
            model_id=self.provider.model_id,
        )
        if prediction is None:
            return AIPredictedCategoryResult(
                available=False,
                confidence=AIPredictionConfidence.NONE,
                model_id=self.provider.model_id,
            )
        return prediction


async def _complete_json[SchemaT: BaseModel](
    *,
    provider: AIProvider,
    instructions: str,
    prompt: str,
    schema: type[SchemaT],
    max_output_tokens: int,
    temperature: float,
) -> SchemaT | None:
    try:
        raw = await provider.complete(
            messages=(
                AIMessage(role="system", content=instructions),
                AIMessage(role="user", content=prompt),
            ),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    except AIProviderError:
        return None

    payload = _extract_json_object(raw)
    if payload is None:
        return None
    try:
        return schema.model_validate(payload)
    except ValidationError:
        return None


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _build_generated_ticket_summary(
    payload: _TicketSummaryPayload,
) -> AIGeneratedTicketSummary | None:
    short_summary = _normalize_ai_text(payload.short_summary, limit=280)
    user_goal = _normalize_ai_text(payload.user_goal, limit=280)
    actions_taken = _normalize_ai_text(payload.actions_taken, limit=280)
    current_status = _normalize_ai_text(payload.current_status, limit=280)
    if (
        short_summary is None
        or user_goal is None
        or actions_taken is None
        or current_status is None
    ):
        return None

    unique_sections = {short_summary, user_goal, actions_taken, current_status}
    if len(unique_sections) < 3:
        return None

    return AIGeneratedTicketSummary(
        short_summary=short_summary,
        user_goal=user_goal,
        actions_taken=actions_taken,
        current_status=current_status,
    )


def _build_suggested_macros(
    payload: _MacroSuggestionPayload,
) -> tuple[AISuggestedMacro, ...]:
    suggestions: list[AISuggestedMacro] = []
    seen_macro_ids: set[int] = set()
    for item in payload.macro_ids:
        if item.macro_id in seen_macro_ids:
            continue
        if item.confidence not in {AIPredictionConfidence.MEDIUM, AIPredictionConfidence.HIGH}:
            continue
        reason = _normalize_ai_reason(item.reason)
        if reason is None:
            continue
        seen_macro_ids.add(item.macro_id)
        suggestions.append(
            AISuggestedMacro(
                macro_id=item.macro_id,
                reason=reason,
                confidence=item.confidence,
            )
        )
    return tuple(suggestions)


def _build_category_prediction(
    payload: _CategoryPredictionPayload | None,
    *,
    command: AIPredictTicketCategoryCommand,
    model_id: str | None,
) -> AIPredictedCategoryResult | None:
    if payload is None or payload.category_id is None:
        return None
    if payload.confidence not in {AIPredictionConfidence.MEDIUM, AIPredictionConfidence.HIGH}:
        return None
    valid_category_ids = {category.id for category in command.categories}
    if payload.category_id not in valid_category_ids:
        return None
    return AIPredictedCategoryResult(
        available=True,
        category_id=payload.category_id,
        confidence=payload.confidence,
        reason=_normalize_ai_reason(payload.reason),
        model_id=model_id,
    )


def _build_ticket_summary_prompt(command: GenerateTicketSummaryCommand) -> str:
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
            _format_ticket_history(command.message_history),
            "",
            "Внутренние заметки:",
            _format_internal_notes(command.internal_notes),
        ]
    )


def _build_macro_suggestion_prompt(command: SuggestMacrosCommand) -> str:
    macro_lines = [
        f"- id={macro.id}; title={macro.title}; body={_normalize_inline(macro.body, 180)}"
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
            _format_ticket_history(command.message_history),
            "",
            "Доступные макросы:",
            "\n".join(macro_lines),
        ]
    )


def _build_category_prediction_prompt(command: AIPredictTicketCategoryCommand) -> str:
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
            "Вложение: " + _format_attachment_hint(command.attachment),
            "",
            "Темы:",
            "\n".join(category_lines),
        ]
    )


def _format_ticket_history(messages: Sequence[AIContextMessage]) -> str:
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
        lines.append(f"{index}. {sender}: {_normalize_inline(body, 400)}{attachment_hint}")
    return "\n".join(lines)


def _format_internal_notes(notes: Sequence[AIContextInternalNote]) -> str:
    if not notes:
        return "Заметок нет."
    return "\n".join(
        (f"{index}. {note.author_name or 'оператор'}: {_normalize_inline(note.text, 280)}")
        for index, note in enumerate(notes, start=1)
    )


def _format_attachment_hint(attachment: AIContextAttachment | None) -> str:
    if attachment is None:
        return "нет"
    parts = [attachment.kind.value]
    if attachment.filename:
        parts.append(attachment.filename)
    if attachment.mime_type:
        parts.append(attachment.mime_type)
    return ", ".join(parts)


def _normalize_inline(value: str, limit: int) -> str:
    normalized = " ".join(escape(value).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _normalize_ai_text(value: str, *, limit: int) -> str | None:
    normalized = " ".join(value.split())
    if len(normalized) < 4:
        return None
    if normalized.lower() in _GENERIC_AI_REASON_TEXTS:
        return None
    clipped = normalized[:limit].rstrip(" ,;:-")
    if len(clipped) < 4:
        return None
    return clipped


def _normalize_ai_reason(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_ai_text(value, limit=120)
    if normalized is None:
        return None
    return normalized


def _has_signal(command: AIPredictTicketCategoryCommand) -> bool:
    return bool(
        (command.text and command.text.strip())
        or command.attachment is not None
        or any(category.title.strip() for category in command.categories)
    )


def _unavailable_summary_result(model_id: str | None) -> GeneratedTicketSummaryResult:
    return GeneratedTicketSummaryResult(
        available=False,
        unavailable_reason="AI-провайдер не настроен.",
        model_id=model_id,
    )


def _unavailable_macros_result(model_id: str | None) -> SuggestedMacrosResult:
    return SuggestedMacrosResult(
        available=False,
        unavailable_reason="AI-провайдер не настроен.",
        model_id=model_id,
    )


def _unavailable_category_result(model_id: str | None) -> AIPredictedCategoryResult:
    return AIPredictedCategoryResult(
        available=False,
        unavailable_reason="AI-провайдер не настроен.",
        model_id=model_id,
    )
