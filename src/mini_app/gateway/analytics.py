from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.services.stats import AnalyticsWindow
from application.use_cases.analytics.exports import AnalyticsExportFormat, AnalyticsSection
from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.responses import BinaryPayload
from mini_app.serializers import serialize_analytics_snapshot


@dataclass(slots=True)
class MiniAppAnalyticsGateway:
    backend_client_factory: HelpdeskBackendClientFactory

    async def get_analytics(
        self,
        *,
        user: TelegramMiniAppUser,
        window: AnalyticsWindow,
    ) -> dict[str, Any]:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            snapshot = await client.get_analytics_snapshot(window=window, actor=actor)
        return {"snapshot": serialize_analytics_snapshot(snapshot)}

    async def export_analytics(
        self,
        *,
        user: TelegramMiniAppUser,
        window: AnalyticsWindow,
        section: AnalyticsSection,
        format: AnalyticsExportFormat,
    ) -> BinaryPayload:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            export = await client.export_analytics_snapshot(
                window=window,
                section=section,
                format=format,
                actor=actor,
            )
        return BinaryPayload(
            filename=export.filename,
            content_type=export.content_type,
            content=export.content,
        )
