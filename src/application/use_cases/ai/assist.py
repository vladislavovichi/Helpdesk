from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application.ai.summaries import (
    AIPredictionConfidence,
    TicketAssistSnapshot,
    TicketCategoryPrediction,
    TicketMacroSuggestion,
    TicketReplyDraft,
    TicketSummaryStatus,
)
from application.contracts.ai import (
    AICategoryOption,
    AIContextAttachment,
    AIContextInternalNote,
    AIContextMessage,
    AIPredictTicketCategoryCommand,
    AIReplyDraftSummaryContext,
    AIServiceClientFactory,
    GeneratedTicketSummaryResult,
    GenerateTicketReplyDraftCommand,
    GenerateTicketSummaryCommand,
    MacroCandidate,
    PredictTicketCategoryCommand,
    SuggestedMacrosResult,
    SuggestMacrosCommand,
)
from application.errors import AIUnavailableError
from application.use_cases.ai.settings import (
    AISettingsProvider,
    InMemoryAISettingsRepository,
    RuntimeAISettings,
)
from application.use_cases.tickets.summaries import MacroSummary, TicketCategorySummary
from domain.contracts.repositories import (
    MacroRepository,
    TicketAISummaryRepository,
    TicketCategoryRepository,
    TicketRepository,
)
from domain.entities.ai import TicketAISummaryDetails
from domain.entities.ticket import TicketAttachmentDetails, TicketDetails, TicketMessageDetails

_MAX_MACRO_REASON_LENGTH = 120
_MAX_CATEGORY_REASON_LENGTH = 120
_AI_GRPC_FAILURES = (AIUnavailableError, TimeoutError, OSError, ConnectionError)


@dataclass(slots=True, frozen=True)
class _SummaryFreshness:
    status: TicketSummaryStatus
    note: str | None = None


@dataclass(slots=True)
class _AssistSnapshotSource:
    ticket: TicketDetails
    stored_summary: TicketAISummaryDetails | None
    macros: tuple[MacroSummary, ...]
    settings: RuntimeAISettings


@dataclass(slots=True)
class _AssistAIResults:
    stored_summary: TicketAISummaryDetails | None
    summary_result: GeneratedTicketSummaryResult | None = None
    macros_result: SuggestedMacrosResult | None = None
    status_note: str | None = None


