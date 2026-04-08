from __future__ import annotations

from aiogram import Router

from bot.handlers.operator.workflow_macro_application import router as application_router
from bot.handlers.operator.workflow_macro_browser import router as browser_router

router = Router(name="operator_workflow_macro_actions")
router.include_router(browser_router)
router.include_router(application_router)
