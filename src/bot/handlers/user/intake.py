from __future__ import annotations

import logging
from collections.abc import Sequence

from aiogram import Bot, F, Router
from aiogram.filters import MagicData, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from application.ai.summaries import TicketCategoryPrediction
from application.use_cases.tickets.summaries import TicketCategorySummary
from bot.callbacks import ClientIntakeCallback
from bot.handlers.common.state_reset import reset_transient_state
from bot.handlers.common.ticket_attachments import IncomingTicketContent
from bot.handlers.user.intake_context import ClientIntakeContext
from bot.handlers.user.intake_flow import (
    browse_client_intake_categories,
    pick_client_intake_category,
    start_client_intake_flow,
    submit_client_intake_message,
)
from bot.handlers.user.states import UserIntakeStates
from bot.texts.categories import INTAKE_CANCELLED_TEXT
from bot.texts.common import ATTACHMENT_NOT_SUPPORTED_TEXT
from domain.enums.roles import UserRole

router = Router(name="client_intake")
logger = logging.getLogger(__name__)
SUPPORTED_TICKET_MEDIA_FILTER = F.photo | F.document | F.voice | F.video


async def start_client_intake(
    *,
    message: Message,
    state: FSMContext,
    categories: Sequence[TicketCategorySummary],
    content: IncomingTicketContent,
    prediction: TicketCategoryPrediction | None = None,
) -> None:
    await start_client_intake_flow(
        message=message,
        state=state,
        categories=tuple(categories),
        content=content,
        prediction=prediction,
    )


@router.callback_query(
    MagicData(F.event_user_role == UserRole.USER),
    ClientIntakeCallback.filter(F.action == "browse"),
)
async def handle_client_intake_category_browse(
    callback: CallbackQuery,
    state: FSMContext,
    client_intake_context: ClientIntakeContext,
) -> None:
    await browse_client_intake_categories(
        callback=callback,
        state=state,
        context=client_intake_context,
    )


@router.callback_query(
    MagicData(F.event_user_role == UserRole.USER),
    ClientIntakeCallback.filter(F.action == "pick"),
)
async def handle_client_intake_category_pick(
    callback: CallbackQuery,
    callback_data: ClientIntakeCallback,
    state: FSMContext,
    bot: Bot,
    client_intake_context: ClientIntakeContext,
) -> None:
    await pick_client_intake_category(
        callback=callback,
        callback_data=callback_data,
        state=state,
        bot=bot,
        context=client_intake_context,
    )


@router.callback_query(
    MagicData(F.event_user_role == UserRole.USER),
    ClientIntakeCallback.filter(F.action == "cancel"),
)
async def handle_client_intake_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await reset_transient_state(state)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(INTAKE_CANCELLED_TEXT, reply_markup=None)


@router.message(
    StateFilter(UserIntakeStates.writing_message),
    MagicData(F.event_user_role == UserRole.USER),
    F.text & ~F.text.startswith("/"),
)
@router.message(
    StateFilter(UserIntakeStates.writing_message),
    MagicData(F.event_user_role == UserRole.USER),
    SUPPORTED_TICKET_MEDIA_FILTER,
)
async def handle_client_intake_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
    client_intake_context: ClientIntakeContext,
) -> None:
    await submit_client_intake_message(
        message=message,
        state=state,
        bot=bot,
        context=client_intake_context,
    )


@router.message(
    StateFilter(UserIntakeStates.writing_message),
    MagicData(F.event_user_role == UserRole.USER),
    F.content_type.in_({"animation", "audio", "sticker", "video_note"}),
)
async def handle_client_intake_unsupported_attachment(message: Message) -> None:
    await message.answer(ATTACHMENT_NOT_SUPPORTED_TEXT)
