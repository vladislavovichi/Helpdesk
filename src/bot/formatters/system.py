from __future__ import annotations

from bot.texts.system import (
    format_diagnostics_report,
    get_help_command_lines,
    get_help_guidance_lines,
    get_help_intro_lines,
    get_start_lines,
)
from domain.enums.roles import UserRole


def build_start_text(role: UserRole, *, mini_app_available: bool = False) -> str:
    return "\n".join(get_start_lines(role, mini_app_available=mini_app_available))


def build_help_text(role: UserRole, *, mini_app_available: bool = False) -> str:
    lines = [*get_help_intro_lines(role)]
    guidance_lines = get_help_guidance_lines(role, mini_app_available=mini_app_available)
    if guidance_lines:
        lines.extend(["", "Навигация", *guidance_lines])
    lines.extend(["", "Команды", *get_help_command_lines()])
    return "\n".join(lines)


__all__ = ["build_help_text", "build_start_text", "format_diagnostics_report"]
