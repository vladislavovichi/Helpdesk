from __future__ import annotations

from dataclasses import dataclass

from domain.contracts.repositories import TicketRepository
from domain.enums.tickets import TicketStatus


@dataclass(slots=True, frozen=True)
class OperatorTicketLoad:
    operator_id: int
    display_name: str
    ticket_count: int


@dataclass(slots=True, frozen=True)
class HelpdeskOperationalStats:
    total_open_tickets: int
    queued_tickets_count: int
    assigned_tickets_count: int
    escalated_tickets_count: int
    closed_tickets_count: int
    tickets_per_operator: tuple[OperatorTicketLoad, ...]
    average_first_response_time_seconds: int | None
    average_resolution_time_seconds: int | None


def _normalize_average_seconds(value: float | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        return 0
    return int(round(value))


class HelpdeskStatsService:
    """Aggregate pragmatic operational metrics from ticket state and timestamps."""

    def __init__(self, ticket_repository: TicketRepository) -> None:
        self.ticket_repository = ticket_repository

    async def get_operational_stats(self) -> HelpdeskOperationalStats:
        by_status = dict(await self.ticket_repository.count_by_status())
        tickets_per_operator = await self.ticket_repository.count_active_tickets_per_operator()
        average_first_response_seconds = (
            await self.ticket_repository.get_average_first_response_time_seconds()
        )
        average_resolution_seconds = (
            await self.ticket_repository.get_average_resolution_time_seconds()
        )

        return HelpdeskOperationalStats(
            total_open_tickets=sum(
                count
                for status, count in by_status.items()
                if status != TicketStatus.CLOSED
            ),
            queued_tickets_count=by_status.get(TicketStatus.QUEUED, 0),
            assigned_tickets_count=by_status.get(TicketStatus.ASSIGNED, 0),
            escalated_tickets_count=by_status.get(TicketStatus.ESCALATED, 0),
            closed_tickets_count=by_status.get(TicketStatus.CLOSED, 0),
            tickets_per_operator=tuple(
                OperatorTicketLoad(
                    operator_id=item.operator_id,
                    display_name=item.display_name,
                    ticket_count=item.ticket_count,
                )
                for item in tickets_per_operator
            ),
            average_first_response_time_seconds=_normalize_average_seconds(
                average_first_response_seconds
            ),
            average_resolution_time_seconds=_normalize_average_seconds(
                average_resolution_seconds
            ),
        )
