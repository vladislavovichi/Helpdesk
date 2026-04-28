from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.services.stats import AnalyticsWindow
from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.gateway_dashboard import build_operator_dashboard, load_dashboard_ticket_details
from mini_app.serializers import (
    serialize_analytics_snapshot,
    serialize_archived_ticket,
    serialize_operator_ticket,
    serialize_queue_ticket,
)


@dataclass(slots=True)
class MiniAppDashboardGateway:
    backend_client_factory: HelpdeskBackendClientFactory

    async def get_dashboard(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            snapshot = await client.get_analytics_snapshot(
                window=AnalyticsWindow.DAYS_7,
                actor=actor,
            )
            queued = await client.list_queued_tickets(actor=actor)
            mine = await client.list_operator_tickets(
                operator_telegram_user_id=user.telegram_user_id,
                actor=actor,
            )
            archive = await client.list_archived_tickets(actor=actor)
            ticket_details = await load_dashboard_ticket_details(
                client=client,
                actor=actor,
                tickets=[*queued, *mine],
            )

        mine_serialized = [serialize_operator_ticket(item) for item in mine]
        queued_serialized = [serialize_queue_ticket(item) for item in queued]
        archive_serialized = [serialize_archived_ticket(item) for item in archive[:6]]
        escalations = [item for item in mine_serialized if item["status"] == "escalated"]
        operator_dashboard = build_operator_dashboard(
            queued=queued,
            mine=mine,
            ticket_details=ticket_details,
        )

        return {
            "snapshot": serialize_analytics_snapshot(snapshot),
            "queue_preview": queued_serialized[:6],
            "my_tickets_preview": mine_serialized[:6],
            "escalations": escalations[:6],
            "recent_archive": archive_serialized,
            "operator_dashboard": operator_dashboard,
            "buckets": operator_dashboard["buckets"],
            "sections": operator_dashboard["sections"],
        }

    async def get_operator_dashboard(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        return await self.get_dashboard(user=user)