class BuildTicketAssistSnapshotUseCase:
    def __init__(
        self,
        *,
        ticket_repository: TicketRepository,
        ticket_ai_summary_repository: TicketAISummaryRepository,
        macro_repository: MacroRepository,
        ai_client_factory: AIServiceClientFactory,
        ai_settings_provider: AISettingsProvider | None = None,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_ai_summary_repository = ticket_ai_summary_repository
        self.macro_repository = macro_repository
        self.ai_client_factory = ai_client_factory
        self.ai_settings_provider = ai_settings_provider or InMemoryAISettingsRepository()

    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
        refresh_summary: bool = False,
    ) -> TicketAssistSnapshot | None:
        source = await self._load_snapshot_source(ticket_public_id=ticket_public_id)
        if source is None:
            return None

        results = await self._build_ai_results(source=source, refresh_summary=refresh_summary)
        return self._assemble_snapshot(
            source=source, results=results, refresh_summary=refresh_summary
        )

    async def _load_snapshot_source(
        self,
        *,
        ticket_public_id: UUID,
    ) -> _AssistSnapshotSource | None:
        ticket = await self.ticket_repository.get_details_by_public_id(ticket_public_id)
        if ticket is None:
            return None
        stored_summary = await self.ticket_ai_summary_repository.get_by_ticket_id(
            ticket_id=ticket.id
        )
        return _AssistSnapshotSource(
            ticket=ticket,
            stored_summary=stored_summary,
            macros=await self._list_macros(),
            settings=self.ai_settings_provider.get(),
        )

    async def _build_ai_results(
        self,
        *,
        source: _AssistSnapshotSource,
        refresh_summary: bool,
    ) -> _AssistAIResults:
        results = _AssistAIResults(stored_summary=source.stored_summary)
        try:
            async with self.ai_client_factory() as ai_client:
                if refresh_summary and source.settings.ai_summaries_enabled:
                    summary_result = await ai_client.generate_ticket_summary(
                        _build_generate_ticket_summary_command(
                            source.ticket,
                            settings=source.settings,
                        )
                    )
                    results.summary_result = summary_result
                    if not summary_result.available or summary_result.summary is None:
                        results.status_note = (
                            "Не удалось обновить сводку. Показываю последнюю сохранённую версию."
                            if results.stored_summary is not None
                            else "Сводку сейчас подготовить не удалось."
                        )
                    else:
                        results.stored_summary = await self._persist_generated_summary(
                            ticket=source.ticket,
                            summary_result=summary_result,
                        )
                        results.status_note = "Сводка обновлена по сохранённой переписке."
                elif refresh_summary:
                    results.status_note = "AI-сводки отключены в настройках администратора."

                if source.settings.ai_macro_suggestions_enabled:
                    results.macros_result = await ai_client.suggest_macros(
                        _build_suggest_macros_command(
                            ticket=source.ticket,
                            macros=source.macros,
                            settings=source.settings,
                        )
                    )
                else:
                    results.status_note = results.status_note or "AI-подсказки макросов отключены."
        except _AI_GRPC_FAILURES:
            self._apply_ai_failure_fallback(
                results=results, source=source, refresh_summary=refresh_summary
            )
        return results

    async def _persist_generated_summary(
        self,
        *,
        ticket: TicketDetails,
        summary_result: GeneratedTicketSummaryResult,
    ) -> TicketAISummaryDetails:
        generated_summary = summary_result.summary
        assert generated_summary is not None
        return await self.ticket_ai_summary_repository.upsert(
            ticket_id=ticket.id,
            short_summary=generated_summary.short_summary,
            user_goal=generated_summary.user_goal,
            actions_taken=generated_summary.actions_taken,
            current_status=generated_summary.current_status,
            generated_at=datetime.now(UTC),
            source_ticket_updated_at=ticket.updated_at,
            source_message_count=len(ticket.message_history),
            source_internal_note_count=len(ticket.internal_notes),
            model_id=summary_result.model_id,
        )

    def _apply_ai_failure_fallback(
        self,
        *,
        results: _AssistAIResults,
        source: _AssistSnapshotSource,
        refresh_summary: bool,
    ) -> None:
        if refresh_summary and source.settings.ai_summaries_enabled:
            results.summary_result = GeneratedTicketSummaryResult(
                available=False,
                unavailable_reason=(
                    "Не удалось обновить сводку. Показываю последнюю сохранённую версию."
                    if results.stored_summary is not None
                    else "Сводку сейчас подготовить не удалось."
                ),
                failure_reason="grpc_unavailable",
                model_id=source.settings.default_model_id,
            )
        if source.settings.ai_macro_suggestions_enabled:
            results.macros_result = SuggestedMacrosResult(
                available=False,
                unavailable_reason="Новые AI-подсказки временно недоступны.",
                failure_reason="grpc_unavailable",
                model_id=source.settings.default_model_id,
            )
        results.status_note = results.status_note or (
            "Не удалось обновить сводку. Показываю последнюю сохранённую версию."
            if results.stored_summary is not None
            else "Сводку сейчас подготовить не удалось."
        )

    def _assemble_snapshot(
        self,
        *,
        source: _AssistSnapshotSource,
        results: _AssistAIResults,
        refresh_summary: bool,
    ) -> TicketAssistSnapshot:
        macro_suggestions = _resolve_macro_suggestions(
            macros=source.macros,
            suggestions=(
                () if results.macros_result is None else results.macros_result.suggestions
            ),
        )

        if results.stored_summary is None and _ai_unavailable(
            results.summary_result,
            results.macros_result,
        ):
            return TicketAssistSnapshot(
                available=False,
                unavailable_reason=_resolve_unavailable_reason(
                    results.summary_result,
                    results.macros_result,
                ),
                failure_reason=_resolve_failure_reason(
                    results.summary_result,
                    results.macros_result,
                ),
                model_id=_resolve_model_id(
                    results.summary_result,
                    results.macros_result,
                    results.stored_summary,
                ),
            )

        freshness = _resolve_summary_freshness(
            ticket=source.ticket,
            stored_summary=results.stored_summary,
        )
        status_note = self._resolve_status_note(
            stored_summary=results.stored_summary,
            macros_result=results.macros_result,
            macro_suggestions=macro_suggestions,
            freshness=freshness,
            refresh_summary=refresh_summary,
            status_note=results.status_note,
        )
        stored_summary = results.stored_summary
        macros_result = results.macros_result
        summary_result = results.summary_result
        return TicketAssistSnapshot(
            available=True,
            summary_status=freshness.status,
            summary_generated_at=(
                stored_summary.generated_at if stored_summary is not None else None
            ),
            short_summary=stored_summary.short_summary if stored_summary is not None else None,
            user_goal=stored_summary.user_goal if stored_summary is not None else None,
            actions_taken=stored_summary.actions_taken if stored_summary is not None else None,
            current_status=stored_summary.current_status if stored_summary is not None else None,
            macro_suggestions=macro_suggestions,
            status_note=status_note,
            unavailable_reason=(
                "Новые AI-подсказки временно недоступны."
                if stored_summary is not None
                and macros_result is not None
                and not macros_result.available
                else None
            ),
            failure_reason=_resolve_failure_reason(
                summary_result if _is_unavailable_result(summary_result) else None,
                macros_result if _is_unavailable_result(macros_result) else None,
            ),
            model_id=_resolve_model_id(summary_result, macros_result, stored_summary),
        )

    def _resolve_status_note(
        self,
        *,
        stored_summary: TicketAISummaryDetails | None,
        macros_result: SuggestedMacrosResult | None,
        macro_suggestions: tuple[TicketMacroSuggestion, ...],
        freshness: _SummaryFreshness,
        refresh_summary: bool,
        status_note: str | None,
    ) -> str | None:
        if stored_summary is not None and freshness.note is not None:
            if refresh_summary and status_note is not None:
                return f"{status_note} {freshness.note}"
            if status_note is None:
                return freshness.note
        if (
            stored_summary is None
            and macros_result is not None
            and macros_result.available
            and status_note is None
        ):
            status_note = "Сводка ещё не собрана. При необходимости её можно подготовить вручную."
        if (
            macros_result is not None
            and macros_result.available
            and not macro_suggestions
            and status_note is None
        ):
            status_note = (
                "Точных AI-подсказок по макросам сейчас нет. "
                "Библиотека макросов доступна как обычно."
            )
        if (
            stored_summary is not None
            and macros_result is not None
            and not macros_result.available
            and status_note is None
        ):
            status_note = "Новые AI-подсказки временно недоступны."
        return status_note

    async def _list_macros(self) -> tuple[MacroSummary, ...]:
        return tuple(
            MacroSummary(id=item.id, title=item.title, body=item.body)
            for item in await self.macro_repository.list_all()
        )


