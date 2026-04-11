from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.audit import AuditLog


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        action: str,
        entity_type: str,
        outcome: str,
        actor_telegram_user_id: int | None = None,
        entity_id: int | None = None,
        entity_public_id: UUID | None = None,
        correlation_id: str | None = None,
        metadata_json: Mapping[str, object] | None = None,
    ) -> None:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            outcome=outcome,
            actor_telegram_user_id=actor_telegram_user_id,
            entity_id=entity_id,
            entity_public_id=entity_public_id,
            correlation_id=correlation_id,
            metadata_json=dict(metadata_json) if metadata_json is not None else None,
        )
        self.session.add(entry)
        await self.session.flush()
