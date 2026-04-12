from __future__ import annotations

from unittest.mock import Mock

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.dispatcher import _register_middlewares, build_dispatcher
from bot.middlewares.authorization import AuthorizationMiddleware
from bot.middlewares.context import UpdateContextMiddleware
from infrastructure.redis.fsm import build_fsm_storage


def test_build_fsm_storage_returns_redis_storage() -> None:
    redis = Mock(spec=Redis)
    storage = build_fsm_storage(redis)

    assert isinstance(storage, RedisStorage)
    assert storage.redis is redis


def test_build_dispatcher_uses_provided_storage() -> None:
    redis = Mock(spec=Redis)
    storage = build_fsm_storage(redis)

    dispatcher = build_dispatcher(storage=storage)

    assert dispatcher.storage is storage
    assert len(dispatcher.observers["error"].handlers) == 1


def test_build_dispatcher_registers_role_context_before_filter_stage() -> None:
    redis = Mock(spec=Redis)
    storage = build_fsm_storage(redis)

    dispatcher = Dispatcher(storage=storage)
    _register_middlewares(dispatcher)

    outer_middlewares = dispatcher.message.outer_middleware._middlewares
    inner_middlewares = dispatcher.message.middleware._middlewares

    assert [type(middleware) for middleware in outer_middlewares] == [
        UpdateContextMiddleware,
        AuthorizationMiddleware,
    ]
    assert inner_middlewares == []
