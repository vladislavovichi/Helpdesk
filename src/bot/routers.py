from __future__ import annotations

from aiogram import Router

from bot.handlers.admin.operators import router as admin_router
from bot.handlers.common.system import router as system_router
from bot.handlers.operator.router import router as operator_router
from bot.handlers.user.cancellation import router as user_cancellation_router
from bot.handlers.user.client import router as client_router
from bot.handlers.user.feedback import router as feedback_router
from bot.handlers.user.intake import router as intake_router
from bot.handlers.user.operator_invites import router as operator_invites_router


def build_root_router() -> Router:
    root_router = Router(name="root")
    for child_router in (
        system_router,
        admin_router,
        operator_router,
        operator_invites_router,
        user_cancellation_router,
        intake_router,
        feedback_router,
        client_router,
    ):
        _detach_from_previous_root(child_router)
        root_router.include_router(child_router)
    return root_router


def _detach_from_previous_root(router: Router) -> None:
    if router.parent_router is not None:
        router._parent_router = None
