from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.use_cases.tickets.exports import TicketReportFormat
from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.responses import BinaryPayload


@dataclass(slots=True)
class MiniAppExportsGateway:
    backend_client_factory: HelpdeskBackendClientFactory

    async def export_ticket(
        self,
        *,
        user: TelegramMiniAppUser,
        ticket_public_id: UUID,
        format: TicketReportFormat,
    ) -> BinaryPayload:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            export = await client.export_ticket_report(
                ticket_public_id=ticket_public_id,
                format=format,
                actor=actor,
            )
        if export is None:
            from application.errors import NotFoundError

            raise NotFoundError("Заявка не найдена.")
        return BinaryPayload(
            filename=export.filename,
            content_type=export.content_type,
            content=export.content,
        )
