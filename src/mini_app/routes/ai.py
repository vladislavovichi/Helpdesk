from __future__ import annotations

import re

TICKET_AI_SUMMARY_ROUTE = re.compile(r"^/api/tickets/([0-9a-fA-F-]{36})/ai-summary$")
TICKET_AI_REPLY_DRAFT_ROUTE = re.compile(
    r"^/api/tickets/([0-9a-fA-F-]{36})/ai-reply-draft$"
)


def is_ai_route(path: str) -> bool:
    return (
        TICKET_AI_SUMMARY_ROUTE.fullmatch(path) is not None
        or TICKET_AI_REPLY_DRAFT_ROUTE.fullmatch(path) is not None
    )
