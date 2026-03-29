from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from application.services.helpdesk import HelpdeskService, HelpdeskServiceFactory
from bot.dispatcher import build_bot, build_dispatcher
from infrastructure.config import Settings
from infrastructure.db.repositories import (
    SqlAlchemyOperatorRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketMessageRepository,
    SqlAlchemyTicketRepository,
)
from infrastructure.db.session import (
    build_engine,
    build_session_factory,
    dispose_engine,
    session_scope,
)
from infrastructure.redis.client import build_redis_client, close_redis_client, ping_redis_client


@dataclass(slots=True)
class AppRuntime:
    settings: Settings
    db_engine: AsyncEngine
    db_session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    helpdesk_service_factory: HelpdeskServiceFactory
    dispatcher: Dispatcher | None = None
    bot: Bot | None = None


def build_helpdesk_service(session: AsyncSession) -> HelpdeskService:
    return HelpdeskService(
        ticket_repository=SqlAlchemyTicketRepository(session),
        ticket_message_repository=SqlAlchemyTicketMessageRepository(session),
        operator_repository=SqlAlchemyOperatorRepository(session),
        tag_repository=SqlAlchemyTagRepository(session),
    )


def build_helpdesk_service_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> HelpdeskServiceFactory:
    @asynccontextmanager
    async def provide() -> AsyncIterator[HelpdeskService]:
        async with session_scope(session_factory) as session:
            yield build_helpdesk_service(session)

    return provide


async def build_runtime(settings: Settings) -> AppRuntime:
    db_engine = build_engine(settings.database)
    db_session_factory = build_session_factory(db_engine)
    helpdesk_service_factory = build_helpdesk_service_factory(db_session_factory)
    redis = build_redis_client(settings.redis)
    bot: Bot | None = None

    try:
        await ping_redis_client(redis)

        dispatcher: Dispatcher | None = None
        if settings.bot.token:
            bot = build_bot(settings.bot)
            dispatcher = build_dispatcher(
                settings=settings,
                db_session_factory=db_session_factory,
                helpdesk_service_factory=helpdesk_service_factory,
                redis=redis,
            )

        return AppRuntime(
            settings=settings,
            db_engine=db_engine,
            db_session_factory=db_session_factory,
            redis=redis,
            helpdesk_service_factory=helpdesk_service_factory,
            dispatcher=dispatcher,
            bot=bot,
        )
    except Exception:
        if bot is not None:
            await bot.session.close()
        await close_redis_client(redis)
        await dispose_engine(db_engine)
        raise


async def close_runtime(runtime: AppRuntime) -> None:
    if runtime.bot is not None:
        await runtime.bot.session.close()

    await close_redis_client(runtime.redis)
    await dispose_engine(runtime.db_engine)
