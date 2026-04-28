from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.user.intake_context import ClientIntakeContext
from bot.handlers.user.intake_draft import (
    PendingClientIntakeDraft,
    load_pending_client_intake_draft,
)
from bot.handlers.user.states import UserIntakeStates
from bot.texts.buttons import ALL_NAVIGATION_BUTTONS, CANCEL_BUTTON_TEXT
from bot.texts.categories import (
    INTAKE_CATEGORY_STALE_TEXT,
    build_intake_attachment_prompt_text,
    build_intake_message_prompt_text,
)
from bot.texts.common import CHAT_RATE_LIMIT_TEXT, SERVICE_UNAVAILABLE_TEXT


@dataclass(slots=True, frozen=True)
class IntakeDraftState:
    data: dict[str, Any]
    draft: PendingClientIntakeDraft | None


async def ensure_choosing_category(callback: CallbackQuery, state: FSMContext) -> bool:
    if await state.get_state() == UserIntakeStates.choosing_category.state:
        return True
    await callback.answer(INTAKE_CATEGORY_STALE_TEXT, show_alert=True)
    return False


async def ensure_callback_capacity(
    callback: CallbackQuery,
    context: ClientIntakeContext,
) -> bool:
    if await context.global_rate_limiter.allow():
        return True
    await callback.answer(SERVICE_UNAVAILABLE_TEXT, show_alert=True)
    return False


async def ensure_message_capacity(message: Message, context: ClientIntakeContext) -> bool:
    if not await context.global_rate_limiter.allow():
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return False
    if not await context.chat_rate_limiter.allow(chat_id=message.chat.id):
        await message.answer(CHAT_RATE_LIMIT_TEXT)
        return False
    return True


async def load_intake_draft_state(state: FSMContext) -> IntakeDraftState:
    state_data = await state.get_data()
    return IntakeDraftState(
        data=state_data,
        draft=load_pending_client_intake_draft(state_data),
    )


async def require_selected_category(message: Message, state: FSMContext) -> int | None:
    state_data = await state.get_data()
    category_id = state_data.get("category_id")
    if isinstance(category_id, int):
        return category_id

    await state.clear()
    await message.answer(INTAKE_CATEGORY_STALE_TEXT)
    return None


async def answer_navigation_in_intake(
    *,
    message: Message,
    state_data: dict[str, Any],
    draft: PendingClientIntakeDraft | None,
    text: str | None,
) -> bool:
    if text not in ALL_NAVIGATION_BUTTONS or text == CANCEL_BUTTON_TEXT:
        return False

    category_title = state_data.get("category_title")
    await message.answer(
        build_intake_attachment_prompt_text(category_title)
        if isinstance(category_title, str) and draft is not None and draft.attachment is not None
        else (
            build_intake_message_prompt_text(category_title)
            if isinstance(category_title, str)
            else INTAKE_CATEGORY_STALE_TEXT
        )
    )
    return True


async def reject_second_attachment(
    *,
    message: Message,
    state_data: dict[str, Any],
    draft: PendingClientIntakeDraft | None,
    has_current_attachment: bool,
) -> bool:
    if draft is None or draft.attachment is None or not has_current_attachment:
        return False

    category_title = state_data.get("category_title")
    await message.answer(
        build_intake_attachment_prompt_text(category_title)
        if isinstance(category_title, str)
        else INTAKE_CATEGORY_STALE_TEXT
    )
    return True
