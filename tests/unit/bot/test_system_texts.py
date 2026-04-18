from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup

from application.services.diagnostics import DiagnosticsCheck, DiagnosticsReport
from bot.formatters.system import build_help_text, build_start_text, format_diagnostics_report
from bot.keyboards.reply.main_menu import build_main_menu
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


def test_build_start_text_for_user_stays_user_friendly() -> None:
    result = build_start_text(UserRole.USER)

    assert "Поддержка в Telegram." in result
    assert "выберите тему обращения" in result.lower()
    assert "оператор" not in result
    assert "суперадминистратор" not in result


def test_build_start_text_for_super_admin_mentions_admin_scope() -> None:
    result = build_start_text(UserRole.SUPER_ADMIN)

    assert "Панель суперадминистратора." in result
    assert "операторы, макросы и темы" in result


def test_build_start_text_for_operator_mentions_workspace_when_available() -> None:
    result = build_start_text(UserRole.OPERATOR, mini_app_available=True)

    assert "Кнопка «Рабочее место» открывает Mini App" in result


def test_build_help_text_for_user_does_not_expose_operator_commands() -> None:
    result = build_help_text(UserRole.USER)

    assert "/start - открыть меню заново" in result
    assert "/help - показать краткую справку" in result
    assert "/queue" not in result
    assert "/operators" not in result


def test_build_help_text_for_operator_is_menu_first() -> None:
    result = build_help_text(UserRole.OPERATOR)

    assert "Навигация" in result
    assert f"«{QUEUE_BUTTON_TEXT}» - открыть новые заявки." in result
    assert f"«{MY_TICKETS_BUTTON_TEXT}» - вернуться к активным диалогам." in result
    assert "/start - открыть меню заново" in result
    assert "/health" not in result
    assert "/ticket" not in result
    assert "/operators" not in result


def test_build_help_text_for_operator_mentions_workspace_when_available() -> None:
    result = build_help_text(UserRole.OPERATOR, mini_app_available=True)

    assert "«Рабочее место» - открыть Mini App" in result


def test_build_help_text_for_operator_mentions_missing_workspace_button_when_unavailable() -> None:
    result = build_help_text(UserRole.OPERATOR, mini_app_available=False)

    assert "Если кнопки «Рабочее место» нет" in result


def test_build_help_text_for_super_admin_is_menu_first() -> None:
    result = build_help_text(UserRole.SUPER_ADMIN)

    assert f"«{OPERATORS_BUTTON_TEXT}» - открыть состав команды и управление ролями." in result
    assert f"«{MACROS_BUTTON_TEXT}» - открыть библиотеку и редактирование макросов." in result
    assert f"«{CATEGORIES_BUTTON_TEXT}» - настроить темы новых обращений." in result
    assert "/add_operator" not in result
    assert "/remove_operator" not in result
    assert "/health" not in result


def test_build_main_menu_for_user_is_minimal() -> None:
    keyboard = build_main_menu(UserRole.USER)

    assert _keyboard_rows(keyboard) == ((HELP_BUTTON_TEXT,),)
    assert keyboard.input_field_placeholder == "Сообщение в поддержку"


def test_build_main_menu_for_operator_contains_operator_navigation() -> None:
    keyboard = build_main_menu(UserRole.OPERATOR)

    assert _keyboard_rows(keyboard) == (
        (QUEUE_BUTTON_TEXT, MY_TICKETS_BUTTON_TEXT),
        (ARCHIVE_BUTTON_TEXT, STATS_BUTTON_TEXT),
        (TAKE_NEXT_BUTTON_TEXT,),
        (HELP_BUTTON_TEXT, CANCEL_BUTTON_TEXT),
    )
    assert keyboard.input_field_placeholder == "Главное меню"


def test_build_main_menu_for_super_admin_contains_admin_navigation() -> None:
    keyboard = build_main_menu(UserRole.SUPER_ADMIN)

    assert _keyboard_rows(keyboard) == (
        (QUEUE_BUTTON_TEXT, MY_TICKETS_BUTTON_TEXT),
        (ARCHIVE_BUTTON_TEXT, STATS_BUTTON_TEXT),
        (TAKE_NEXT_BUTTON_TEXT,),
        (OPERATORS_BUTTON_TEXT, MACROS_BUTTON_TEXT),
        (CATEGORIES_BUTTON_TEXT,),
        (HELP_BUTTON_TEXT, CANCEL_BUTTON_TEXT),
    )
    assert keyboard.input_field_placeholder == "Главное меню"


def test_build_main_menu_adds_mini_app_button_when_public_url_is_configured() -> None:
    keyboard = build_main_menu(
        UserRole.OPERATOR,
        mini_app_url="https://mini-app.example.com",
    )

    rows = keyboard.keyboard
    assert rows is not None
    workspace_button = rows[0][0]
    assert workspace_button.text == WORKSPACE_BUTTON_TEXT
    assert workspace_button.web_app is not None
    assert workspace_button.web_app.url == "https://mini-app.example.com"


def test_format_diagnostics_report_uses_compact_russian_output() -> None:
    report = DiagnosticsReport(
        checks=(
            DiagnosticsCheck(
                name="bootstrap",
                category="liveness",
                ok=True,
                detail="runtime инициализирован",
            ),
            DiagnosticsCheck(
                name="redis",
                category="dependency",
                ok=False,
                detail="RuntimeError: timeout",
            ),
        )
    )

    result = format_diagnostics_report(report)

    assert "Есть проблемы с готовностью сервиса." in result
    assert "- liveness: в порядке" in result
    assert "- readiness: ошибка" in result
    assert "- bootstrap: в порядке (runtime инициализирован)" in result
    assert "- redis: ошибка (RuntimeError: timeout)" in result


def test_format_diagnostics_report_marks_non_blocking_warning() -> None:
    report = DiagnosticsReport(
        checks=(
            DiagnosticsCheck(
                name="bootstrap",
                category="liveness",
                ok=True,
                detail="runtime инициализирован",
            ),
            DiagnosticsCheck(
                name="mini_app_url",
                category="integration",
                ok=False,
                detail="MINI_APP__PUBLIC_URL должен начинаться с https://.",
                affects_readiness=False,
            ),
        )
    )

    result = format_diagnostics_report(report)

    assert "Сервис готов к работе, но есть замечания." in result
    assert "- mini_app_url: внимание (MINI_APP__PUBLIC_URL должен начинаться с https://.)" in result


def _keyboard_rows(keyboard: ReplyKeyboardMarkup) -> tuple[tuple[str, ...], ...]:
    rows = keyboard.keyboard
    assert rows is not None
    return tuple(tuple(button.text for button in row) for row in rows)
