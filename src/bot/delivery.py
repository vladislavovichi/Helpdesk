from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)

DEFAULT_SEND_ATTEMPTS = 3


async def send_message_with_retry(
    bot: Bot,
    *,
    chat_id: int,
    text: str,
    logger: logging.Logger,
    operation: str,
) -> None:
    for attempt in range(1, DEFAULT_SEND_ATTEMPTS + 1):
        try:
            await bot.send_message(chat_id, text)
            if attempt > 1:
                logger.info(
                    "Telegram delivery recovered operation=%s chat_id=%s attempt=%s",
                    operation,
                    chat_id,
                    attempt,
                )
            return
        except TelegramRetryAfter as exc:
            logger.warning(
                "Telegram delivery rate-limited operation=%s chat_id=%s attempt=%s retry_after=%s",
                operation,
                chat_id,
                attempt,
                exc.retry_after,
            )
            if attempt >= DEFAULT_SEND_ATTEMPTS:
                raise
            await asyncio.sleep(min(max(exc.retry_after, 1), 5))
        except (TelegramNetworkError, TelegramServerError) as exc:
            logger.warning(
                "Telegram delivery transient failure operation=%s chat_id=%s attempt=%s error=%s",
                operation,
                chat_id,
                attempt,
                exc,
            )
            if attempt >= DEFAULT_SEND_ATTEMPTS:
                raise
            await asyncio.sleep(min(0.5 * (2 ** (attempt - 1)), 2.0))
        except TelegramAPIError:
            raise
