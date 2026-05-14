from types import TracebackType
from typing import Self

from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import LockError

from application.contracts.runtime import TicketLock, TicketLockManager
from infrastructure.redis.keys import ticket_lock_key


class RedisTicketLock(TicketLock):
    def __init__(self, redis: Redis, *, key: str) -> None:
        self.redis = redis
        self.key = key
        self._lock: Lock | None = None
        self._is_acquired = False

    async def acquire(self, *, ttl_seconds: int = 30) -> bool:
        self._lock = self.redis.lock(
            self.key,
            timeout=ttl_seconds,
            blocking=False,
            thread_local=False,
        )
        self._is_acquired = bool(await self._lock.acquire(blocking=False))
        if not self._is_acquired:
            self._lock = None
        return self._is_acquired

    async def release(self) -> None:
        if not self._is_acquired or self._lock is None:
            return

        try:
            await self._lock.release()
        except LockError:
            pass
        finally:
            self._is_acquired = False
            self._lock = None

    async def __aenter__(self) -> Self:
        if await self.acquire():
            return self
        raise LockError("Unable to acquire ticket lock.")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.release()


class RedisTicketLockManager(TicketLockManager):
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def for_ticket(self, ticket_id: str | int) -> TicketLock:
        return RedisTicketLock(self.redis, key=ticket_lock_key(ticket_id))
