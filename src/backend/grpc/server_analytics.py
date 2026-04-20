from __future__ import annotations

from uuid import UUID

import grpc

from application.services.stats import AnalyticsWindow
from application.use_cases.analytics.exports import AnalyticsExportFormat, AnalyticsSection
from application.use_cases.tickets.exports import TicketReportFormat
from backend.grpc.generated import helpdesk_pb2
from backend.grpc.server_base import HelpdeskBackendGrpcServiceBase
from backend.grpc.translators import (
    serialize_analytics_export,
    serialize_analytics_snapshot,
    serialize_export,
)


class HelpdeskBackendAnalyticsGrpcMixin(HelpdeskBackendGrpcServiceBase):
    async def ExportTicketReport(
        self,
        request: helpdesk_pb2.ExportTicketReportRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketReportExport:
        async with self._rpc_scope(
            context,
            method="ExportTicketReport",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            export = await self._invoke_helpdesk(
                context,
                method="ExportTicketReport",
                call=lambda helpdesk_service: helpdesk_service.export_ticket_report(
                    ticket_public_id=UUID(request.ticket_public_id),
                    format=TicketReportFormat(request.format),
                    actor=request_context.actor,
                ),
            )
            if export is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert export is not None
            return serialize_export(export)

    async def GetAnalyticsSnapshot(
        self,
        request: helpdesk_pb2.GetAnalyticsSnapshotRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.HelpdeskAnalyticsSnapshot:
        async with self._rpc_scope(
            context,
            method="GetAnalyticsSnapshot",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            snapshot = await self._invoke_helpdesk(
                context,
                method="GetAnalyticsSnapshot",
                call=lambda helpdesk_service: helpdesk_service.get_analytics_snapshot(
                    window=AnalyticsWindow(request.window),
                    actor=request_context.actor,
                ),
            )
            return serialize_analytics_snapshot(snapshot)

    async def ExportAnalyticsSnapshot(
        self,
        request: helpdesk_pb2.ExportAnalyticsSnapshotRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.AnalyticsReportExport:
        async with self._rpc_scope(
            context,
            method="ExportAnalyticsSnapshot",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            export = await self._invoke_helpdesk(
                context,
                method="ExportAnalyticsSnapshot",
                call=lambda helpdesk_service: helpdesk_service.export_analytics_snapshot(
                    window=AnalyticsWindow(request.window),
                    section=AnalyticsSection(request.section),
                    format=AnalyticsExportFormat(request.format),
                    actor=request_context.actor,
                ),
            )
            return serialize_analytics_export(export)
