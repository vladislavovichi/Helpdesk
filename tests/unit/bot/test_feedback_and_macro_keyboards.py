from __future__ import annotations

from uuid import uuid4

from bot.keyboards.inline.client_actions import build_client_ticket_finish_confirmation_markup
from bot.keyboards.inline.feedback import (
    build_ticket_feedback_comment_markup,
    build_ticket_feedback_rating_markup,
)
from bot.keyboards.inline.macros import (
    build_operator_macro_picker_markup,
    build_operator_macro_preview_markup,
)
from bot.keyboards.inline.tags import build_ticket_tags_markup
from bot.texts.buttons import (
    BACK_BUTTON_TEXT,
    BACK_TO_TICKET_BUTTON_TEXT,
    CANCEL_BUTTON_TEXT,
    COMMENT_BUTTON_TEXT,
    SKIP_BUTTON_TEXT,
)


def test_build_client_ticket_finish_confirmation_markup_fits_telegram_callback_limit() -> None:
    markup = build_client_ticket_finish_confirmation_markup(ticket_public_id=uuid4())
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("Завершить", CANCEL_BUTTON_TEXT),)


def test_build_ticket_feedback_rating_markup_stays_compact() -> None:
    markup = build_ticket_feedback_rating_markup(ticket_public_id=uuid4())
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == (("1", "2", "3", "4", "5"),)


def test_build_ticket_feedback_comment_markup_keeps_clean_skip_path() -> None:
    markup = build_ticket_feedback_comment_markup(ticket_public_id=uuid4())
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == ((COMMENT_BUTTON_TEXT, SKIP_BUTTON_TEXT),)


def test_build_ticket_tags_markup_uses_consistent_ticket_return_action() -> None:
    markup = build_ticket_tags_markup(
        ticket_public_id=uuid4(),
        available_tags=(),
        active_tag_names=(),
    )
    rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)

    assert rows == ((BACK_TO_TICKET_BUTTON_TEXT,),)


def test_build_operator_macro_navigation_is_consistent() -> None:
    markup = build_operator_macro_picker_markup(
        ticket_public_id=uuid4(),
        macros=(),
        current_page=1,
        total_pages=1,
    )
    picker_rows = tuple(tuple(button.text for button in row) for row in markup.inline_keyboard)
    preview_markup = build_operator_macro_preview_markup(
        ticket_public_id=uuid4(),
        macro_id=1,
        page=1,
    )
    preview_rows = tuple(
        tuple(button.text for button in row) for row in preview_markup.inline_keyboard
    )

    assert picker_rows == ((BACK_TO_TICKET_BUTTON_TEXT,),)
    assert preview_rows == (("Отправить", BACK_BUTTON_TEXT),)
