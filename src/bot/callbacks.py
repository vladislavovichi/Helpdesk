from __future__ import annotations

from typing import Literal

from aiogram.filters.callback_data import CallbackData


class OperatorActionCallback(CallbackData, prefix="operator"):
    action: Literal["take", "reply", "close", "escalate", "reassign", "view", "macros"]
    ticket_public_id: str


class OperatorQueueCallback(CallbackData, prefix="operator_queue"):
    action: Literal["page", "noop"]
    page: int


class OperatorMacroCallback(CallbackData, prefix="operator_macro"):
    action: Literal["page", "noop", "preview", "apply", "back", "ticket"]
    ticket_public_id: str
    macro_id: int
    page: int


class AdminOperatorCallback(CallbackData, prefix="admin_operator"):
    action: Literal["refresh", "revoke", "confirm_revoke", "cancel_revoke"]
    telegram_user_id: int


class AdminMacroCallback(CallbackData, prefix="admin_macro"):
    action: Literal[
        "page",
        "noop",
        "view",
        "create",
        "back_list",
        "edit_title",
        "edit_body",
        "delete",
        "confirm_delete",
        "cancel_delete",
        "preview_save",
        "preview_edit",
        "preview_cancel",
    ]
    macro_id: int
    page: int