class GenerateTicketReplyDraftUseCase:
    def __init__(
        self,
        *,
        ticket_repository: TicketRepository,
        ticket_ai_summary_repository: TicketAISummaryRepository,
        ai_client_factory: AIServiceClientFactory,
        ai_settings_provider: AISettingsProvider | None = None,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_ai_summary_repository = ticket_ai_summary_repository
        self.ai_client_factory = ai_client_factory
        self.ai_settings_provider = ai_settings_provider or InMemoryAISettingsRepository()

    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
    ) -> TicketReplyDraft | None:
        ticket = await self.ticket_repository.get_details_by_public_id(ticket_public_id)
        if ticket is None:
            return None
        settings = self.ai_settings_provider.get()
        if not settings.ai_reply_drafts_enabled:
            return TicketReplyDraft(
                available=False,
                unavailable_reason="AI reply drafts are disabled by admin settings.",
                failure_reason="disabled_by_settings",
                model_id=settings.default_model_id,
            )
        stored_summary = await self.ticket_ai_summary_repository.get_by_ticket_id(
            ticket_id=ticket.id
        )
        try:
            async with self.ai_client_factory() as ai_client:
                result = await ai_client.generate_ticket_reply_draft(
                    _build_generate_ticket_reply_draft_command(
                        ticket=ticket,
                        stored_summary=stored_summary,
                        settings=settings,
                    )
                )
        except _AI_GRPC_FAILURES:
            return TicketReplyDraft(
                available=False,
                unavailable_reason="AI-черновик сейчас недоступен.",
                failure_reason="grpc_unavailable",
                model_id=settings.default_model_id,
            )
        return TicketReplyDraft(
            available=result.available,
            reply_text=result.reply_text,
            tone=result.tone,
            confidence=result.confidence,
            safety_note=result.safety_note,
            missing_information=result.missing_information,
            unavailable_reason=result.unavailable_reason,
            failure_reason=result.failure_reason,
            model_id=result.model_id,
        )


