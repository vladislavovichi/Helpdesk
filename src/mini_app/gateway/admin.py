from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.use_cases.ai.settings import AISettingsRepository, build_ai_settings_from_update
from backend.grpc.contracts import HelpdeskBackendClientFactory
from mini_app.auth import TelegramMiniAppUser
from mini_app.gateway.common import build_actor
from mini_app.serializers import (
    serialize_ai_settings,
    serialize_operator,
    serialize_operator_invite,
)


@dataclass(slots=True)
class MiniAppAdminGateway:
    backend_client_factory: HelpdeskBackendClientFactory
    ai_settings_repository: AISettingsRepository
    bot_username: str | None = None

    async def list_operators(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            operators = await client.list_operators(actor=actor)
        return {"items": [serialize_operator(item) for item in operators]}

    async def create_operator_invite(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        actor = build_actor(user)
        async with self.backend_client_factory() as client:
            invite = await client.create_operator_invite(actor=actor)
        return {"invite": serialize_operator_invite(invite, bot_username=self.bot_username)}

    async def get_ai_settings(self, *, user: TelegramMiniAppUser) -> dict[str, Any]:
        del user
        return {"settings": serialize_ai_settings(self.ai_settings_repository.get())}

    async def update_ai_settings(
        self,
        *,
        user: TelegramMiniAppUser,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        del user
        current = self.ai_settings_repository.get()
        updated = build_ai_settings_from_update(current, payload)
        saved = self.ai_settings_repository.save(updated)
        return {"settings": serialize_ai_settings(saved)}
