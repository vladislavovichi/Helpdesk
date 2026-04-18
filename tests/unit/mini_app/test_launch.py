from __future__ import annotations

from mini_app.launch import resolve_mini_app_launch


def test_resolve_mini_app_launch_prefers_header_value() -> None:
    launch = resolve_mini_app_launch(
        path="/api/session?init_data=query-value",
        headers={
            "X-Telegram-Init-Data": "header-value",
            "X-Mini-App-Launch-Source": "telegram-web-app",
        },
    )

    assert launch.init_data == "header-value"
    assert launch.source == "header:x-telegram-init-data"
    assert launch.client_source == "telegram-web-app"


def test_resolve_mini_app_launch_supports_telegram_query_fallback() -> None:
    launch = resolve_mini_app_launch(
        path="/api/session?tgWebAppData=user%3D1%26hash%3Dabc",
        headers={},
    )

    assert launch.init_data == "user=1&hash=abc"
    assert launch.source == "query:tgWebAppData"


def test_resolve_mini_app_launch_marks_missing_init_data_with_diagnostics() -> None:
    launch = resolve_mini_app_launch(
        path="/api/session?tgWebAppVersion=8.0",
        headers={},
    )

    assert launch.init_data == ""
    assert launch.source == "missing"
    assert "telegram-launch-markers-present" in launch.diagnostics
    assert "init_data_missing" in launch.diagnostics
