from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.exceptions import LockError

from application.contracts.runtime import TicketStreamMessage
from infrastructure.redis.locks import RedisTicketLock
from infrastructure.redis.sla import RedisSLADeadlineScheduler, RedisSLATimeoutProcessor
from infrastructure.redis.streams import RedisTicketStreamConsumer


class InMemoryRedisLockClient:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.expires_at_ms: dict[str, int] = {}
        self.now_ms = 0
        self.lock_calls: list[dict[str, Any]] = []

        Lock.lua_release = None
        Lock.lua_extend = None
        Lock.lua_reacquire = None

    def advance(self, *, seconds: float) -> None:
        self.now_ms += int(seconds * 1000)

    def lock(
        self,
        name: str,
        timeout: float | None = None,
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
        thread_local: bool = True,
    ) -> Lock:
        self.lock_calls.append(
            {
                "name": name,
                "timeout": timeout,
                "sleep": sleep,
                "blocking": blocking,
                "blocking_timeout": blocking_timeout,
                "thread_local": thread_local,
            }
        )
        return Lock(
            cast(Any, self),
            name,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
        )

    async def set(
        self,
        name: str,
        value: bytes,
        nx: bool = False,
        px: int | None = None,
    ) -> bool:
        self._purge_if_expired(name)
        if nx and name in self.values:
            return False
        self.values[name] = value
        if px is None:
            self.expires_at_ms.pop(name, None)
        else:
            self.expires_at_ms[name] = self.now_ms + px
        return True

    async def get(self, name: str) -> bytes | None:
        self._purge_if_expired(name)
        return self.values.get(name)

    def register_script(self, script: str) -> Any:
        class RegisteredScript:
            async def __call__(
                self,
                *,
                keys: list[str],
                args: list[bytes],
                client: InMemoryRedisLockClient,
            ) -> int:
                name = keys[0]
                expected_token = args[0]
                client._purge_if_expired(name)
                if client.values.get(name) != expected_token:
                    return 0
                client.values.pop(name, None)
                client.expires_at_ms.pop(name, None)
                return 1

        return RegisteredScript()

    def _purge_if_expired(self, name: str) -> None:
        expires_at = self.expires_at_ms.get(name)
        if expires_at is not None and expires_at <= self.now_ms:
            self.values.pop(name, None)
            self.expires_at_ms.pop(name, None)


def redis_lock_client() -> tuple[InMemoryRedisLockClient, Redis]:
    client = InMemoryRedisLockClient()
    return client, cast(Redis, client)


async def test_ticket_stream_consumer_returns_structured_messages() -> None:
    redis = Mock()
    redis.xread = AsyncMock(
        return_value=[
            (
                "tickets:new",
                [
                    (
                        "1-0",
                        {
                            "ticket_id": "ticket-1",
                            "client_chat_id": "2002",
                            "subject": "Нужна помощь",
                        },
                    )
                ],
            )
        ]
    )
    consumer = RedisTicketStreamConsumer(redis)

    result = await consumer.read_new_ticket_messages(last_id="0-0")

    assert result == [
        TicketStreamMessage(
            message_id="1-0",
            ticket_id="ticket-1",
            client_chat_id=2002,
            subject="Нужна помощь",
        )
    ]


async def test_sla_deadline_scheduler_claims_due_ticket_ids() -> None:
    redis = Mock()
    redis.eval = AsyncMock(return_value=["ticket-1", "ticket-2"])
    scheduler = RedisSLADeadlineScheduler(redis)

    due = await scheduler.claim_due(until=datetime.now(UTC), limit=10)

    assert list(due) == ["ticket-1", "ticket-2"]
    redis.eval.assert_awaited_once()


async def test_sla_timeout_processor_claims_due_ticket_ids_before_counting() -> None:
    scheduler = Mock()
    scheduler.claim_due = AsyncMock(return_value=["ticket-1", "ticket-2", "ticket-3"])
    processor = RedisSLATimeoutProcessor(scheduler)

    due_ticket_ids = await processor.claim_due_ticket_ids(limit=50)
    claimed_count = await processor.run_once(limit=50)

    assert list(due_ticket_ids) == ["ticket-1", "ticket-2", "ticket-3"]
    assert claimed_count == 3


async def test_ticket_lock_configures_redis_py_lock_for_non_blocking_ttl() -> None:
    redis, redis_for_lock = redis_lock_client()
    lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    acquired = await lock.acquire(ttl_seconds=45)
    await lock.release()

    assert acquired is True
    assert redis.lock_calls == [
        {
            "name": "ticket-lock:1",
            "timeout": 45,
            "sleep": 0.1,
            "blocking": False,
            "blocking_timeout": None,
            "thread_local": False,
        }
    ]
    assert await redis.get("ticket-lock:1") is None


async def test_ticket_lock_cannot_be_acquired_twice_concurrently() -> None:
    redis, redis_for_lock = redis_lock_client()
    first_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")
    second_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    first_acquired = await first_lock.acquire(ttl_seconds=10)
    second_acquired = await second_lock.acquire(ttl_seconds=10)

    assert first_acquired is True
    assert second_acquired is False


async def test_ticket_lock_does_not_release_when_acquire_failed() -> None:
    redis, redis_for_lock = redis_lock_client()
    first_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")
    second_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    assert await first_lock.acquire(ttl_seconds=10) is True
    assert await second_lock.acquire(ttl_seconds=10) is False
    await second_lock.release()

    assert await redis.get("ticket-lock:1") is not None


async def test_ticket_lock_release_does_not_delete_another_owner_after_expiry() -> None:
    redis, redis_for_lock = redis_lock_client()
    first_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")
    second_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    assert await first_lock.acquire(ttl_seconds=1) is True
    redis.advance(seconds=1.1)
    assert await second_lock.acquire(ttl_seconds=10) is True

    second_owner_token = await redis.get("ticket-lock:1")
    await first_lock.release()

    assert await redis.get("ticket-lock:1") == second_owner_token


async def test_ticket_lock_ignores_release_after_ttl_expiry() -> None:
    redis, redis_for_lock = redis_lock_client()
    lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    acquired = await lock.acquire(ttl_seconds=10)
    redis.advance(seconds=10.1)
    await lock.release()

    assert acquired is True
    assert await redis.get("ticket-lock:1") is None


async def test_ticket_lock_context_manager_releases_on_success() -> None:
    redis, redis_for_lock = redis_lock_client()

    async with RedisTicketLock(redis_for_lock, key="ticket-lock:1"):
        assert await redis.get("ticket-lock:1") is not None

    assert await redis.get("ticket-lock:1") is None


async def test_ticket_lock_context_manager_releases_on_exception() -> None:
    redis, redis_for_lock = redis_lock_client()

    with pytest.raises(RuntimeError, match="handler failed"):
        async with RedisTicketLock(redis_for_lock, key="ticket-lock:1"):
            assert await redis.get("ticket-lock:1") is not None
            raise RuntimeError("handler failed")

    assert await redis.get("ticket-lock:1") is None


async def test_ticket_lock_context_manager_raises_when_lock_is_held() -> None:
    redis, redis_for_lock = redis_lock_client()
    held_lock = RedisTicketLock(redis_for_lock, key="ticket-lock:1")

    assert await held_lock.acquire(ttl_seconds=10) is True

    with pytest.raises(LockError, match="Unable to acquire ticket lock"):
        async with RedisTicketLock(redis_for_lock, key="ticket-lock:1"):
            pass
