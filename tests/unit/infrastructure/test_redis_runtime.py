from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

from redis.exceptions import LockError

from application.contracts.runtime import TicketStreamMessage
from infrastructure.redis.keys import SLA_DEADLINES_KEY
from infrastructure.redis.locks import RedisTicketLock
from infrastructure.redis.sla import RedisSLADeadlineScheduler, RedisSLATimeoutProcessor
from infrastructure.redis.streams import RedisTicketStreamConsumer


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
    redis.zrangebyscore = AsyncMock(return_value=["ticket-1", "ticket-2"])
    redis.zrem = AsyncMock()
    scheduler = RedisSLADeadlineScheduler(redis)

    due = await scheduler.claim_due(until=datetime.now(UTC), limit=10)

    assert list(due) == ["ticket-1", "ticket-2"]
    redis.zrem.assert_awaited_once_with(SLA_DEADLINES_KEY, "ticket-1", "ticket-2")


async def test_sla_timeout_processor_claims_due_ticket_ids_before_counting() -> None:
    scheduler = Mock()
    scheduler.claim_due = AsyncMock(return_value=["ticket-1", "ticket-2", "ticket-3"])
    processor = RedisSLATimeoutProcessor(scheduler)

    due_ticket_ids = await processor.claim_due_ticket_ids(limit=50)
    claimed_count = await processor.run_once(limit=50)

    assert list(due_ticket_ids) == ["ticket-1", "ticket-2", "ticket-3"]
    assert claimed_count == 3


async def test_ticket_lock_uses_ttl_and_owner_token_for_safe_release() -> None:
    redis_lock = Mock()
    redis_lock.acquire = AsyncMock(return_value=True)
    redis_lock.release = AsyncMock()
    redis = Mock()
    redis.lock = Mock(return_value=redis_lock)
    lock = RedisTicketLock(redis, key="ticket-lock:1")

    acquired = await lock.acquire(ttl_seconds=45)
    await lock.release()

    assert acquired is True
    redis.lock.assert_called_once_with(
        "ticket-lock:1",
        timeout=45,
        blocking=False,
        thread_local=False,
    )
    redis_lock.acquire.assert_awaited_once_with(blocking=False)
    redis_lock.release.assert_awaited_once()


async def test_ticket_lock_does_not_release_when_acquire_failed() -> None:
    redis_lock = Mock()
    redis_lock.acquire = AsyncMock(return_value=False)
    redis_lock.release = AsyncMock()
    redis = Mock()
    redis.lock = Mock(return_value=redis_lock)
    lock = RedisTicketLock(redis, key="ticket-lock:1")

    acquired = await lock.acquire(ttl_seconds=10)
    await lock.release()

    assert acquired is False
    redis_lock.release.assert_not_awaited()


async def test_ticket_lock_ignores_release_after_ttl_expiry() -> None:
    redis_lock = Mock()
    redis_lock.acquire = AsyncMock(return_value=True)
    redis_lock.release = AsyncMock(side_effect=LockError("no longer owned"))
    redis = Mock()
    redis.lock = Mock(return_value=redis_lock)
    lock = RedisTicketLock(redis, key="ticket-lock:1")

    acquired = await lock.acquire(ttl_seconds=10)
    await lock.release()

    assert acquired is True
    redis_lock.release.assert_awaited_once()
