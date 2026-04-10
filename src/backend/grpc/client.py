# mypy: disable-error-code="attr-defined,name-defined"
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

import grpc

from application.contracts.actors import RequestActor
from application.contracts.tickets import (
    ApplyMacroToTicketCommand,
    AssignNextQueuedTicketCommand,
    ClientTicketMessageCommand,
    OperatorTicketReplyCommand,
    TicketAssignmentCommand,
)
from application.services.stats import AnalyticsWindow, HelpdeskAnalyticsSnapshot
from application.use_cases.analytics.exports import (
    AnalyticsExportFormat,
    AnalyticsSection,
    AnalyticsSnapshotExport,
)
from application.use_cases.tickets.exports import TicketReportExport, TicketReportFormat
from application.use_cases.tickets.summaries import (
    MacroApplicationResult,
    MacroSummary,
    OperatorReplyResult,
    OperatorTicketSummary,
    QueuedTicketSummary,
    TicketCategorySummary,
    TicketDetailsSummary,
    TicketSummary,
)
from backend.grpc.contracts import HelpdeskBackendClient, HelpdeskBackendClientFactory
from backend.grpc.generated import helpdesk_pb2, helpdesk_pb2_grpc
from backend.grpc.translators import (
    deserialize_analytics_export,
    deserialize_analytics_snapshot,
    deserialize_category,
    deserialize_export,
    deserialize_macro,
    deserialize_macro_application_result,
    deserialize_operator_reply_result,
    deserialize_operator_ticket,
    deserialize_queued_ticket,
    deserialize_ticket_details,
    deserialize_ticket_summary,
    serialize_apply_macro_command,
    serialize_assign_next_command,
    serialize_client_ticket_message_command,
    serialize_operator_reply_command,
    serialize_request_actor,
    serialize_ticket_assignment_command,
)
from domain.tickets import InvalidTicketTransitionError
from infrastructure.config.settings import BackendServiceConfig

CHANNEL_READY_TIMEOUT_SECONDS = 5.0
RPC_TIMEOUT_SECONDS = 10.0


