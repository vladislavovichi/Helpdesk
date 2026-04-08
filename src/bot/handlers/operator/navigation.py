from __future__ import annotations

from aiogram import Router

from bot.handlers.operator.navigation_cancellation import router as cancellation_router
from bot.handlers.operator.navigation_queue import router as queue_router

router = Router(name="operator_navigation")
router.include_router(cancellation_router)
router.include_router(queue_router)
