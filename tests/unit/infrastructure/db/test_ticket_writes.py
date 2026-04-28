from __future__ import annotations

from uuid import uuid4

from sqlalchemy.sql.selectable import Select

from infrastructure.db.repositories.ticket_writes import SqlAlchemyTicketWriteRepository


async def test_get_ticket_for_update_uses_row_level_locking() -> None:
    session = CapturingSession()
    repository = SqlAlchemyTicketWriteRepository()
    repository.session = session  # type: ignore[assignment]

    await repository._get_ticket_for_update(uuid4())

    assert session.statement is not None
    assert isinstance(session.statement, Select)
    assert session.statement._for_update_arg is not None


class CapturingSession:
    def __init__(self) -> None:
        self.statement: object | None = None

    async def execute(self, statement: object) -> object:
        self.statement = statement
        return EmptyResult()


class EmptyResult:
    def scalar_one_or_none(self) -> None:
        return None
