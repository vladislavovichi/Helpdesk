from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import CallbackQuery, Message

from application.ai.summaries import TicketCategoryPrediction
from application.use_cases.tickets.summaries import TicketCategorySummary
from bot.keyboards.inline.categories import (
    build_client_intake_categories_markup,
    build_client_intake_message_markup,
    build_client_intake_suggestion_markup,
)
from bot.texts.categories import (
    INTAKE_CATEGORY_PROMPT_TEXT,
    build_intake_attachment_prompt_text,
    build_intake_category_prompt_text,
    build_intake_category_selected_text,
    build_intake_message_prompt_text,
)


async def send_intake_category_prompt(
    *,
    message: Message,
    categories: Sequence[TicketCategorySummary],
    prediction: TicketCategoryPrediction | None,
) -> None:
    if prediction is not None and prediction.available and prediction.category_id is not None:
        await message.answer(
            build_intake_category_prompt_text(
                suggested_category_title=prediction.category_title,
                reason=prediction.reason,
            ),
            reply_markup=build_client_intake_suggestion_markup(
                category_id=prediction.category_id,
                category_title=prediction.category_title or "Тема",
            ),
        )
        return

    await message.answer(
        build_intake_category_prompt_text(),
        reply_markup=build_client_intake_categories_markup(
            prioritize_categories(categories, prediction)
        ),
    )


async def edit_intake_category_browse_prompt(
    *,
    callback: CallbackQuery,
    categories: Sequence[TicketCategorySummary],
    prediction: TicketCategoryPrediction | None,
) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            INTAKE_CATEGORY_PROMPT_TEXT,
            reply_markup=build_client_intake_categories_markup(
                prioritize_categories(categories, prediction)
            ),
        )


async def edit_intake_category_selected(
    *,
    callback: CallbackQuery,
    category_title: str,
) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            build_intake_category_selected_text(category_title),
            reply_markup=None,
        )


async def edit_intake_message_prompt(
    *,
    callback: CallbackQuery,
    category_title: str,
    has_attachment: bool,
) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            (
                build_intake_attachment_prompt_text(category_title)
                if has_attachment
                else build_intake_message_prompt_text(category_title)
            ),
            reply_markup=build_client_intake_message_markup(),
        )


def prioritize_categories(
    categories: Sequence[TicketCategorySummary],
    prediction: TicketCategoryPrediction | None,
) -> tuple[TicketCategorySummary, ...]:
    if prediction is None or not prediction.available or prediction.category_id is None:
        return tuple(categories)

    preferred: list[TicketCategorySummary] = []
    rest: list[TicketCategorySummary] = []
    for category in categories:
        if category.id == prediction.category_id:
            preferred.append(category)
        else:
            rest.append(category)
    return tuple(preferred + rest)
