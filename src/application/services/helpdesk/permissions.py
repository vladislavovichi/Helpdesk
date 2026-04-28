from __future__ import annotations

from dataclasses import dataclass

from application.services.authorization import ROLE_PERMISSIONS, AuthorizationError, Permission
from domain.contracts.repositories import OperatorRepository
from domain.enums.roles import UserRole


@dataclass(slots=True)
class HelpdeskPermissionGuard:
    operator_repository: OperatorRepository
    super_admin_telegram_user_ids: frozenset[int]

    async def ensure_allowed(
        self,
        *,
        permission: Permission,
        telegram_user_id: int | None,
    ) -> None:
        if telegram_user_id is None:
            raise AuthorizationError(permission)

        if permission in ROLE_PERMISSIONS[UserRole.USER]:
            return

        if permission not in ROLE_PERMISSIONS[UserRole.OPERATOR]:
            if telegram_user_id not in self.super_admin_telegram_user_ids:
                raise AuthorizationError(permission)
            return

        if telegram_user_id in self.super_admin_telegram_user_ids:
            return

        is_operator = await self.operator_repository.exists_active_by_telegram_user_id(
            telegram_user_id=telegram_user_id
        )
        if not is_operator:
            raise AuthorizationError(permission)
