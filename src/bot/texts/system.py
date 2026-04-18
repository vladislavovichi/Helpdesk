from __future__ import annotations

from application.services.diagnostics import DiagnosticsReport
from domain.enums.roles import UserRole

PING_RESPONSE_TEXT = "понг"


def format_diagnostics_report(report: DiagnosticsReport) -> str:
    if not report.readiness_ok:
        status_line = "Есть проблемы с готовностью сервиса."
    elif report.has_warnings:
        status_line = "Сервис готов к работе, но есть замечания."
    else:
        status_line = "Сервис готов к работе."
    lines = [status_line, ""]
    lines.append(f"- liveness: {'в порядке' if report.liveness_ok else 'ошибка'}")
    lines.append(f"- readiness: {'в порядке' if report.readiness_ok else 'ошибка'}")
    lines.extend(
        f"- {check.name}: "
        f"{'в порядке' if check.ok else ('внимание' if not check.affects_readiness else 'ошибка')} "
        f"({check.detail})"
        for check in report.checks
    )
    return "\n".join(lines)


def get_start_lines(role: UserRole, *, mini_app_available: bool = False) -> list[str]:
    if role == UserRole.SUPER_ADMIN:
        lines = [
            "Панель суперадминистратора.",
            "Ниже доступны очередь, архив, личные заявки, операторы, макросы и темы.",
            "Откройте раздел и продолжайте работу кнопками в карточках.",
        ]
        if mini_app_available:
            lines.insert(
                2,
                "Кнопка меню «Панель» открывает Mini App с обзором, очередью и аналитикой.",
            )
        else:
            lines.insert(
                2,
                (
                    "Если кнопки меню «Панель» нет, "
                    "Mini App пока недоступен и работа остаётся в меню бота."
                ),
            )
        return lines
    if role == UserRole.OPERATOR:
        lines = [
            "Рабочее место оператора.",
            "Очередь, архив, личные заявки и статистика уже в меню.",
            "Откройте заявку, чтобы ответить, применить макрос или изменить метки.",
        ]
        if mini_app_available:
            lines.insert(
                2,
                "Кнопка меню «Панель» открывает Mini App с обзором и карточкой заявки.",
            )
        else:
            lines.insert(
                2,
                (
                    "Если кнопки меню «Панель» нет, "
                    "Mini App пока недоступен и основные действия остаются в меню."
                ),
            )
        return lines
    return [
        "Поддержка в Telegram.",
        "Сначала выберите тему обращения, затем коротко опишите ситуацию.",
        "Когда заявка будет создана, диалог продолжится здесь.",
    ]


def get_help_intro_lines(role: UserRole) -> list[str]:
    if role == UserRole.SUPER_ADMIN:
        return [
            "Справка суперадминистратора.",
            "Основные разделы открываются из меню, действия по заявке находятся в её карточке.",
        ]
    if role == UserRole.OPERATOR:
        return [
            "Справка оператора.",
            "Основные разделы открываются из меню, действия по заявке находятся в её карточке.",
        ]
    return [
        "Справка.",
        "Чтобы начать новое обращение, просто напишите сообщение в этот чат.",
    ]


def get_help_guidance_lines(role: UserRole, *, mini_app_available: bool = False) -> list[str]:
    if role == UserRole.SUPER_ADMIN:
        lines = [
            "«Очередь» - открыть новые заявки.",
            "«Взять следующую» - быстро забрать ближайшую заявку.",
            "«Мои заявки» - вернуться к своим активным диалогам.",
            "«Архив» - открыть закрытые заявки и отчёты.",
            "«Статистика» - посмотреть текущую нагрузку.",
            "«Операторы» - открыть состав команды и управление ролями.",
            "«Макросы» - открыть библиотеку и редактирование макросов.",
            "«Темы» - настроить темы новых обращений.",
            "«Отмена» - выйти из текущего шага.",
        ]
        if mini_app_available:
            lines.insert(
                0,
                "Кнопка меню «Панель» - открыть Mini App с обзором, очередью и аналитикой.",
            )
        else:
            lines.insert(
                0,
                (
                    "Если кнопки меню «Панель» нет, "
                    "проверьте публичный HTTPS URL Mini App в настройках."
                ),
            )
        return lines
    if role == UserRole.OPERATOR:
        lines = [
            "«Очередь» - открыть новые заявки.",
            "«Взять следующую» - сразу взять ближайшую заявку.",
            "«Мои заявки» - вернуться к активным диалогам.",
            "«Архив» - открыть закрытые заявки и отчёты.",
            "«Статистика» - посмотреть текущую нагрузку.",
            "«Отмена» - выйти из текущего шага.",
        ]
        if mini_app_available:
            lines.insert(
                0,
                ("Кнопка меню «Панель» - открыть Mini App с обзором, очередью и карточкой заявки."),
            )
        else:
            lines.insert(
                0,
                (
                    "Если кнопки меню «Панель» нет, "
                    "Mini App сейчас недоступен и работа продолжается в меню."
                ),
            )
        return lines
    return [
        "Напишите сообщение, чтобы начать новое обращение.",
        "Сначала бот предложит выбрать тему, затем попросит коротко описать вопрос.",
        "Когда оператор ответит, диалог продолжится в этом чате.",
    ]


def get_help_command_lines() -> tuple[str, str]:
    return (
        "/start - открыть меню заново",
        "/help - показать краткую справку",
    )
