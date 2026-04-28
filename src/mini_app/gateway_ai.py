from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any
from uuid import UUID


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
