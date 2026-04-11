# mypy: disable-error-code="attr-defined,name-defined,no-untyped-def"
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import grpc

from application.services.helpdesk.service import HelpdeskServiceFactory
from application.services.stats import AnalyticsWindow
from application.use_cases.analytics.exports import AnalyticsExportFormat, AnalyticsSection
from application.use_cases.tickets.exports import TicketReportFormat
from backend.grpc.generated import helpdesk_pb2, helpdesk_pb2_grpc
from backend.grpc.translators import (
    deserialize_apply_macro_command,
    deserialize_assign_next_command,
    deserialize_client_ticket_message_command,
    deserialize_operator_reply_command,
    deserialize_request_actor,
    deserialize_ticket_assignment_command,
    serialize_analytics_export,
    serialize_analytics_snapshot,
    serialize_archived_ticket,
    serialize_category,
    serialize_export,
    serialize_macro,
    serialize_macro_application_result,
    serialize_operator_reply_result,
    serialize_operator_ticket,
    serialize_queued_ticket,
    serialize_ticket_details,
    serialize_ticket_summary,
)
from domain.tickets import InvalidTicketTransitionError


@dataclass(slots=True)
class HelpdeskBackendGrpcService(helpdesk_pb2_grpc.HelpdeskBackendServiceServicer):
    helpdesk_service_factory: HelpdeskServiceFactory

    async def GetBackendStatus(
        self,
        request: helpdesk_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.BackendStatus:
        del request, context
        return helpdesk_pb2.BackendStatus(service="helpdesk-backend", status="ready")

    async def GetClientActiveTicket(
        self,
        request: helpdesk_pb2.GetClientActiveTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                ticket = await helpdesk_service.get_client_active_ticket(
                    client_chat_id=request.client_chat_id
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if ticket is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Активная заявка не найдена.")
        assert ticket is not None
        return serialize_ticket_summary(ticket)

    async def ListClientTicketCategories(
        self,
        request: helpdesk_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ):
        del request
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                categories = await helpdesk_service.list_client_ticket_categories()
        except Exception as exc:
            await _abort_for_exception(context, exc)

        for category in categories:
            yield serialize_category(category)

    async def CreateTicketFromClientMessage(
        self,
        request: helpdesk_pb2.CreateTicketFromClientMessageRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                result = await helpdesk_service.create_ticket_from_client_message(
                    deserialize_client_ticket_message_command(request.command)
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        return serialize_ticket_summary(result)

    async def CreateTicketFromClientIntake(
        self,
        request: helpdesk_pb2.CreateTicketFromClientIntakeRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                result = await helpdesk_service.create_ticket_from_client_intake(
                    deserialize_client_ticket_message_command(request.command)
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        return serialize_ticket_summary(result)

    async def GetTicketDetails(
        self,
        request: helpdesk_pb2.GetTicketDetailsRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketDetailsSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                details = await helpdesk_service.get_ticket_details(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if details is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert details is not None
        return serialize_ticket_details(details)

    async def ListQueuedTickets(
        self,
        request: helpdesk_pb2.ListQueuedTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                tickets = await helpdesk_service.list_queued_tickets(actor=_request_actor(request))
        except Exception as exc:
            await _abort_for_exception(context, exc)

        for ticket in tickets:
            yield serialize_queued_ticket(ticket)

    async def ListOperatorTickets(
        self,
        request: helpdesk_pb2.ListOperatorTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                tickets = await helpdesk_service.list_operator_tickets(
                    operator_telegram_user_id=request.operator_telegram_user_id,
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        for ticket in tickets:
            yield serialize_operator_ticket(ticket)

    async def ListArchivedTickets(
        self,
        request: helpdesk_pb2.ListArchivedTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                tickets = await helpdesk_service.list_archived_tickets(
                    actor=_request_actor(request)
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        for ticket in tickets:
            yield serialize_archived_ticket(ticket)

    async def AssignNextQueuedTicket(
        self,
        request: helpdesk_pb2.AssignNextQueuedTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                ticket = await helpdesk_service.assign_next_ticket_to_operator(
                    deserialize_assign_next_command(request.command),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if ticket is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert ticket is not None
        return serialize_ticket_summary(ticket)

    async def AssignTicketToOperator(
        self,
        request: helpdesk_pb2.AssignTicketToOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                ticket = await helpdesk_service.assign_ticket_to_operator(
                    deserialize_ticket_assignment_command(request.command),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if ticket is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert ticket is not None
        return serialize_ticket_summary(ticket)

    async def CloseTicket(
        self,
        request: helpdesk_pb2.CloseTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                ticket = await helpdesk_service.close_ticket(
                    ticket_public_id=UUID(request.ticket_public_id)
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if ticket is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert ticket is not None
        return serialize_ticket_summary(ticket)

    async def CloseTicketAsOperator(
        self,
        request: helpdesk_pb2.CloseTicketAsOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                ticket = await helpdesk_service.close_ticket_as_operator(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if ticket is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert ticket is not None
        return serialize_ticket_summary(ticket)

    async def ReplyToTicketAsOperator(
        self,
        request: helpdesk_pb2.ReplyToTicketAsOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.OperatorReplyResult:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                result = await helpdesk_service.reply_to_ticket_as_operator(
                    deserialize_operator_reply_command(request.command),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if result is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert result is not None
        return serialize_operator_reply_result(result)

    async def ListMacros(
        self,
        request: helpdesk_pb2.ListMacrosRequest,
        context: grpc.aio.ServicerContext,
    ):
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                macros = await helpdesk_service.list_macros(actor=_request_actor(request))
        except Exception as exc:
            await _abort_for_exception(context, exc)

        for macro in macros:
            yield serialize_macro(macro)

    async def ApplyMacroToTicket(
        self,
        request: helpdesk_pb2.ApplyMacroToTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.MacroApplicationResult:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                result = await helpdesk_service.apply_macro_to_ticket(
                    deserialize_apply_macro_command(request.command),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if result is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert result is not None
        return serialize_macro_application_result(result)

    async def ExportTicketReport(
        self,
        request: helpdesk_pb2.ExportTicketReportRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketReportExport:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                export = await helpdesk_service.export_ticket_report(
                    ticket_public_id=UUID(request.ticket_public_id),
                    format=TicketReportFormat(request.format),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        if export is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
        assert export is not None
        return serialize_export(export)

    async def GetAnalyticsSnapshot(
        self,
        request: helpdesk_pb2.GetAnalyticsSnapshotRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.HelpdeskAnalyticsSnapshot:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                snapshot = await helpdesk_service.get_analytics_snapshot(
                    window=AnalyticsWindow(request.window),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        return serialize_analytics_snapshot(snapshot)

    async def ExportAnalyticsSnapshot(
        self,
        request: helpdesk_pb2.ExportAnalyticsSnapshotRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.AnalyticsReportExport:
        try:
            async with self.helpdesk_service_factory() as helpdesk_service:
                export = await helpdesk_service.export_analytics_snapshot(
                    window=AnalyticsWindow(request.window),
                    section=AnalyticsSection(request.section),
                    format=AnalyticsExportFormat(request.format),
                    actor=_request_actor(request),
                )
        except Exception as exc:
            await _abort_for_exception(context, exc)

        return serialize_analytics_export(export)


@dataclass(slots=True)
class HelpdeskBackendGrpcServer:
    helpdesk_service_factory: HelpdeskServiceFactory
    bind_target: str
    server: grpc.aio.Server = field(init=False)
    bound_port: int = field(init=False)

    def __post_init__(self) -> None:
        self.server = grpc.aio.server()
        helpdesk_pb2_grpc.add_HelpdeskBackendServiceServicer_to_server(
            HelpdeskBackendGrpcService(self.helpdesk_service_factory),
            self.server,
        )
        self.bound_port = self.server.add_insecure_port(self.bind_target)
        if self.bound_port == 0:
            raise RuntimeError(f"Не удалось открыть gRPC порт {self.bind_target}.")

    async def start(self) -> None:
        await self.server.start()

    async def stop(self, grace: float = 5.0) -> None:
        await self.server.stop(grace)

    async def wait_for_termination(self) -> None:
        await self.server.wait_for_termination()


def build_helpdesk_backend_server(
    *,
    helpdesk_service_factory: HelpdeskServiceFactory,
    bind_target: str,
) -> HelpdeskBackendGrpcServer:
    return HelpdeskBackendGrpcServer(
        helpdesk_service_factory=helpdesk_service_factory,
        bind_target=bind_target,
    )


async def _abort_for_exception(
    context: grpc.aio.ServicerContext,
    exc: Exception,
) -> None:
    if isinstance(exc, InvalidTicketTransitionError):
        await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
    if isinstance(exc, PermissionError):
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
    if isinstance(exc, ValueError):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
    await context.abort(grpc.StatusCode.INTERNAL, "Внутренняя ошибка backend сервиса.")


def _request_actor(request: Any):
    if request.HasField("actor"):
        return deserialize_request_actor(request.actor)
    return None
