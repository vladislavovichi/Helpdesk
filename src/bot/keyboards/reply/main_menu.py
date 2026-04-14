from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.texts.buttons import (
    ARCHIVE_BUTTON_TEXT,
    CANCEL_BUTTON_TEXT,
    CATEGORIES_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    MACROS_BUTTON_TEXT,
    MY_TICKETS_BUTTON_TEXT,
    OPERATORS_BUTTON_TEXT,
    QUEUE_BUTTON_TEXT,
    STATS_BUTTON_TEXT,
    TAKE_NEXT_BUTTON_TEXT,
    WORKSPACE_BUTTON_TEXT,
)
from domain.enums.roles import UserRole


def build_main_menu(role: UserRole, *, mini_app_url: str | None = None) -> ReplyKeyboardMarkup:
    keyboard_rows: list[list[KeyboardButton]] = []

    if role == UserRole.USER:
        keyboard_rows.append([KeyboardButton(text=HELP_BUTTON_TEXT)])
        placeholder = "Сообщение в поддержку"
    else:
        keyboard_rows.extend(
            [
                [
                    KeyboardButton(text=QUEUE_BUTTON_TEXT),
                    KeyboardButton(text=MY_TICKETS_BUTTON_TEXT),
                ],
                [
                    KeyboardButton(text=ARCHIVE_BUTTON_TEXT),
                    KeyboardButton(text=STATS_BUTTON_TEXT),
                ],
                [KeyboardButton(text=TAKE_NEXT_BUTTON_TEXT)],
            ]
        )
        placeholder = "Главное меню"

        normalized_mini_app_url = mini_app_url.strip() if isinstance(mini_app_url, str) else ""
        if normalized_mini_app_url:
            keyboard_rows.append(
                [
                    KeyboardButton(
                        text=WORKSPACE_BUTTON_TEXT,
                        web_app=WebAppInfo(url=normalized_mini_app_url),
                    )
                ]
            )

        if role == UserRole.SUPER_ADMIN:
            keyboard_rows.append(
                [
                    KeyboardButton(text=OPERATORS_BUTTON_TEXT),
                    KeyboardButton(text=MACROS_BUTTON_TEXT),
                ]
            )
            keyboard_rows.append([KeyboardButton(text=CATEGORIES_BUTTON_TEXT)])

        keyboard_rows.append(
            [
                KeyboardButton(text=HELP_BUTTON_TEXT),
                KeyboardButton(text=CANCEL_BUTTON_TEXT),
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )
