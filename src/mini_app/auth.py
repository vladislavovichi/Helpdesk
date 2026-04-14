from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl


class TelegramMiniAppAuthError(ValueError):
    """Raised when Telegram Mini App init data is missing or invalid."""


@dataclass(slots=True, frozen=True)
class TelegramMiniAppUser:
    telegram_user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None

    @property
    def display_name(self) -> str:
        parts = [self.first_name.strip()]
        if self.last_name:
            parts.append(self.last_name.strip())
        display_name = " ".join(part for part in parts if part)
        if display_name:
            return display_name
        if self.username:
            return self.username
        return f"Оператор {self.telegram_user_id}"


@dataclass(slots=True, frozen=True)
class ValidatedMiniAppInitData:
    raw_init_data: str
    auth_date: datetime
    user: TelegramMiniAppUser


def validate_telegram_mini_app_init_data(
    *,
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
    now: datetime | None = None,
) -> ValidatedMiniAppInitData:
    normalized_init_data = init_data.strip()
    normalized_bot_token = bot_token.strip()
    if not normalized_init_data:
        raise TelegramMiniAppAuthError("Mini App открыт без Telegram init data.")
    if not normalized_bot_token:
        raise TelegramMiniAppAuthError("BOT__TOKEN не настроен для проверки Mini App.")

    pairs = parse_qsl(normalized_init_data, keep_blank_values=True, strict_parsing=True)
    values = dict(pairs)
    provided_hash = values.pop("hash", "").strip()
    if not provided_hash:
        raise TelegramMiniAppAuthError("В Telegram init data отсутствует подпись.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(
        b"WebAppData",
        normalized_bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, provided_hash):
        raise TelegramMiniAppAuthError("Telegram init data не прошёл проверку подписи.")

    auth_timestamp_raw = values.get("auth_date", "").strip()
    if not auth_timestamp_raw:
        raise TelegramMiniAppAuthError("В Telegram init data отсутствует auth_date.")
    try:
        auth_date = datetime.fromtimestamp(int(auth_timestamp_raw), tz=UTC)
    except ValueError as exc:
        raise TelegramMiniAppAuthError("Некорректный auth_date в Telegram init data.") from exc

    current_time = now or datetime.now(UTC)
    if max_age_seconds > 0 and (current_time - auth_date).total_seconds() > max_age_seconds:
        raise TelegramMiniAppAuthError("Сеанс Mini App устарел. Откройте рабочее место заново.")

    user_raw = values.get("user", "").strip()
    if not user_raw:
        raise TelegramMiniAppAuthError("В Telegram init data отсутствует пользователь.")
    try:
        payload = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramMiniAppAuthError("Telegram user payload повреждён.") from exc

    user_id = payload.get("id")
    first_name = payload.get("first_name")
    if not isinstance(user_id, int) or user_id <= 0 or not isinstance(first_name, str):
        raise TelegramMiniAppAuthError("Telegram user payload неполный.")

    return ValidatedMiniAppInitData(
        raw_init_data=normalized_init_data,
        auth_date=auth_date,
        user=TelegramMiniAppUser(
            telegram_user_id=user_id,
            first_name=first_name,
            last_name=payload.get("last_name")
            if isinstance(payload.get("last_name"), str)
            else None,
            username=payload.get("username") if isinstance(payload.get("username"), str) else None,
            language_code=payload.get("language_code")
            if isinstance(payload.get("language_code"), str)
            else None,
        ),
    )
