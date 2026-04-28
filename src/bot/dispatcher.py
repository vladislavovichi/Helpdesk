from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.base import BaseStorage
from aiogram.types import (
    ErrorEvent,
    MenuButtonCommands,
    MenuButtonDefault,
    MenuButtonWebApp,
    WebAppInfo,
)
from pydantic import ValidationError

from bot.middlewares.authorization import AuthorizationMiddleware
from bot.middlewares.context import UpdateContextMiddleware
from bot.middlewares.workflow_contexts import WorkflowContextMiddleware
from bot.routers import build_root_router
from bot.texts.buttons import WORKSPACE_BUTTON_TEXT
from bot.texts.common import SERVICE_UNAVAILABLE_TEXT
from infrastructure.config.settings import BotConfig, Settings, get_settings

_MENU_BUTTON_RECONCILE_INTERVAL_SECONDS = 90.0
_MENU_BUTTON_RECONCILE_TASK_KEY = "mini_app_menu_button_reconcile_task"


def build_bot(config: BotConfig) -> Bot:
    return Bot(token=config.token.strip())


def build_dispatcher(*, storage: BaseStorage, **workflow_data: Any) -> Dispatcher:
    dispatcher = Dispatcher(storage=storage)
    dispatcher.workflow_data.update(workflow_data)
    _register_middlewares(dispatcher)
    _register_lifecycle(dispatcher)
    dispatcher.include_router(build_root_router())
    return dispatcher


def _register_middlewares(dispatcher: Dispatcher) -> None:
    update_context_middleware = UpdateContextMiddleware()
    authorization_middleware = AuthorizationMiddleware()
    workflow_context_middleware = WorkflowContextMiddleware()
    dispatcher.message.outer_middleware(update_context_middleware)
    dispatcher.callback_query.outer_middleware(update_context_middleware)
    dispatcher.message.outer_middleware(workflow_context_middleware)
    dispatcher.callback_query.outer_middleware(workflow_context_middleware)
    dispatcher.message.outer_middleware(authorization_middleware)
    dispatcher.callback_query.outer_middleware(authorization_middleware)


def _register_lifecycle(dispatcher: Dispatcher) -> None:
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    dispatcher.observers["error"].register(on_error)


async def on_startup(dispatcher: Dispatcher, bot: Bot, settings: Settings, **_: Any) -> None:
    logger = logging.getLogger(__name__)
    await _configure_mini_app_menu_button(
        bot=bot,
        settings=settings,
        logger=logger,
        source="startup",
    )
    _start_mini_app_menu_button_reconciler(dispatcher=dispatcher, bot=bot, logger=logger)
    bot_info = await bot.get_me()
    logger.info(
        "Bot startup completed username=%s app=%s update_types=%s",
        bot_info.username,
        settings.app.name,
        ",".join(dispatcher.resolve_used_update_types()),
    )


async def on_shutdown(dispatcher: Dispatcher, bot: Bot, settings: Settings, **_: Any) -> None:
    logger = logging.getLogger(__name__)
    await _stop_mini_app_menu_button_reconciler(dispatcher=dispatcher, logger=logger)
    logger.info(
        "Bot shutdown completed bot_id=%s app=%s update_types=%s",
        bot.id,
        settings.app.name,
        ",".join(dispatcher.resolve_used_update_types()),
    )


async def on_error(event: ErrorEvent, **_: Any) -> bool:
    logger = logging.getLogger(__name__)
    logger.exception(
        "Unhandled Telegram update processing failed update_id=%s",
        event.update.update_id,
        exc_info=event.exception,
    )

    callback_query = event.update.callback_query
    if callback_query is not None:
        try:
            await callback_query.answer(SERVICE_UNAVAILABLE_TEXT, show_alert=True)
        except TelegramAPIError:
            logger.exception(
                "Failed to send callback error response update_id=%s",
                event.update.update_id,
            )
        return True

    message = event.update.message
    if message is not None:
        try:
            await message.answer(SERVICE_UNAVAILABLE_TEXT)
        except TelegramAPIError:
            logger.exception(
                "Failed to send message error response update_id=%s",
                event.update.update_id,
            )
        return True

    return True


