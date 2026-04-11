from __future__ import annotations

from typing import Literal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from application.services.stats import AnalyticsWindow
from bot.callbacks import OperatorStatsCallback, OperatorStatsExportCallback

AnalyticsSection = Literal["overview", "operators", "topics", "quality", "sla"]


def build_operator_stats_markup(
    *,
    section: AnalyticsSection,
    window: AnalyticsWindow,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        _button("Общая", section="overview", active=section == "overview", window=window),
        _button("Операторы", section="operators", active=section == "operators", window=window),
        _button("Темы", section="topics", active=section == "topics", window=window),
    )
    builder.row(
        _button("Качество", section="quality", active=section == "quality", window=window),
        _button("SLA", section="sla", active=section == "sla", window=window),
    )
    builder.row(
        InlineKeyboardButton(
            text="Экспорт отчёта",
            callback_data=OperatorStatsExportCallback(
                action="open",
                section=section,
                window=window.value,
            ).pack(),
        )
    )
    builder.row(
        _button(
            "Сегодня",
            section=section,
            active=window == AnalyticsWindow.TODAY,
            window=AnalyticsWindow.TODAY,
        ),
        _button(
            "7 дн",
            section=section,
            active=window == AnalyticsWindow.DAYS_7,
            window=AnalyticsWindow.DAYS_7,
        ),
        _button(
            "30 дн",
            section=section,
            active=window == AnalyticsWindow.DAYS_30,
            window=AnalyticsWindow.DAYS_30,
        ),
        _button(
            "Всё",
            section=section,
            active=window == AnalyticsWindow.ALL,
            window=AnalyticsWindow.ALL,
        ),
    )
    return builder.as_markup()


def build_operator_stats_export_markup(
    *,
    section: AnalyticsSection,
    window: AnalyticsWindow,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="CSV",
            callback_data=OperatorStatsExportCallback(
                action="csv",
                section=section,
                window=window.value,
            ).pack(),
        ),
        InlineKeyboardButton(
            text="HTML отчёт",
            callback_data=OperatorStatsExportCallback(
                action="html",
                section=section,
                window=window.value,
            ).pack(),
        ),
    )
    builder.row(
        _button(
            "Назад",
            section=section,
            active=False,
            window=window,
        )
    )
    return builder.as_markup()


def _button(
    text: str,
    *,
    section: AnalyticsSection,
    active: bool,
    window: AnalyticsWindow,
) -> InlineKeyboardButton:
    label = f"• {text}" if active else text
    return InlineKeyboardButton(
        text=label,
        callback_data=OperatorStatsCallback(section=section, window=window.value).pack(),
    )
