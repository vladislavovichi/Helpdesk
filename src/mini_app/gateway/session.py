from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.serializers import serialize_access_context


@dataclass(slots=True)
class MiniAppSessionGateway:
    backend_client_factory: HelpdeskBackendClientFactory

    async def get_session(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        actor = build_actor(user)

        async with self.backend_client_factory() as client:
            access_context = await client.get_access_context(actor=actor)

        return {
            "access": serialize_access_context(access_context),
            "user": {
                "telegram_user_id": user.telegram_user_id,
                "display_name": user.display_name,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
            },
        }
