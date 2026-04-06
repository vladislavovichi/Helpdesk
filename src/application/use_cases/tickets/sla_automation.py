from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application.use_cases.tickets.common import build_status_payload, build_ticket_summary, utcnow
from application.use_cases.tickets.sla_evaluation import (
    evaluate_ticket_sla,
    persist_sla_breach_events,
)
from application.use_cases.tickets.summaries import SLADeadlineStatus, TicketSummary
from domain.contracts.repositories import (
    OperatorRepository,
    SLAPolicyRepository,
    TicketEventRepository,
    TicketRepository,
)
from domain.enums.tickets import TicketEventType


class AutoEscalateTicketBySLAUseCase:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        ticket_event_repository: TicketEventRepository,
        sla_policy_repository: SLAPolicyRepository,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_event_repository = ticket_event_repository
        self.sla_policy_repository = sla_policy_repository

    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
        now: datetime | None = None,
    ) -> TicketSummary | None:
        ticket = await self.ticket_repository.get_by_public_id(ticket_public_id)
        if ticket is None or ticket.id is None:
            return None

        checked_at = now or utcnow()
        policy = await self.sla_policy_repository.get_for_priority(priority=ticket.priority)
        evaluation = evaluate_ticket_sla(ticket=ticket, policy=policy, now=checked_at)
        if not evaluation.should_auto_escalate:
            return None

        await persist_sla_breach_events(
            ticket=ticket,
            evaluation=evaluation,
            policy=policy,
            checked_at=checked_at,
            ticket_event_repository=self.ticket_event_repository,
        )

        previous_status = ticket.status
        escalated_ticket = await self.ticket_repository.escalate(ticket_public_id=ticket_public_id)
        if escalated_ticket is None:
            return None

        reasons = [
            event_type.value
            for event_type, deadline in (
                (TicketEventType.SLA_BREACHED_FIRST_RESPONSE, evaluation.first_response),
                (TicketEventType.SLA_BREACHED_RESOLUTION, evaluation.resolution),
            )
            if deadline.status == SLADeadlineStatus.BREACHED
        ]
        await self.ticket_event_repository.add(
            ticket_id=ticket.id,
            event_type=TicketEventType.AUTO_ESCALATED,
            payload_json={
                **build_status_payload(
                    from_status=previous_status,
                    to_status=escalated_ticket.status,
                    assigned_operator_id=escalated_ticket.assigned_operator_id,
                ),
                "reasons": reasons,
                "checked_at": checked_at.isoformat(),
            },
        )
        return build_ticket_summary(escalated_ticket, event_type=TicketEventType.AUTO_ESCALATED)


class AutoReassignTicketBySLAUseCase:
    def __init__(
        self,
        ticket_repository: TicketRepository,
        ticket_event_repository: TicketEventRepository,
        operator_repository: OperatorRepository,
        sla_policy_repository: SLAPolicyRepository,
    ) -> None:
        self.ticket_repository = ticket_repository
        self.ticket_event_repository = ticket_event_repository
        self.operator_repository = operator_repository
        self.sla_policy_repository = sla_policy_repository

    async def __call__(
        self,
        *,
        ticket_public_id: UUID,
        telegram_user_id: int,
        display_name: str,
        username: str | None = None,
        now: datetime | None = None,
    ) -> TicketSummary | None:
        ticket = await self.ticket_repository.get_by_public_id(ticket_public_id)
        if ticket is None or ticket.id is None:
            return None

        checked_at = now or utcnow()
        policy = await self.sla_policy_repository.get_for_priority(priority=ticket.priority)
        evaluation = evaluate_ticket_sla(ticket=ticket, policy=policy, now=checked_at)
        if not evaluation.should_auto_reassign:
            return None

        operator_id = await self.operator_repository.get_or_create(
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        previous_status = ticket.status
        previous_operator_id = ticket.assigned_operator_id
        if previous_operator_id == operator_id:
            return None

        reassigned_ticket = await self.ticket_repository.assign_to_operator(
            ticket_public_id=ticket_public_id,
            operator_id=operator_id,
        )
        if reassigned_ticket is None:
            return None

        await self.ticket_event_repository.add(
            ticket_id=ticket.id,
            event_type=TicketEventType.AUTO_REASSIGNED,
            payload_json={
                **build_status_payload(
                    from_status=previous_status,
                    to_status=reassigned_ticket.status,
                    assigned_operator_id=operator_id,
                    previous_operator_id=previous_operator_id,
                ),
                "checked_at": checked_at.isoformat(),
                "reason": "stale_assigned_ticket",
            },
        )
        return build_ticket_summary(reassigned_ticket, event_type=TicketEventType.AUTO_REASSIGNED)