class PredictTicketCategoryUseCase:
    def __init__(
        self,
        *,
        ticket_category_repository: TicketCategoryRepository,
        ai_client_factory: AIServiceClientFactory,
        ai_settings_provider: AISettingsProvider | None = None,
    ) -> None:
        self.ticket_category_repository = ticket_category_repository
        self.ai_client_factory = ai_client_factory
        self.ai_settings_provider = ai_settings_provider or InMemoryAISettingsRepository()

    async def __call__(
        self,
        command: PredictTicketCategoryCommand,
    ) -> TicketCategoryPrediction:
        settings = self.ai_settings_provider.get()
        if not settings.ai_category_prediction_enabled:
            return TicketCategoryPrediction(
                available=False,
                failure_reason="disabled_by_settings",
                model_id=settings.default_model_id,
            )
        categories = await self._list_categories()
        if not categories or not _has_signal(command):
            return TicketCategoryPrediction(available=False)

        try:
            async with self.ai_client_factory() as ai_client:
                result = await ai_client.predict_ticket_category(
                    AIPredictTicketCategoryCommand(
                        text=command.text,
                        attachment=_build_attachment_context_from_prediction(command),
                        categories=tuple(
                            AICategoryOption(
                                id=category.id,
                                code=category.code,
                                title=category.title,
                            )
                            for category in categories
                        ),
                    )
                )
        except _AI_GRPC_FAILURES:
            return TicketCategoryPrediction(
                available=False,
                failure_reason="grpc_unavailable",
                model_id=settings.default_model_id,
            )

        if (
            not result.available
            or result.category_id is None
            or result.confidence
            not in {
                AIPredictionConfidence.MEDIUM,
                AIPredictionConfidence.HIGH,
            }
        ):
            return TicketCategoryPrediction(
                available=False,
                failure_reason=result.failure_reason,
                model_id=result.model_id,
            )

        category = next((item for item in categories if item.id == result.category_id), None)
        if category is None:
            return TicketCategoryPrediction(
                available=False,
                failure_reason=result.failure_reason,
                model_id=result.model_id,
            )

        return TicketCategoryPrediction(
            available=True,
            category_id=category.id,
            category_code=category.code,
            category_title=category.title,
            confidence=result.confidence,
            reason=_normalize_reason_text(result.reason, limit=_MAX_CATEGORY_REASON_LENGTH),
            model_id=result.model_id,
        )

    async def _list_categories(self) -> tuple[TicketCategorySummary, ...]:
        return tuple(
            TicketCategorySummary(
                id=item.id,
                code=item.code,
                title=item.title,
                is_active=item.is_active,
                sort_order=item.sort_order,
            )
            for item in await self.ticket_category_repository.list_all(include_inactive=False)
        )


def _build_generate_ticket_summary_command(
    ticket: TicketDetails,
    *,
    settings: RuntimeAISettings,
) -> GenerateTicketSummaryCommand:
    return GenerateTicketSummaryCommand(
        ticket_public_id=ticket.public_id,
        subject=ticket.subject,
        status=ticket.status,
        category_title=ticket.category_title,
        tags=ticket.tags,
        message_history=tuple(
            _build_message_context(message)
            for message in _limited_messages(ticket.message_history, settings=settings)
        ),
        internal_notes=tuple(
            AIContextInternalNote(
                author_name=note.author_operator_name,
                text=note.text,
                created_at=note.created_at,
            )
            for note in ticket.internal_notes
        ),
    )


