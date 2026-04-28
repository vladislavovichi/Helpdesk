from __future__ import annotations

from application.contracts.actors import OperatorIdentity, RequestActor
from mini_app.auth import TelegramMiniAppUser


def build_actor(user: TelegramMiniAppUser) -> RequestActor:
    return RequestActor(telegram_user_id=user.telegram_user_id)


def build_operator_identity(user: TelegramMiniAppUser) -> OperatorIdentity:
    return OperatorIdentity(
        telegram_user_id=user.telegram_user_id,
        display_name=user.display_name,
        username=user.username,
    )
