from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from application.ai.summaries import TicketCategoryPrediction
from application.use_cases.tickets.summaries import TicketCategorySummary
from bot.adapters.helpdesk import build_client_ticket_message_command_from_values
from bot.callbacks import ClientIntakeCallback
from bot.handlers.common.ticket_attachments import (
    AttachmentRejectedError,
    IncomingTicketContent,
    extract_ticket_content,
)
from bot.handlers.user.intake_context import ClientIntakeContext
from bot.handlers.user.intake_draft import (
    PendingClientIntakeDraft,
    build_pending_client_intake_draft,
    store_pending_client_intake_draft,
)
from bot.handlers.user.intake_guards import (
    answer_navigation_in_intake,
    ensure_callback_capacity,
    ensure_choosing_category,
    ensure_message_capacity,
    load_intake_draft_state,
    reject_second_attachment,
    require_selected_category,
)
from bot.handlers.user.intake_responses import (
    edit_intake_category_browse_prompt,
    edit_intake_category_selected,
    edit_intake_message_prompt,
    send_intake_category_prompt,
)
from bot.handlers.user.states import UserIntakeStates
from bot.handlers.user.workflow import (
    process_client_intake_submission,
    process_client_ticket_command,
    process_client_ticket_message,
)
from bot.texts.categories import INTAKE_CATEGORY_STALE_TEXT


async def start_client_intake_flow(
    *,
    message: Message,
    state: FSMContext,
    categories: tuple[TicketCategorySummary, ...],
    content: IncomingTicketContent,
    prediction: TicketCategoryPrediction | None = None,
) -> None:
    await state.set_state(UserIntakeStates.choosing_category)
    await store_pending_client_intake_draft(
        state=state,
        draft=build_pending_client_intake_draft(
            client_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            content=content,
        ),
        extra_data={"suggested_category_id": _suggested_category_id(prediction)},
    )
    await send_intake_category_prompt(
        message=message,
        categories=categories,
        prediction=prediction,
    )


async def browse_client_intake_categories(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    context: ClientIntakeContext,
) -> None:
    if not await ensure_choosing_category(callback, state):
        return

    draft_state = await load_intake_draft_state(state)
    suggested_category_id = draft_state.data.get("suggested_category_id")
    async with context.helpdesk_backend_client_factory() as helpdesk_backend:
        categories = await helpdesk_backend.list_client_ticket_categories()

    await callback.answer()
    await edit_intake_category_browse_prompt(
        callback=callback,
        categories=categories,
        prediction=TicketCategoryPrediction(
            available=isinstance(suggested_category_id, int),
            category_id=(suggested_category_id if isinstance(suggested_category_id, int) else None),
        ),
    )


async def pick_client_intake_category(
    *,
    callback: CallbackQuery,
    callback_data: ClientIntakeCallback,
    state: FSMContext,
    bot: Bot,
    context: ClientIntakeContext,
) -> None:
    if not await ensure_choosing_category(callback, state):
        return
    if not await ensure_callback_capacity(callback, context):
        return

    draft_state = await load_intake_draft_state(state)
    async with context.helpdesk_backend_client_factory() as helpdesk_backend:
        categories = await helpdesk_backend.list_client_ticket_categories()

    category = next((item for item in categories if item.id == callback_data.category_id), None)
    if category is None:
        await callback.answer(INTAKE_CATEGORY_STALE_TEXT, show_alert=True)
        return

    await callback.answer()
    if draft_state.draft is None:
        await _clear_stale_intake(callback=callback, state=state)
        return

    if draft_state.draft.has_meaningful_text or draft_state.draft.attachment is not None:
        await edit_intake_category_selected(callback=callback, category_title=category.title)
        await state.clear()
        await _submit_saved_intake_draft(
            callback=callback,
            bot=bot,
            context=context,
            category_id=category.id,
            draft=draft_state.draft,
        )
        return

    await state.set_state(UserIntakeStates.writing_message)
    await store_pending_client_intake_draft(
        state=state,
        draft=draft_state.draft,
        extra_data={"category_id": category.id, "category_title": category.title},
    )
    await edit_intake_message_prompt(
        callback=callback,
        category_title=category.title,
        has_attachment=draft_state.draft.attachment is not None,
    )


async def submit_client_intake_message(
    *,
    message: Message,
    state: FSMContext,
    bot: Bot,
    context: ClientIntakeContext,
) -> None:
    if not await ensure_message_capacity(message, context):
        return

    category_id = await require_selected_category(message, state)
    if category_id is None:
        return

    draft_state = await load_intake_draft_state(state)
    try:
        current_content = await extract_ticket_content(message, bot=bot)
    except AttachmentRejectedError as exc:
        await message.answer(str(exc))
        return
    if current_content is None:
        return

    if await answer_navigation_in_intake(
        message=message,
        state_data=draft_state.data,
        draft=draft_state.draft,
        text=current_content.text,
    ):
        return
    if await reject_second_attachment(
        message=message,
        state_data=draft_state.data,
        draft=draft_state.draft,
        has_current_attachment=current_content.attachment is not None,
    ):
        return

    await state.clear()
    if (
        draft_state.draft is not None
        and draft_state.draft.attachment is not None
        and draft_state.draft.text is None
    ):
        await process_client_intake_submission(
            response_message=message,
            bot=bot,
            context=context.ticket_runtime,
            initial_command=build_client_ticket_message_command_from_values(
                client_chat_id=draft_state.draft.client_chat_id,
                telegram_message_id=draft_state.draft.telegram_message_id,
                text=None,
                attachment=draft_state.draft.attachment,
                category_id=category_id,
            ),
            follow_up_command=build_client_ticket_message_command_from_values(
                client_chat_id=message.chat.id,
                telegram_message_id=message.message_id,
                text=current_content.text,
                attachment=None,
                category_id=None,
            ),
        )
        return

    await process_client_ticket_message(
        message=message,
        bot=bot,
        context=context.ticket_runtime,
        category_id=category_id,
        content=_merge_initial_attachment(draft_state.draft, current_content),
    )


async def _submit_saved_intake_draft(
    *,
    callback: CallbackQuery,
    bot: Bot,
    context: ClientIntakeContext,
    category_id: int,
    draft: PendingClientIntakeDraft,
) -> None:
    if not isinstance(callback.message, Message):
        return
    content = draft.to_content()
    await process_client_ticket_command(
        response_message=callback.message,
        bot=bot,
        context=context.ticket_runtime,
        command=build_client_ticket_message_command_from_values(
            client_chat_id=draft.client_chat_id,
            telegram_message_id=draft.telegram_message_id,
            text=draft.text,
            attachment=draft.attachment,
            category_id=category_id,
        ),
        content=content,
        category_id=category_id,
    )


async def _clear_stale_intake(*, callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(INTAKE_CATEGORY_STALE_TEXT, reply_markup=None)


def _merge_initial_attachment(
    draft: PendingClientIntakeDraft | None,
    current_content: IncomingTicketContent,
) -> IncomingTicketContent:
    if draft is None or draft.attachment is None:
        return current_content
    return IncomingTicketContent(text=current_content.text, attachment=draft.attachment)


def _suggested_category_id(prediction: TicketCategoryPrediction | None) -> int | None:
    if prediction is None or not prediction.available or prediction.category_id is None:
        return None
    return prediction.category_id
