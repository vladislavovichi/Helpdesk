from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest

from mini_app.auth import TelegramMiniAppAuthError, validate_telegram_mini_app_init_data


def test_validate_telegram_mini_app_init_data_accepts_signed_payload() -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    init_data = _build_init_data(bot_token="123:ABC", auth_date=now)

    result = validate_telegram_mini_app_init_data(
        init_data=init_data,
        bot_token="123:ABC",
        max_age_seconds=3600,
        now=now,
    )

    assert result.user.telegram_user_id == 1001
    assert result.user.display_name == "Анна Смирнова"


def test_validate_telegram_mini_app_init_data_rejects_expired_payload() -> None:
    auth_date = datetime(2026, 4, 14, 9, 0, tzinfo=UTC)
    now = auth_date + timedelta(hours=2)
    init_data = _build_init_data(bot_token="123:ABC", auth_date=auth_date)

    with pytest.raises(TelegramMiniAppAuthError):
        validate_telegram_mini_app_init_data(
            init_data=init_data,
            bot_token="123:ABC",
            max_age_seconds=300,
            now=now,
        )


def test_validate_telegram_mini_app_init_data_rejects_modified_payload() -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    init_data = _build_init_data(bot_token="123:ABC", auth_date=now).replace(
        "anna.support",
        "mallory",
    )

    with pytest.raises(TelegramMiniAppAuthError):
        validate_telegram_mini_app_init_data(
            init_data=init_data,
            bot_token="123:ABC",
            max_age_seconds=3600,
            now=now,
        )


def _build_init_data(*, bot_token: str, auth_date: datetime) -> str:
    values = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAEAAAE",
        "user": json.dumps(
            {
                "id": 1001,
                "first_name": "Анна",
                "last_name": "Смирнова",
                "username": "anna.support",
                "language_code": "ru",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)
