from __future__ import annotations

from redis.asyncio import Redis

from application.contracts.runtime import ChatRateLimiter, GlobalRateLimiter
from infrastructure.redis.keys import GLOBAL_RATE_LIMIT_KEY, chat_rate_limit_key

_INCR_WITH_EXPIRE_LUA = """
local c = redis.call('incr', KEYS[1])
if c == 1 then redis.call('expire', KEYS[1], ARGV[1]) end
return c
"""


class RedisFixedWindowRateLimiter:
    def __init__(self, redis: Redis, *, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    async def allow_key(self, key: str) -> bool:
        current = int(await self.redis.eval(_INCR_WITH_EXPIRE_LUA, 1, key, self.window_seconds))  # type: ignore[misc]
        return current <= self.limit


class RedisGlobalRateLimiter(GlobalRateLimiter):
    def __init__(self, redis: Redis, *, limit: int = 30, window_seconds: int = 1) -> None:
        self._limiter = RedisFixedWindowRateLimiter(
            redis,
            limit=limit,
            window_seconds=window_seconds,
        )

    async def allow(self) -> bool:
        return await self._limiter.allow_key(GLOBAL_RATE_LIMIT_KEY)


class RedisChatRateLimiter(ChatRateLimiter):
    def __init__(self, redis: Redis, *, limit: int = 5, window_seconds: int = 10) -> None:
        self._limiter = RedisFixedWindowRateLimiter(
            redis,
            limit=limit,
            window_seconds=window_seconds,
        )

    async def allow(self, *, chat_id: int) -> bool:
        return await self._limiter.allow_key(chat_rate_limit_key(chat_id))
