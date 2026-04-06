from __future__ import annotations

from aiogram import Router

from bot.handlers.operator.command_macros import router as macros_router
from bot.handlers.operator.command_navigation import router as navigation_router
from bot.handlers.operator.command_tags import router as tags_router

router = Router(name="operator_commands")
router.include_router(navigation_router)
router.include_router(macros_router)
router.include_router(tags_router)
