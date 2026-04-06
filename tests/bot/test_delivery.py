from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from pytest import MonkeyPatch

from bot.delivery import send_message_with_retry


async def test_send_message_with_retry_recovers_from_network_error(
    monkeypatch: MonkeyPatch,
) -> None:
    bot = Mock()
    bot.send_message = AsyncMock(
        side_effect=[TelegramNetworkError(Mock(), "temporary network issue"), None]
    )
    sleep = AsyncMock()
    monkeypatch.setattr("bot.delivery.asyncio.sleep", sleep)

    await send_message_with_retry(
        bot,
        chat_id=42,
        text="hello",
        logger=logging.getLogger("test"),
        operation="operator_reply",
    )

    assert bot.send_message.await_count == 2
    sleep.assert_awaited_once()


async def test_send_message_with_retry_honors_retry_after(monkeypatch: MonkeyPatch) -> None:
    bot = Mock()
    bot.send_message = AsyncMock(
        side_effect=[TelegramRetryAfter(Mock(), "too many requests", 4), None]
    )
    sleep = AsyncMock()
    monkeypatch.setattr("bot.delivery.asyncio.sleep", sleep)

    await send_message_with_retry(
        bot,
        chat_id=42,
        text="hello",
        logger=logging.getLogger("test"),
        operation="apply_macro",
    )

    sleep.assert_awaited_once_with(4)


async def test_send_message_with_retry_raises_after_last_attempt(
    monkeypatch: MonkeyPatch,
) -> None:
    bot = Mock()
    bot.send_message = AsyncMock(side_effect=TelegramNetworkError(Mock(), "still failing"))
    sleep = AsyncMock()
    monkeypatch.setattr("bot.delivery.asyncio.sleep", sleep)

    with pytest.raises(TelegramNetworkError):
        await send_message_with_retry(
            bot,
            chat_id=42,
            text="hello",
            logger=logging.getLogger("test"),
            operation="operator_reply",
        )

    assert bot.send_message.await_count == 3
    assert sleep.await_count == 2
