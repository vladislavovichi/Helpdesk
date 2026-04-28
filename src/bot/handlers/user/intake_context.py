from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.grpc.contracts import HelpdeskBackendClientFactory
from infrastructure.redis.contracts import (
    ChatRateLimiter,
    GlobalRateLimiter,
    OperatorActiveTicketStore,
    TicketLiveSessionStore,
    TicketStreamPublisher,
)


@dataclass(slots=True, frozen=True)
class TicketRuntimeContext:
    helpdesk_backend_client_factory: HelpdeskBackendClientFactory
    operator_active_ticket_store: OperatorActiveTicketStore
    ticket_live_session_store: TicketLiveSessionStore
    ticket_stream_publisher: TicketStreamPublisher
    logger: logging.Logger


@dataclass(slots=True, frozen=True)
class ClientIntakeContext:
    ticket_runtime: TicketRuntimeContext
    global_rate_limiter: GlobalRateLimiter
    chat_rate_limiter: ChatRateLimiter

    @property
    def helpdesk_backend_client_factory(self) -> HelpdeskBackendClientFactory:
        return self.ticket_runtime.helpdesk_backend_client_factory
