from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.contracts.repositories import OperatorTicketLoadRecord
from domain.enums.tickets import TicketStatus
from infrastructure.db.models.operator import Operator
from infrastructure.db.models.ticket import Ticket as TicketModel
from infrastructure.db.repositories.base import OperatorTicketLoadRow


class SqlAlchemyTicketMetricsRepository:
    session: AsyncSession

    async def count_by_status(self) -> Mapping[TicketStatus, int]:
        statement = select(TicketModel.status, func.count(TicketModel.id)).group_by(
            TicketModel.status
        )
        result = await self.session.execute(statement)
        return {status: count for status, count in result.all()}

    async def count_active_tickets_per_operator(self) -> Sequence[OperatorTicketLoadRecord]:
        statement = (
            select(Operator.id, Operator.display_name, func.count(TicketModel.id))
            .join(TicketModel, TicketModel.assigned_operator_id == Operator.id)
            .where(TicketModel.status != TicketStatus.CLOSED)
            .group_by(Operator.id, Operator.display_name)
            .order_by(
                func.count(TicketModel.id).desc(),
                Operator.display_name.asc(),
                Operator.id.asc(),
            )
        )
        result = await self.session.execute(statement)
        return [
            OperatorTicketLoadRow(
                operator_id=operator_id,
                display_name=display_name,
                ticket_count=ticket_count,
            )
            for operator_id, display_name, ticket_count in result.all()
        ]

    async def get_average_first_response_time_seconds(self) -> float | None:
        statement = select(
            func.avg(func.extract("epoch", TicketModel.first_response_at - TicketModel.created_at))
        ).where(
            TicketModel.first_response_at.is_not(None),
            TicketModel.first_response_at >= TicketModel.created_at,
        )
        result = await self.session.execute(statement)
        average_seconds = result.scalar_one_or_none()
        return None if average_seconds is None else float(average_seconds)

    async def get_average_resolution_time_seconds(self) -> float | None:
        statement = select(
            func.avg(func.extract("epoch", TicketModel.closed_at - TicketModel.created_at))
        ).where(
            TicketModel.status == TicketStatus.CLOSED,
            TicketModel.closed_at.is_not(None),
            TicketModel.closed_at >= TicketModel.created_at,
        )
        result = await self.session.execute(statement)
        average_seconds = result.scalar_one_or_none()
        return None if average_seconds is None else float(average_seconds)
