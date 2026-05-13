from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest

from application.use_cases.tickets import sla_automation, sla_batch
from application.use_cases.tickets.sla_evaluation import build_stale_assignment_window
from application.use_cases.tickets.summaries import (
    SLAAutoReassignmentTarget,
    TicketSLAEvaluationSummary,
)
from domain.contracts.repositories import SLAPolicyRecord
from domain.entities.ticket import Ticket
from domain.enums.tickets import TicketEventType, TicketStatus

from .test_helpdesk_service import (
    StubTicketRepository,
    build_event_repository_mock,
    build_operator_repository_mock,
    build_service,
    build_sla_policy_repository_mock,
    build_ticket,
)


@pytest.mark.parametrize(
    ("first_response_minutes", "resolution_minutes", "expected_minutes"),
    [
        (30, 120, 30),
        (5, 20, 15),
        (30, 40, 30),
        (60, 25, 25),
        (10, 200, 50),
    ],
)
def test_build_stale_assignment_window_preserves_current_formula(
    first_response_minutes: int,
    resolution_minutes: int,
    expected_minutes: int,
) -> None:
    policy = cast(
        SLAPolicyRecord,
        SimpleNamespace(
            id=1,
            name="Default",
            first_response_minutes=first_response_minutes,
            resolution_minutes=resolution_minutes,
            priority=None,
        ),
    )

    assert build_stale_assignment_window(policy) == timedelta(minutes=expected_minutes)


async def test_evaluate_ticket_sla_state_detects_approaching_deadlines() -> None:
    public_id = uuid4()
    now = datetime.now(UTC)
    ticket = build_ticket(
        ticket_id=1,
        public_id=public_id,
        status=TicketStatus.QUEUED,
        created_at=now - timedelta(minutes=26),
        updated_at=now - timedelta(minutes=5),
    )
    service = build_service(
        ticket_repository=StubTicketRepository(created_ticket=ticket),
        sla_policy_repository=build_sla_policy_repository_mock(
            policies={
                None: SimpleNamespace(
                    id=1,
                    name="Default",
                    first_response_minutes=30,
                    resolution_minutes=240,
                    priority=None,
                )
            }
        ),
    )

    result = await service.evaluate_ticket_sla_state(
        ticket_public_id=public_id,
        now=now,
    )

    assert result is not None
    assert result.policy_name == "Default"
    assert result.first_response.status.value == "approaching"
    assert result.resolution.status.value == "ok"
    assert result.should_auto_escalate is False
    assert result.should_auto_reassign is False


async def test_auto_escalate_ticket_by_sla_persists_breach_and_auto_escalated_events() -> None:
    public_id = uuid4()
    now = datetime.now(UTC)
    ticket = build_ticket(
        ticket_id=1,
        public_id=public_id,
        status=TicketStatus.ASSIGNED,
        assigned_operator_id=7,
        created_at=now - timedelta(minutes=90),
        updated_at=now - timedelta(minutes=45),
    )
    event_repository = build_event_repository_mock()
    service = build_service(
        ticket_repository=StubTicketRepository(created_ticket=ticket),
        event_repository=event_repository,
        sla_policy_repository=build_sla_policy_repository_mock(
            policies={
                None: SimpleNamespace(
                    id=1,
                    name="Default",
                    first_response_minutes=30,
                    resolution_minutes=240,
                    priority=None,
                )
            }
        ),
    )

    result = await service.auto_escalate_ticket_by_sla(
        ticket_public_id=public_id,
        now=now,
    )

    assert result is not None
    assert result.status == TicketStatus.ESCALATED
    assert result.event_type == TicketEventType.AUTO_ESCALATED
    assert [event["event_type"] for event in event_repository.added_events] == [
        TicketEventType.SLA_BREACHED_FIRST_RESPONSE,
        TicketEventType.AUTO_ESCALATED,
    ]


