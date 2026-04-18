from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo
from redis.asyncio import Redis

from bot.dispatcher import (
    _configure_mini_app_menu_button,
    _menu_button_signature,
    _register_middlewares,
    build_dispatcher,
)
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


@pytest.mark.asyncio
async def test_configure_mini_app_menu_button_uses_web_app_menu_when_url_is_valid() -> None:
    bot = AsyncMock()
    bot.get_chat_menu_button.return_value = MenuButtonCommands()
    logger = Mock()
    settings = SimpleNamespace(
        mini_app=SimpleNamespace(
            public_url_is_valid=True,
            telegram_launch_url="https://mini-app.example.com",
            public_url_status_detail="ok",
            public_url="https://mini-app.example.com",
            public_url_hostname="mini-app.example.com",
            public_url_looks_temporary=False,
        )
    )

    await _configure_mini_app_menu_button(
        bot=bot,
        settings=settings,
        logger=logger,
        source="test",
    )

    bot.set_chat_menu_button.assert_awaited_once()
    menu_button = bot.set_chat_menu_button.await_args.kwargs["menu_button"]
    assert isinstance(menu_button, MenuButtonWebApp)
    assert menu_button.text == "Панель"
    assert menu_button.web_app.url == "https://mini-app.example.com"


@pytest.mark.asyncio
async def test_configure_mini_app_menu_button_falls_back_to_commands_when_url_invalid() -> None:
    bot = AsyncMock()
    bot.get_chat_menu_button.return_value = MenuButtonWebApp(
        text="Панель",
        web_app=WebAppInfo(url="https://stale.example.com"),
    )
    logger = Mock()
    settings = SimpleNamespace(
        mini_app=SimpleNamespace(
            public_url_is_valid=False,
            telegram_launch_url=None,
            public_url_status_detail="MINI_APP__PUBLIC_URL не задан.",
            public_url="",
            public_url_hostname=None,
            public_url_looks_temporary=False,
        )
    )

    await _configure_mini_app_menu_button(
        bot=bot,
        settings=settings,
        logger=logger,
        source="test",
    )

    bot.set_chat_menu_button.assert_awaited_once()
    menu_button = bot.set_chat_menu_button.await_args.kwargs["menu_button"]
    assert isinstance(menu_button, MenuButtonCommands)


@pytest.mark.asyncio
async def test_configure_mini_app_menu_button_skips_apply_when_remote_state_is_current() -> None:
    menu_button = MenuButtonWebApp(
        text="Панель",
        web_app=WebAppInfo(url="https://mini-app.example.com"),
    )
    bot = AsyncMock()
    bot.get_chat_menu_button.return_value = menu_button
    logger = Mock()
    settings = SimpleNamespace(
        mini_app=SimpleNamespace(
            public_url_is_valid=True,
            telegram_launch_url="https://mini-app.example.com",
            public_url_status_detail="ok",
            public_url="https://mini-app.example.com",
            public_url_hostname="mini-app.example.com",
            public_url_looks_temporary=False,
        )
    )

    await _configure_mini_app_menu_button(
        bot=bot,
        settings=settings,
        logger=logger,
        source="test",
    )

    bot.set_chat_menu_button.assert_not_awaited()


def test_menu_button_signature_extracts_web_app_url() -> None:
    signature = _menu_button_signature(
        MenuButtonWebApp(
            text="Панель",
            web_app=WebAppInfo(url="https://mini-app.example.com"),
        )
    )

    assert signature == ("web_app", "Панель", "https://mini-app.example.com")