def _build_generate_ticket_reply_draft_command(
    *,
    ticket: TicketDetails,
    stored_summary: TicketAISummaryDetails | None,
    settings: RuntimeAISettings,
) -> GenerateTicketReplyDraftCommand:
    summary = None
    if stored_summary is not None:
        freshness = _resolve_summary_freshness(ticket=ticket, stored_summary=stored_summary)
        summary = AIReplyDraftSummaryContext(
            short_summary=stored_summary.short_summary,
            user_goal=stored_summary.user_goal,
            actions_taken=stored_summary.actions_taken,
            current_status=stored_summary.current_status,
            status_note=freshness.note,
        )
    internal_notes = tuple(
        AIContextInternalNote(
            author_name=note.author_operator_name,
            text=note.text,
            created_at=note.created_at,
        )
        for note in ticket.internal_notes
    )
    if settings.reply_draft_tone:
        internal_notes = (
            *internal_notes,
            AIContextInternalNote(
                author_name="AI settings",
                text=f"Preferred reply tone: {settings.reply_draft_tone}.",
                created_at=datetime.now(UTC),
            ),
        )

    return GenerateTicketReplyDraftCommand(
        ticket_public_id=ticket.public_id,
        subject=ticket.subject,
        status=ticket.status,
        category_title=ticket.category_title,
        tags=ticket.tags,
        message_history=tuple(
            _build_message_context(message)
            for message in _limited_messages(ticket.message_history, settings=settings)
        ),
        internal_notes=internal_notes,
        summary=summary,
    )


def _build_suggest_macros_command(
    *,
    ticket: TicketDetails,
    macros: tuple[MacroSummary, ...],
    settings: RuntimeAISettings,
) -> SuggestMacrosCommand:
    return SuggestMacrosCommand(
        ticket_public_id=ticket.public_id,
        subject=ticket.subject,
        status=ticket.status,
        category_title=ticket.category_title,
        tags=ticket.tags,
        message_history=tuple(
            _build_message_context(message)
            for message in _limited_messages(ticket.message_history, settings=settings)
        ),
        macros=tuple(
            MacroCandidate(id=macro.id, title=macro.title, body=macro.body) for macro in macros
        ),
    )


def _limited_messages(
    messages: tuple[TicketMessageDetails, ...],
    *,
    settings: RuntimeAISettings,
) -> tuple[TicketMessageDetails, ...]:
    limit = max(settings.max_history_messages, 1)
    return messages[-limit:]


def _build_message_context(message: TicketMessageDetails) -> AIContextMessage:
    return AIContextMessage(
        sender_type=message.sender_type,
        sender_label=message.sender_operator_name,
        text=message.text,
        created_at=message.created_at,
        attachment=_build_attachment_context(message.attachment),
    )


def _build_attachment_context(
    attachment: TicketAttachmentDetails | None,
) -> AIContextAttachment | None:
    if attachment is None:
        return None
    return AIContextAttachment(
        kind=attachment.kind,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
    )


def _build_attachment_context_from_prediction(
    command: PredictTicketCategoryCommand,
) -> AIContextAttachment | None:
    if command.attachment_kind is None:
        return None
    return AIContextAttachment(
        kind=command.attachment_kind,
        filename=command.attachment_filename,
        mime_type=command.attachment_mime_type,
    )


def _resolve_macro_suggestions(
    *,
    macros: tuple[MacroSummary, ...],
    suggestions: tuple[object, ...],
) -> tuple[TicketMacroSuggestion, ...]:
    macro_by_id = {macro.id: macro for macro in macros}
    result: list[TicketMacroSuggestion] = []
    seen_macro_ids: set[int] = set()
    for suggestion in suggestions:
        macro_id = getattr(suggestion, "macro_id", None)
        if not isinstance(macro_id, int) or macro_id in seen_macro_ids:
            continue
        macro = macro_by_id.get(macro_id)
        if macro is None:
            continue
        confidence = getattr(suggestion, "confidence", AIPredictionConfidence.NONE)
        if confidence not in {AIPredictionConfidence.MEDIUM, AIPredictionConfidence.HIGH}:
            continue
        reason = _normalize_reason_text(
            getattr(suggestion, "reason", None),
            limit=_MAX_MACRO_REASON_LENGTH,
        )
        if reason is None:
            continue
        seen_macro_ids.add(macro_id)
        result.append(
            TicketMacroSuggestion(
                macro_id=macro.id,
                title=macro.title,
                body=macro.body,
                reason=reason,
                confidence=confidence,
            )
        )
    return tuple(result)


