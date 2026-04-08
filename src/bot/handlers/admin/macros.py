from __future__ import annotations

from aiogram import Router

from bot.handlers.admin.macro_browser import router as browser_router
from bot.handlers.admin.macro_creation import router as creation_router
from bot.handlers.admin.macro_editing import router as editing_router

router = Router(name="admin_macros")
router.include_router(browser_router)
router.include_router(creation_router)
router.include_router(editing_router)
