# mypy: disable-error-code="attr-defined,name-defined"
from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import grpc

from backend.grpc.generated import helpdesk_pb2
from backend.grpc.server_base import HelpdeskBackendGrpcServiceBase
from backend.grpc.translators import (
    deserialize_apply_macro_command,
    deserialize_predict_ticket_category_command,
    serialize_macro,
    serialize_macro_application_result,
    serialize_operator_invite_summary,
    serialize_operator_summary,
    serialize_ticket_assist_snapshot,
    serialize_ticket_category_prediction,
    serialize_ticket_reply_draft,
)


class HelpdeskBackendOperationsGrpcMixin(HelpdeskBackendGrpcServiceBase):
    async def ListOperators(
        self,
        request: helpdesk_pb2.ListOperatorsRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[helpdesk_pb2.OperatorSummary]:
        async for operator in self._stream_rpc(
            context,
            method="ListOperators",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: helpdesk_service.list_operators(
                actor=request_context.actor
            ),
            serialize=serialize_operator_summary,
        ):
            yield operator

    async def CreateOperatorInvite(
        self,
        request: helpdesk_pb2.CreateOperatorInviteRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.OperatorInviteCodeSummary:
        return await self._unary_rpc(
            context,
            method="CreateOperatorInvite",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: helpdesk_service.create_operator_invite(
                actor=request_context.actor
            ),
            serialize=serialize_operator_invite_summary,
        )

    async def ListMacros(
        self,
        request: helpdesk_pb2.ListMacrosRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[helpdesk_pb2.MacroSummary]:
        async for macro in self._stream_rpc(
            context,
            method="ListMacros",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: helpdesk_service.list_macros(
                actor=request_context.actor
            ),
            serialize=serialize_macro,
        ):
            yield macro

    async def ApplyMacroToTicket(
        self,
        request: helpdesk_pb2.ApplyMacroToTicketRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.MacroApplicationResult:
        return await self._optional_unary_rpc(
            context,
            method="ApplyMacroToTicket",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: helpdesk_service.apply_macro_to_ticket(
                deserialize_apply_macro_command(request.command),
                actor=request_context.actor,
            ),
            serialize=serialize_macro_application_result,
            not_found_message="Заявка не найдена.",
        )

    async def GetTicketAssistSnapshot(
        self,
        request: helpdesk_pb2.GetTicketAssistSnapshotRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketAssistSnapshot:
        return await self._optional_unary_rpc(
            context,
            method="GetTicketAssistSnapshot",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: (
                helpdesk_service.get_ticket_ai_assist_snapshot(
                    ticket_public_id=UUID(request.ticket_public_id),
                    refresh_summary=request.refresh_summary,
                    actor=request_context.actor,
                )
            ),
            serialize=serialize_ticket_assist_snapshot,
            not_found_message="Заявка не найдена.",
        )

    async def GenerateTicketReplyDraft(
        self,
        request: helpdesk_pb2.GenerateTicketReplyDraftRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketReplyDraft:
        return await self._optional_unary_rpc(
            context,
            method="GenerateTicketReplyDraft",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: (
                helpdesk_service.generate_ticket_reply_draft(
                    ticket_public_id=UUID(request.ticket_public_id),
                    actor=request_context.actor,
                )
            ),
            serialize=serialize_ticket_reply_draft,
            not_found_message="Заявка не найдена.",
        )

    async def PredictTicketCategory(
        self,
        request: helpdesk_pb2.PredictTicketCategoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> helpdesk_pb2.TicketCategoryPrediction:
        return await self._unary_rpc(
            context,
            method="PredictTicketCategory",
            fallback_actor=self._request_actor(request),
            call=lambda helpdesk_service, request_context: helpdesk_service.predict_ticket_category(
                deserialize_predict_ticket_category_command(request.command),
                actor=request_context.actor,
            ),
            serialize=serialize_ticket_category_prediction,
        )