@dataclass(slots=True)
class GrpcHelpdeskBackendClient(HelpdeskBackendClient):
    stub: helpdesk_pb2_grpc.HelpdeskBackendServiceStub

    async def get_backend_status(self) -> tuple[str, str]:
        response = await self.stub.GetBackendStatus(
            helpdesk_pb2.Empty(),
            timeout=RPC_TIMEOUT_SECONDS,
        )
        return response.service, response.status

    async def get_client_active_ticket(self, *, client_chat_id: int) -> TicketSummary | None:
        try:
            result = await self.stub.GetClientActiveTicket(
                helpdesk_pb2.GetClientActiveTicketRequest(client_chat_id=client_chat_id),
                timeout=RPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_summary(result)

    async def list_client_ticket_categories(self) -> tuple[TicketCategorySummary, ...]:
        response = self.stub.ListClientTicketCategories(
            helpdesk_pb2.Empty(),
            timeout=RPC_TIMEOUT_SECONDS,
        )
        return tuple(deserialize_category(item) for item in await _collect_stream(response))

    async def create_ticket_from_client_message(
        self,
        command: ClientTicketMessageCommand,
    ) -> TicketSummary:
        request = helpdesk_pb2.CreateTicketFromClientMessageRequest()
        request.command.CopyFrom(serialize_client_ticket_message_command(command))
        result = await self.stub.CreateTicketFromClientMessage(
            request,
            timeout=RPC_TIMEOUT_SECONDS,
        )
        return deserialize_ticket_summary(result)

    async def create_ticket_from_client_intake(
        self,
        command: ClientTicketMessageCommand,
    ) -> TicketSummary:
        request = helpdesk_pb2.CreateTicketFromClientIntakeRequest()
        request.command.CopyFrom(serialize_client_ticket_message_command(command))
        result = await self.stub.CreateTicketFromClientIntake(
            request,
            timeout=RPC_TIMEOUT_SECONDS,
        )
        return deserialize_ticket_summary(result)

    async def get_ticket_details(
        self,
        *,
        ticket_public_id: UUID,
        actor: RequestActor | None = None,
    ) -> TicketDetailsSummary | None:
        request = helpdesk_pb2.GetTicketDetailsRequest(ticket_public_id=str(ticket_public_id))
        _apply_actor(request, actor)
        try:
            result = await self.stub.GetTicketDetails(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_details(result)

    async def list_queued_tickets(
        self,
        *,
        actor: RequestActor | None = None,
    ) -> tuple[QueuedTicketSummary, ...]:
        request = helpdesk_pb2.ListQueuedTicketsRequest()
        _apply_actor(request, actor)
        response = self.stub.ListQueuedTickets(request, timeout=RPC_TIMEOUT_SECONDS)
        return tuple(deserialize_queued_ticket(item) for item in await _collect_stream(response))

    async def list_operator_tickets(
        self,
        *,
        operator_telegram_user_id: int,
        actor: RequestActor | None = None,
    ) -> tuple[OperatorTicketSummary, ...]:
        request = helpdesk_pb2.ListOperatorTicketsRequest(
            operator_telegram_user_id=operator_telegram_user_id
        )
        _apply_actor(request, actor)
        response = self.stub.ListOperatorTickets(request, timeout=RPC_TIMEOUT_SECONDS)
        return tuple(deserialize_operator_ticket(item) for item in await _collect_stream(response))

    async def assign_next_ticket_to_operator(
        self,
        command: AssignNextQueuedTicketCommand,
        actor: RequestActor | None = None,
    ) -> TicketSummary | None:
        request = helpdesk_pb2.AssignNextQueuedTicketRequest()
        request.command.CopyFrom(serialize_assign_next_command(command))
        _apply_actor(request, actor)
        try:
            result = await self.stub.AssignNextQueuedTicket(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_summary(result)

    async def assign_ticket_to_operator(
        self,
        command: TicketAssignmentCommand,
        actor: RequestActor | None = None,
    ) -> TicketSummary | None:
        request = helpdesk_pb2.AssignTicketToOperatorRequest()
        request.command.CopyFrom(serialize_ticket_assignment_command(command))
        _apply_actor(request, actor)
        try:
            result = await self.stub.AssignTicketToOperator(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_summary(result)

    async def close_ticket(
        self,
        *,
        ticket_public_id: UUID,
    ) -> TicketSummary | None:
        try:
            result = await self.stub.CloseTicket(
                helpdesk_pb2.CloseTicketRequest(ticket_public_id=str(ticket_public_id)),
                timeout=RPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_summary(result)

    async def close_ticket_as_operator(
        self,
        *,
        ticket_public_id: UUID,
        actor: RequestActor | None,
    ) -> TicketSummary | None:
        request = helpdesk_pb2.CloseTicketAsOperatorRequest(ticket_public_id=str(ticket_public_id))
        _apply_actor(request, actor)
        try:
            result = await self.stub.CloseTicketAsOperator(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_ticket_summary(result)

    async def reply_to_ticket_as_operator(
        self,
        command: OperatorTicketReplyCommand,
        actor: RequestActor | None = None,
    ) -> OperatorReplyResult | None:
        request = helpdesk_pb2.ReplyToTicketAsOperatorRequest()
        request.command.CopyFrom(serialize_operator_reply_command(command))
        _apply_actor(request, actor)
        try:
            result = await self.stub.ReplyToTicketAsOperator(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_operator_reply_result(result)

    async def list_macros(
        self,
        *,
        actor: RequestActor | None = None,
    ) -> tuple[MacroSummary, ...]:
        request = helpdesk_pb2.ListMacrosRequest()
        _apply_actor(request, actor)
        response = self.stub.ListMacros(request, timeout=RPC_TIMEOUT_SECONDS)
        return tuple(deserialize_macro(item) for item in await _collect_stream(response))

    async def apply_macro_to_ticket(
        self,
        command: ApplyMacroToTicketCommand,
        actor: RequestActor | None = None,
    ) -> MacroApplicationResult | None:
        request = helpdesk_pb2.ApplyMacroToTicketRequest()
        request.command.CopyFrom(serialize_apply_macro_command(command))
        _apply_actor(request, actor)
        try:
            result = await self.stub.ApplyMacroToTicket(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_macro_application_result(result)

    async def export_ticket_report(
        self,
        *,
        ticket_public_id: UUID,
        format: TicketReportFormat,
        actor: RequestActor | None = None,
    ) -> TicketReportExport | None:
        request = helpdesk_pb2.ExportTicketReportRequest(
            ticket_public_id=str(ticket_public_id),
            format=format.value,
        )
        _apply_actor(request, actor)
        try:
            result = await self.stub.ExportTicketReport(request, timeout=RPC_TIMEOUT_SECONDS)
        except grpc.aio.AioRpcError as exc:
            _raise_optional_rpc_error(exc)
            return None
        return deserialize_export(result)

    async def get_analytics_snapshot(
        self,
        *,
        window: AnalyticsWindow,
        actor: RequestActor | None = None,
    ) -> HelpdeskAnalyticsSnapshot:
        request = helpdesk_pb2.GetAnalyticsSnapshotRequest(window=window.value)
        _apply_actor(request, actor)
        result = await self.stub.GetAnalyticsSnapshot(request, timeout=RPC_TIMEOUT_SECONDS)
        return deserialize_analytics_snapshot(result)

    async def export_analytics_snapshot(
        self,
        *,
        window: AnalyticsWindow,
        section: AnalyticsSection,
        format: AnalyticsExportFormat,
        actor: RequestActor | None = None,
    ) -> AnalyticsSnapshotExport:
        request = helpdesk_pb2.ExportAnalyticsSnapshotRequest(
            window=window.value,
            section=section.value,
            format=format.value,
        )
        _apply_actor(request, actor)
        result = await self.stub.ExportAnalyticsSnapshot(request, timeout=RPC_TIMEOUT_SECONDS)
        return deserialize_analytics_export(result)


def build_helpdesk_backend_client_factory(
    config: BackendServiceConfig,
) -> HelpdeskBackendClientFactory:
    @asynccontextmanager
    async def provide() -> AsyncIterator[HelpdeskBackendClient]:
        channel = grpc.aio.insecure_channel(config.target)
        try:
            await asyncio.wait_for(channel.channel_ready(), timeout=CHANNEL_READY_TIMEOUT_SECONDS)
            yield GrpcHelpdeskBackendClient(
                stub=helpdesk_pb2_grpc.HelpdeskBackendServiceStub(channel)
            )
        finally:
            await channel.close()

    return provide


async def ping_helpdesk_backend(config: BackendServiceConfig) -> bool:
    async with build_helpdesk_backend_client_factory(config)() as client:
        service, status = await client.get_backend_status()
    return service == "helpdesk-backend" and status == "ready"


async def _collect_stream(call: grpc.aio.UnaryStreamCall) -> list[object]:
    items: list[object] = []
    try:
        async for item in call:
            items.append(item)
    except grpc.aio.AioRpcError as exc:
        raise _translate_rpc_error(exc) from exc
    return items


def _apply_actor(message: Any, actor: RequestActor | None) -> None:
    if actor is None:
        return
    message.actor.CopyFrom(serialize_request_actor(actor))


def _raise_optional_rpc_error(exc: grpc.aio.AioRpcError) -> None:
    if exc.code() == grpc.StatusCode.NOT_FOUND:
        return
    raise _translate_rpc_error(exc) from exc


def _translate_rpc_error(exc: grpc.aio.AioRpcError) -> Exception:
    if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
        return InvalidTicketTransitionError(exc.details() or "Недопустимый переход заявки.")
    if exc.code() == grpc.StatusCode.PERMISSION_DENIED:
        return PermissionError(exc.details() or "Недостаточно прав.")
    if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
        return ValueError(exc.details() or "Некорректный запрос.")
    return cast(Exception, exc)