async def test_auto_reassign_ticket_by_sla_requires_stale_assignment() -> None:
    public_id = uuid4()
    now = datetime.now(UTC)
    ticket = build_ticket(
        ticket_id=1,
        public_id=public_id,
        status=TicketStatus.ASSIGNED,
        assigned_operator_id=7,
        created_at=now - timedelta(minutes=35),
        updated_at=now - timedelta(minutes=31),
        first_response_at=now - timedelta(minutes=34),
    )
    event_repository = build_event_repository_mock()
    service = build_service(
        ticket_repository=StubTicketRepository(created_ticket=ticket),
        event_repository=event_repository,
        operator_repository=build_operator_repository_mock({1002: 9}),
        sla_policy_repository=build_sla_policy_repository_mock(
            policies={
                None: SimpleNamespace(
                    id=1,
                    name="Default",
                    first_response_minutes=30,
                    resolution_minutes=120,
                    priority=None,
                )
            }
        ),
    )

    result = await service.auto_reassign_ticket_by_sla(
        ticket_public_id=public_id,
        telegram_user_id=1002,
        display_name="Operator Two",
        now=now,
    )

    assert result is not None
    assert result.status == TicketStatus.ASSIGNED
    assert result.event_type == TicketEventType.AUTO_REASSIGNED
    assert ticket.assigned_operator_id == 9
    assert [event["event_type"] for event in event_repository.added_events] == [
        TicketEventType.AUTO_REASSIGNED,
    ]


async def test_run_ticket_sla_checks_processes_escalation_and_reassignment_paths() -> None:
    now = datetime.now(UTC)
    escalated_ticket = build_ticket(
        ticket_id=1,
        public_id=uuid4(),
        status=TicketStatus.QUEUED,
        created_at=now - timedelta(minutes=45),
        updated_at=now - timedelta(minutes=45),
    )
    stale_ticket = build_ticket(
        ticket_id=2,
        public_id=uuid4(),
        status=TicketStatus.ASSIGNED,
        assigned_operator_id=7,
        created_at=now - timedelta(minutes=50),
        updated_at=now - timedelta(minutes=31),
        first_response_at=now - timedelta(minutes=49),
    )
    ticket_repository = StubTicketRepository(
        created_ticket=escalated_ticket,
        queued_tickets=[stale_ticket],
    )
    event_repository = build_event_repository_mock()
    sla_policy_repository = build_sla_policy_repository_mock(
        policies={
            None: SimpleNamespace(
                id=1,
                name="Default",
                first_response_minutes=30,
                resolution_minutes=120,
                priority=None,
            )
        }
    )
    service = build_service(
        ticket_repository=ticket_repository,
        event_repository=event_repository,
        operator_repository=build_operator_repository_mock({2001: 11}),
        sla_policy_repository=sla_policy_repository,
    )
    original_batch_evaluator = sla_batch.evaluate_ticket_sla
    original_automation_evaluator = sla_automation.evaluate_ticket_sla
    evaluated_ticket_public_ids: list[UUID] = []

    def count_batch_evaluation(
        *,
        ticket: Ticket,
        policy: SLAPolicyRecord | None,
        now: datetime,
    ) -> TicketSLAEvaluationSummary:
        evaluated_ticket_public_ids.append(ticket.public_id)
        return original_batch_evaluator(ticket=ticket, policy=policy, now=now)

    def count_automation_evaluation(
        *,
        ticket: Ticket,
        policy: SLAPolicyRecord | None,
        now: datetime,
    ) -> TicketSLAEvaluationSummary:
        del policy, now
        raise AssertionError(f"SLA was re-evaluated during automation for {ticket.public_id}")

    sla_batch.evaluate_ticket_sla = count_batch_evaluation
    sla_automation.evaluate_ticket_sla = count_automation_evaluation

    try:
        result = await service.run_ticket_sla_checks(
            now=now,
            reassignment_targets=(
                SLAAutoReassignmentTarget(
                    ticket_public_id=stale_ticket.public_id,
                    telegram_user_id=2001,
                    display_name="Operator Eleven",
                    username="operator11",
                ),
            ),
        )
    finally:
        sla_batch.evaluate_ticket_sla = original_batch_evaluator
        sla_automation.evaluate_ticket_sla = original_automation_evaluator

    assert result.evaluated_count == 2
    assert result.auto_escalated_count == 1
    assert result.auto_reassigned_count == 1
    assert escalated_ticket.status == TicketStatus.ESCALATED
    assert stale_ticket.assigned_operator_id == 11
    assert sla_policy_repository.calls == [escalated_ticket.priority]
    assert evaluated_ticket_public_ids == [escalated_ticket.public_id, stale_ticket.public_id]
    assert [event["event_type"] for event in event_repository.added_events] == [
        TicketEventType.SLA_BREACHED_FIRST_RESPONSE,
        TicketEventType.AUTO_ESCALATED,
        TicketEventType.AUTO_REASSIGNED,
    ]
