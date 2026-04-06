from __future__ import annotations

from aiogram import Router

from bot.handlers.operator.workflow_macro_actions import router as macro_router
from bot.handlers.operator.workflow_reassignment import router as reassignment_router
from bot.handlers.operator.workflow_reply import router as reply_router
from bot.handlers.operator.workflow_ticket_actions import router as ticket_actions_router

router = Router(name="operator_workflow")
router.include_router(ticket_actions_router)
router.include_router(reply_router)
router.include_router(macro_router)
router.include_router(reassignment_router)
