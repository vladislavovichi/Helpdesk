from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RequestActor:
    telegram_user_id: int


@dataclass(slots=True, frozen=True)
class OperatorIdentity:
    telegram_user_id: int
    display_name: str
    username: str | None = None


def actor_telegram_user_id(actor: RequestActor | None) -> int | None:
    if actor is None:
        return None
    return actor.telegram_user_id