def _resolve_summary_freshness(
    *,
    ticket: TicketDetails,
    stored_summary: TicketAISummaryDetails | None,
) -> _SummaryFreshness:
    if stored_summary is None:
        return _SummaryFreshness(status=TicketSummaryStatus.MISSING)

    new_message_count = max(len(ticket.message_history) - stored_summary.source_message_count, 0)
    new_internal_note_count = max(
        len(ticket.internal_notes) - stored_summary.source_internal_note_count,
        0,
    )
    if new_message_count > 0 or new_internal_note_count > 0:
        return _SummaryFreshness(
            status=TicketSummaryStatus.STALE,
            note=_build_stale_summary_note(
                new_message_count=new_message_count,
                new_internal_note_count=new_internal_note_count,
            ),
        )
    if ticket.updated_at > stored_summary.source_ticket_updated_at:
        return _SummaryFreshness(
            status=TicketSummaryStatus.STALE,
            note=(
                "После сводки данные заявки изменились. При необходимости обновите её по переписке."
            ),
        )
    return _SummaryFreshness(status=TicketSummaryStatus.FRESH)


def _build_stale_summary_note(
    *,
    new_message_count: int,
    new_internal_note_count: int,
) -> str:
    changes: list[str] = []
    if new_message_count > 0:
        changes.append(
            _format_change_count(new_message_count, "сообщение", "сообщения", "сообщений")
        )
    if new_internal_note_count > 0:
        changes.append(
            _format_change_count(
                new_internal_note_count,
                "внутренняя заметка",
                "внутренние заметки",
                "внутренних заметок",
            )
        )
    verb = "появилось" if len(changes) == 1 else "появились"
    return f"После последней сводки {verb} {' и '.join(changes)}. Обновите её по переписке."


def _format_change_count(count: int, one: str, few: str, many: str) -> str:
    absolute = abs(count) % 100
    last_digit = absolute % 10
    if 11 <= absolute <= 19:
        word = many
    elif last_digit == 1:
        word = one
    elif 2 <= last_digit <= 4:
        word = few
    else:
        word = many
    return f"{count} {word}"


def _ai_unavailable(summary_result: object | None, macros_result: object | None) -> bool:
    checks = [item for item in (summary_result, macros_result) if item is not None]
    return bool(checks) and not any(bool(getattr(item, "available", False)) for item in checks)


def _is_unavailable_result(result: object | None) -> bool:
    return result is not None and not bool(getattr(result, "available", False))


def _resolve_unavailable_reason(*results: object | None) -> str:
    for result in results:
        reason = getattr(result, "unavailable_reason", None) if result is not None else None
        if isinstance(reason, str) and reason.strip():
            return reason
    return "AI-подсказки сейчас недоступны."


def _resolve_failure_reason(*results: object | None) -> str | None:
    for result in results:
        reason = getattr(result, "failure_reason", None) if result is not None else None
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None


def _resolve_model_id(
    summary_result: object | None,
    macros_result: object | None,
    stored_summary: TicketAISummaryDetails | None,
) -> str | None:
    if stored_summary is not None and stored_summary.model_id is not None:
        return stored_summary.model_id
    for result in (summary_result, macros_result):
        model_id = getattr(result, "model_id", None) if result is not None else None
        if isinstance(model_id, str) and model_id.strip():
            return model_id
    return None


def _normalize_reason_text(value: object, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if normalized.lower() in {
        "...",
        "не знаю",
        "не уверен",
        "подходит",
        "релевантно",
        "по контексту",
        "по теме",
    }:
        return None
    clipped = normalized[:limit].rstrip(" ,;:-")
    return clipped if clipped else None


def _has_signal(command: PredictTicketCategoryCommand) -> bool:
    return bool(
        (command.text and command.text.strip())
        or command.attachment_kind is not None
        or (command.attachment_filename and command.attachment_filename.strip())
    )
