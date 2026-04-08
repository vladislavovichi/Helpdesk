from __future__ import annotations

from collections.abc import Sequence

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from application.use_cases.tickets.summaries import MacroSummary
from bot.formatters.macros import (
    format_admin_macro_details,
    format_admin_macro_list,
    paginate_macros,
)
from bot.keyboards.inline.macros import (
    build_admin_macro_detail_markup,
    build_admin_macro_list_markup,
)


def build_admin_macro_list_response(
    *,
    macros: Sequence[MacroSummary],
    page: int,
) -> tuple[str, InlineKeyboardMarkup]:
    page_macros, current_page, total_pages = paginate_macros(macros, page=page)
    return (
        format_admin_macro_list(
            page_macros,
            current_page=current_page,
            total_pages=total_pages,
        ),
        build_admin_macro_list_markup(
            macros=page_macros,
            current_page=current_page,
            total_pages=total_pages,
        ),
    )


async def edit_admin_macro_list(
    *,
    callback: CallbackQuery,
    macros: Sequence[MacroSummary],
    page: int,
    answer_text: str,
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer(answer_text)
        return
    text, markup = build_admin_macro_list_response(macros=macros, page=page)
    await callback.answer(answer_text)
    await callback.message.edit_text(text, reply_markup=markup)


async def edit_admin_macro_details(
    *,
    callback: CallbackQuery,
    macro: MacroSummary,
    page: int,
    answer_text: str,
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer(answer_text)
        return
    await callback.answer(answer_text)
    await callback.message.edit_text(
        format_admin_macro_details(macro),
        reply_markup=build_admin_macro_detail_markup(
            macro_id=macro.id,
            page=page,
        ),
    )


async def update_admin_source_message(
    *,
    bot: Bot,
    state_data: dict[str, object],
    macro: MacroSummary,
    page: int,
    fallback_message: Message,
) -> None:
    chat_id = state_data.get("source_chat_id")
    message_id = state_data.get("source_message_id")
    if isinstance(chat_id, int) and isinstance(message_id, int):
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=format_admin_macro_details(macro),
            reply_markup=build_admin_macro_detail_markup(
                macro_id=macro.id,
                page=page,
            ),
        )
        return

    await fallback_message.answer(
        format_admin_macro_details(macro),
        reply_markup=build_admin_macro_detail_markup(
            macro_id=macro.id,
            page=page,
        ),
    )
