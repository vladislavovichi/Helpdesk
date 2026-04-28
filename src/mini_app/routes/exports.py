from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import ParseResult, parse_qs
from uuid import UUID

from application.errors import ValidationAppError
from application.use_cases.analytics.exports import AnalyticsExportFormat, AnalyticsSection
from application.use_cases.tickets.exports import TicketReportFormat
from mini_app.auth import TelegramMiniAppUser
from mini_app.request_parsing import parse_analytics_window
from mini_app.responses import write_binary


def handle_analytics_export(
    handler: Any,
    *,
    user: TelegramMiniAppUser,
    parsed: ParseResult,
) -> None:
    window = parse_analytics_window(parsed)
    query = parse_qs(parsed.query)
    try:
        section = AnalyticsSection(query.get("section", ["overview"])[0])
        analytics_format = AnalyticsExportFormat(query.get("format", ["html"])[0])
    except ValueError as exc:
        raise ValidationAppError("Некорректные параметры экспорта аналитики.") from exc
    write_binary(
        handler,
        asyncio.run(
            handler.gateway.export_analytics(
                user=user,
                window=window,
                section=section,
                format=analytics_format,
            )
        ),
    )


def handle_ticket_export(
    handler: Any,
    *,
    user: TelegramMiniAppUser,
    ticket_public_id: UUID,
    parsed: ParseResult,
) -> None:
    query = parse_qs(parsed.query)
    try:
        ticket_format = TicketReportFormat(query.get("format", ["html"])[0])
    except ValueError as exc:
        raise ValidationAppError("Некорректный формат экспорта заявки.") from exc
    write_binary(
        handler,
        asyncio.run(
            handler.gateway.export_ticket(
                user=user,
                ticket_public_id=ticket_public_id,
                format=ticket_format,
            )
        ),
    )