async def _configure_mini_app_menu_button(
    *,
    bot: Bot,
    settings: Settings,
    logger: logging.Logger,
    source: str,
) -> None:
    desired_button = _build_desired_mini_app_menu_button(settings)
    current_button = await _get_current_menu_button(bot=bot, logger=logger, source=source)
    current_signature = _menu_button_signature(current_button)
    desired_signature = _menu_button_signature(desired_button)

    if current_signature == desired_signature:
        logger.info(
            (
                "Mini App menu button already synchronized source=%s "
                "type=%s url=%s host=%s temporary=%s"
            ),
            source,
            desired_signature[0],
            desired_signature[2] or "<not-set>",
            settings.mini_app.public_url_hostname or "<unknown>",
            settings.mini_app.public_url_looks_temporary,
        )
        return

    await bot.set_chat_menu_button(menu_button=desired_button)
    if isinstance(desired_button, MenuButtonWebApp):
        launch_url = desired_button.web_app.url
        logger.info(
            (
                "Mini App menu button updated source=%s type=web_app text=%s "
                "host=%s url=%s previous_type=%s previous_url=%s temporary=%s"
            ),
            source,
            WORKSPACE_BUTTON_TEXT,
            urlparse(launch_url).hostname or "<unknown>",
            launch_url,
            current_signature[0],
            current_signature[2] or "<not-set>",
            settings.mini_app.public_url_looks_temporary,
        )
        return

    logger.warning(
        (
            "Mini App menu button switched to commands source=%s previous_type=%s "
            "previous_url=%s detail=%s configured_public_url=%s"
        ),
        source,
        current_signature[0],
        current_signature[2] or "<not-set>",
        settings.mini_app.public_url_status_detail,
        settings.mini_app.public_url or "<not-set>",
    )


def _build_desired_mini_app_menu_button(
    settings: Settings,
) -> MenuButtonWebApp | MenuButtonCommands:
    if settings.mini_app.public_url_is_valid:
        launch_url = settings.mini_app.telegram_launch_url
        if launch_url is not None:
            return MenuButtonWebApp(
                text=WORKSPACE_BUTTON_TEXT,
                web_app=WebAppInfo(url=launch_url),
            )
    return MenuButtonCommands()


async def _get_current_menu_button(
    *,
    bot: Bot,
    logger: logging.Logger,
    source: str,
) -> MenuButtonWebApp | MenuButtonCommands | MenuButtonDefault | None:
    try:
        return await bot.get_chat_menu_button()
    except TelegramAPIError:
        logger.warning(
            "Mini App menu button inspection failed source=%s",
            source,
            exc_info=True,
        )
        return None


def _menu_button_signature(menu_button: object | None) -> tuple[str, str | None, str | None]:
    if isinstance(menu_button, MenuButtonWebApp):
        return ("web_app", menu_button.text, menu_button.web_app.url)
    if isinstance(menu_button, MenuButtonCommands):
        return ("commands", None, None)
    if isinstance(menu_button, MenuButtonDefault):
        return ("default", None, None)
    return ("unknown", None, None)


def _start_mini_app_menu_button_reconciler(
    *,
    dispatcher: Dispatcher,
    bot: Bot,
    logger: logging.Logger,
) -> None:
    existing_task = dispatcher.workflow_data.get(_MENU_BUTTON_RECONCILE_TASK_KEY)
    if isinstance(existing_task, asyncio.Task) and not existing_task.done():
        return

    task = asyncio.create_task(
        _run_mini_app_menu_button_reconciler(bot=bot, logger=logger),
        name="mini-app-menu-button-reconciler",
    )
    dispatcher.workflow_data[_MENU_BUTTON_RECONCILE_TASK_KEY] = task
    logger.info(
        "Mini App menu button reconciler started interval_seconds=%s",
        _MENU_BUTTON_RECONCILE_INTERVAL_SECONDS,
    )


async def _stop_mini_app_menu_button_reconciler(
    *,
    dispatcher: Dispatcher,
    logger: logging.Logger,
) -> None:
    task = dispatcher.workflow_data.pop(_MENU_BUTTON_RECONCILE_TASK_KEY, None)
    if not isinstance(task, asyncio.Task):
        return

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Mini App menu button reconciler stopped.")


async def _run_mini_app_menu_button_reconciler(
    *,
    bot: Bot,
    logger: logging.Logger,
) -> None:
    while True:
        await asyncio.sleep(_MENU_BUTTON_RECONCILE_INTERVAL_SECONDS)
        try:
            settings = _reload_runtime_settings()
        except ValidationError:
            logger.warning(
                "Mini App menu button reconciliation skipped because settings reload failed.",
                exc_info=True,
            )
            continue

        try:
            await _configure_mini_app_menu_button(
                bot=bot,
                settings=settings,
                logger=logger,
                source="runtime-reconcile",
            )
        except TelegramAPIError:
            logger.warning(
                "Mini App menu button reconciliation failed while applying Telegram state.",
                exc_info=True,
            )


def _reload_runtime_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
