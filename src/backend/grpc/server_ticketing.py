from __future__ import annotations

from uuid import UUID

import grpc

from backend.grpc.generated import helpdesk_pb2
from backend.grpc.server_base import HelpdeskBackendGrpcServiceBase
from backend.grpc.translators import (
    deserialize_add_internal_note_command,
    deserialize_assign_next_command,
    deserialize_client_ticket_message_command,
    deserialize_operator_reply_command,
    deserialize_ticket_assignment_command,
    serialize_access_context,
    serialize_archived_ticket,
    serialize_category,
    serialize_operator_reply_result,
    serialize_operator_ticket,
    serialize_queued_ticket,
    serialize_ticket_details,
    serialize_ticket_summary,
)


class HelpdeskBackendTicketingGrpcMixin(HelpdeskBackendGrpcServiceBase):
    async def GetBackendStatus(
        self,
        request: helpdesk_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.BackendStatus:
        del request
        async with self._rpc_scope(context, method="GetBackendStatus"):
            return helpdesk_pb2.BackendStatus(service="helpdesk-backend", status="ready")

    async def GetAccessContext(
        self,
        request: helpdesk_pb2.GetAccessContextRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.AccessContextSummary:
        async with self._rpc_scope(
            context,
            method="GetAccessContext",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            access_context = await self._invoke_helpdesk(
                context,
                method="GetAccessContext",
                call=lambda helpdesk_service: helpdesk_service.get_access_context(
                    actor=request_context.actor
                ),
            )
            return serialize_access_context(access_context)

    async def GetClientActiveTicket(
        self,
        request: helpdesk_pb2.GetClientActiveTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(context, method="GetClientActiveTicket"):
            ticket = await self._invoke_helpdesk(
                context,
                method="GetClientActiveTicket",
                call=lambda helpdesk_service: helpdesk_service.get_client_active_ticket(
                    client_chat_id=request.client_chat_id
                ),
            )

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
        async with self._rpc_scope(context, method="ListClientTicketCategories"):
            categories = await self._invoke_helpdesk(
                context,
                method="ListClientTicketCategories",
                call=lambda helpdesk_service: helpdesk_service.list_client_ticket_categories(),
            )
            for category in categories:
                yield serialize_category(category)

    async def CreateTicketFromClientMessage(
        self,
        request: helpdesk_pb2.CreateTicketFromClientMessageRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(context, method="CreateTicketFromClientMessage"):
            result = await self._invoke_helpdesk(
                context,
                method="CreateTicketFromClientMessage",
                call=lambda helpdesk_service: helpdesk_service.create_ticket_from_client_message(
                    deserialize_client_ticket_message_command(request.command)
                ),
            )
            return serialize_ticket_summary(result)

    async def CreateTicketFromClientIntake(
        self,
        request: helpdesk_pb2.CreateTicketFromClientIntakeRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(context, method="CreateTicketFromClientIntake"):
            result = await self._invoke_helpdesk(
                context,
                method="CreateTicketFromClientIntake",
                call=lambda helpdesk_service: helpdesk_service.create_ticket_from_client_intake(
                    deserialize_client_ticket_message_command(request.command)
                ),
            )
            return serialize_ticket_summary(result)

    async def GetTicketDetails(
        self,
        request: helpdesk_pb2.GetTicketDetailsRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketDetailsSummary:
        async with self._rpc_scope(
            context,
            method="GetTicketDetails",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            details = await self._invoke_helpdesk(
                context,
                method="GetTicketDetails",
                call=lambda helpdesk_service: helpdesk_service.get_ticket_details(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=request_context.actor,
                ),
            )
            if details is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert details is not None
            return serialize_ticket_details(details)

    async def ListQueuedTickets(
        self,
        request: helpdesk_pb2.ListQueuedTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        async with self._rpc_scope(
            context,
            method="ListQueuedTickets",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            tickets = await self._invoke_helpdesk(
                context,
                method="ListQueuedTickets",
                call=lambda helpdesk_service: helpdesk_service.list_queued_tickets(
                    actor=request_context.actor
                ),
            )
            for ticket in tickets:
                yield serialize_queued_ticket(ticket)

    async def ListOperatorTickets(
        self,
        request: helpdesk_pb2.ListOperatorTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        async with self._rpc_scope(
            context,
            method="ListOperatorTickets",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            tickets = await self._invoke_helpdesk(
                context,
                method="ListOperatorTickets",
                call=lambda helpdesk_service: helpdesk_service.list_operator_tickets(
                    operator_telegram_user_id=request.operator_telegram_user_id,
                    actor=request_context.actor,
                ),
            )
            for ticket in tickets:
                yield serialize_operator_ticket(ticket)

    async def ListArchivedTickets(
        self,
        request: helpdesk_pb2.ListArchivedTicketsRequest,
        context: grpc.aio.ServicerContext,
    ):
        async with self._rpc_scope(
            context,
            method="ListArchivedTickets",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            tickets = await self._invoke_helpdesk(
                context,
                method="ListArchivedTickets",
                call=lambda helpdesk_service: helpdesk_service.list_archived_tickets(
                    actor=request_context.actor
                ),
            )
            for ticket in tickets:
                yield serialize_archived_ticket(ticket)

    async def AssignNextQueuedTicket(
        self,
        request: helpdesk_pb2.AssignNextQueuedTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="AssignNextQueuedTicket",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="AssignNextQueuedTicket",
                call=lambda helpdesk_service: helpdesk_service.assign_next_ticket_to_operator(
                    deserialize_assign_next_command(request.command),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)

    async def AssignTicketToOperator(
        self,
        request: helpdesk_pb2.AssignTicketToOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="AssignTicketToOperator",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="AssignTicketToOperator",
                call=lambda helpdesk_service: helpdesk_service.assign_ticket_to_operator(
                    deserialize_ticket_assignment_command(request.command),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)

    async def CloseTicket(
        self,
        request: helpdesk_pb2.CloseTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="CloseTicket",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="CloseTicket",
                call=lambda helpdesk_service: helpdesk_service.close_ticket(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)

    async def CloseTicketAsOperator(
        self,
        request: helpdesk_pb2.CloseTicketAsOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="CloseTicketAsOperator",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="CloseTicketAsOperator",
                call=lambda helpdesk_service: helpdesk_service.close_ticket_as_operator(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)

    async def EscalateTicketAsOperator(
        self,
        request: helpdesk_pb2.EscalateTicketAsOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="EscalateTicketAsOperator",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="EscalateTicketAsOperator",
                call=lambda helpdesk_service: helpdesk_service.escalate_ticket_as_operator(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)

    async def ReplyToTicketAsOperator(
        self,
        request: helpdesk_pb2.ReplyToTicketAsOperatorRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.OperatorReplyResult:
        async with self._rpc_scope(
            context,
            method="ReplyToTicketAsOperator",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            result = await self._invoke_helpdesk(
                context,
                method="ReplyToTicketAsOperator",
                call=lambda helpdesk_service: helpdesk_service.reply_to_ticket_as_operator(
                    deserialize_operator_reply_command(request.command),
                    actor=request_context.actor,
                ),
            )
            if result is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert result is not None
            return serialize_operator_reply_result(result)

    async def AddInternalNoteToTicket(
        self,
        request: helpdesk_pb2.AddInternalNoteToTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketSummary:
        async with self._rpc_scope(
            context,
            method="AddInternalNoteToTicket",
            fallback_actor=self._request_actor(request),
        ) as request_context:
            ticket = await self._invoke_helpdesk(
                context,
                method="AddInternalNoteToTicket",
                call=lambda helpdesk_service: helpdesk_service.add_internal_note_to_ticket(
                    deserialize_add_internal_note_command(request.command),
                    actor=request_context.actor,
                ),
            )
            if ticket is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Заявка не найдена.")
            assert ticket is not None
            return serialize_ticket_summary(ticket)
