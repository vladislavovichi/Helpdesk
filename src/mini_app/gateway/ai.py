from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any
from uuid import UUID

from application.ai.summaries import TicketReplyDraft
from application.errors import NotFoundError
from application.use_cases.ai.settings import AISettingsRepository
from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.serializers import serialize_ticket_ai_snapshot, serialize_ticket_reply_draft


@dataclass(slots=True)
class MiniAppAIRateLimiter:
    summary_limit: int = 3
    reply_draft_limit: int = 5
    window_seconds: int = 60
    _buckets: dict[tuple[str, int, UUID], tuple[float, int]] = field(default_factory=dict)

    async def allow(
        self,
        *,
        operation: str,
        operator_telegram_user_id: int,
        ticket_public_id: UUID,
    ) -> bool:
        limit = self.summary_limit if operation == "summary" else self.reply_draft_limit
        if limit <= 0:
            return False
        now = monotonic()
        key = (operation, operator_telegram_user_id, ticket_public_id)
        window_started_at, count = self._buckets.get(key, (now, 0))
        if now - window_started_at >= self.window_seconds:
            window_started_at = now
            count = 0
        count += 1
        self._buckets[key] = (window_started_at, count)
        self._prune(now)
        return count <= limit

    def _prune(self, now: float) -> None:
        expired = [
            key
            for key, (window_started_at, _count) in self._buckets.items()
            if now - window_started_at >= self.window_seconds
        ]
        for key in expired:
            self._buckets.pop(key, None)


def rate_limited_ai_summary_payload(*, model_id: str | None) -> dict[str, Any]:
    return {
        "available": False,
        "unavailable_reason": "rate_limited",
        "model_id": model_id,
        "short_summary": None,
        "user_goal": None,
        "actions_taken": None,
        "current_status": None,
        "summary_status": "missing",
        "summary_generated_at": None,
        "status_note": None,
        "macro_suggestions": [],
    }


@dataclass(slots=True)
class MiniAppAIGateway:
    backend_client_factory: HelpdeskBackendClientFactory
    ai_settings_repository: AISettingsRepository
    ai_rate_limiter: MiniAppAIRateLimiter

    async def refresh_ticket_ai_summary(
        self,
        *,
        user: TelegramMiniAppUser,
        ticket_public_id: UUID,
    ) -> dict[str, Any]:
        actor = build_actor(user)
        settings = self.ai_settings_repository.get()
        if settings.ai_summaries_enabled and not await self.ai_rate_limiter.allow(
            operation="summary",
            operator_telegram_user_id=user.telegram_user_id,
            ticket_public_id=ticket_public_id,
        ):
            return rate_limited_ai_summary_payload(model_id=settings.default_model_id)
        async with self.backend_client_factory() as client:
            ai_snapshot = await client.get_ticket_ai_assist_snapshot(
                ticket_public_id=ticket_public_id,
                refresh_summary=settings.ai_summaries_enabled,
                actor=actor,
            )
        if ai_snapshot is None:
            raise NotFoundError("Заявка не найдена.")
        serialized = serialize_ticket_ai_snapshot(ai_snapshot)
        if serialized is None:
            raise NotFoundError("Заявка не найдена.")
        return apply_ai_settings_to_snapshot_payload(
            serialized,
            ai_settings_repository=self.ai_settings_repository,
        )

    async def generate_ticket_reply_draft(
        self,
        *,
        user: TelegramMiniAppUser,
        ticket_public_id: UUID,
    ) -> dict[str, Any]:
        actor = build_actor(user)
        settings = self.ai_settings_repository.get()
        if not settings.ai_reply_drafts_enabled:
            return (
                serialize_ticket_reply_draft(
                    TicketReplyDraft(
                        available=False,
                        unavailable_reason="AI reply drafts are disabled by admin settings.",
                        model_id=settings.default_model_id,
                    )
                )
                or {}
            )
        if not await self.ai_rate_limiter.allow(
            operation="reply_draft",
            operator_telegram_user_id=user.telegram_user_id,
            ticket_public_id=ticket_public_id,
        ):
            return (
                serialize_ticket_reply_draft(
                    TicketReplyDraft(
                        available=False,
                        unavailable_reason="rate_limited",
                        model_id=settings.default_model_id,
                    )
                )
                or {}
            )
        async with self.backend_client_factory() as client:
            draft = await client.generate_ticket_reply_draft(
                ticket_public_id=ticket_public_id,
                actor=actor,
            )
        if draft is None:
            raise NotFoundError("Заявка не найдена.")
        serialized = serialize_ticket_reply_draft(draft)
        if serialized is None:
            raise NotFoundError("Заявка не найдена.")
        return serialized


def apply_ai_settings_to_snapshot_payload(
    payload: dict[str, Any],
    *,
    ai_settings_repository: AISettingsRepository,
) -> dict[str, Any]:
    settings = ai_settings_repository.get()
    result = dict(payload)
    notes: list[str] = []
    if not settings.ai_summaries_enabled:
        result["short_summary"] = None
        result["user_goal"] = None
        result["actions_taken"] = None
        result["current_status"] = None
        result["summary_status"] = "missing"
        result["summary_generated_at"] = None
        notes.append("AI summaries are disabled by admin settings.")
    if not settings.ai_macro_suggestions_enabled:
        result["macro_suggestions"] = []
        notes.append("AI macro suggestions are disabled by admin settings.")
    if notes:
        result["status_note"] = " ".join(notes)
        result["unavailable_reason"] = result.get("unavailable_reason") or result["status_note"]
    return result
