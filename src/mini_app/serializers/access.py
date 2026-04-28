from __future__ import annotations

from typing import Any

from application.use_cases.tickets.summaries import AccessContextSummary


def serialize_access_context(access_context: AccessContextSummary) -> dict[str, Any]:
    return {
        "telegram_user_id": access_context.telegram_user_id,
        "role": access_context.role.value,
    }
