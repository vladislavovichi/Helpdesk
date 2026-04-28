from __future__ import annotations

from typing import Any

from application.use_cases.ai.settings import RuntimeAISettings
from application.use_cases.tickets.operator_invites import OperatorInviteCodeSummary
from application.use_cases.tickets.summaries import OperatorSummary
from mini_app.serializers.common import normalize_bot_username, serialize_datetime


def serialize_ai_settings(settings: RuntimeAISettings) -> dict[str, Any]:
    return {
        "ai_summaries_enabled": settings.ai_summaries_enabled,
        "ai_macro_suggestions_enabled": settings.ai_macro_suggestions_enabled,
        "ai_reply_drafts_enabled": settings.ai_reply_drafts_enabled,
        "ai_category_prediction_enabled": settings.ai_category_prediction_enabled,
        "default_model_id": settings.default_model_id,
        "max_history_messages": settings.max_history_messages,
        "reply_draft_tone": settings.reply_draft_tone,
        "operator_must_review_ai": settings.operator_must_review_ai,
    }


def serialize_operator(operator: OperatorSummary) -> dict[str, Any]:
    return {
        "telegram_user_id": operator.telegram_user_id,
        "display_name": operator.display_name,
        "username": operator.username,
        "is_active": operator.is_active,
    }


def serialize_operator_invite(
    invite: OperatorInviteCodeSummary,
    *,
    bot_username: str | None = None,
) -> dict[str, Any]:
    normalized_bot_username = normalize_bot_username(bot_username)
    telegram_deep_link = (
        f"https://t.me/{normalized_bot_username}?start={invite.code}"
        if normalized_bot_username
        else None
    )
    return {
        "code": invite.code,
        "expires_at": serialize_datetime(invite.expires_at),
        "max_uses": invite.max_uses,
        "bot_username": normalized_bot_username,
        "telegram_deep_link": telegram_deep_link,
        "link_available": telegram_deep_link is not None,
        "link_unavailable_reason": None if telegram_deep_link else "bot_username_missing",
    }
