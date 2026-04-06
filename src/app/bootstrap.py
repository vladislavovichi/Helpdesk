from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from application.services.authorization import (
    AuthorizationService,
    AuthorizationServiceFactory,
)
from application.services.diagnostics import DiagnosticsService
from application.services.helpdesk.service import HelpdeskService, HelpdeskServiceFactory
from bot.dispatcher import build_bot, build_dispatcher
from infrastructure.config.settings import Settings
from infrastructure.db.repositories.catalog import (
    SqlAlchemyMacroRepository,
    SqlAlchemySLAPolicyRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketTagRepository,
)
from infrastructure.db.repositories.operators import SqlAlchemyOperatorRepository
from infrastructure.db.repositories.tickets import (
    SqlAlchemyTicketEventRepository,
    SqlAlchemyTicketMessageRepository,
    SqlAlchemyTicketRepository,
)
from infrastructure.db.session import (
    build_engine,
    build_session_factory,
    dispose_engine,
    ping_database_engine,
    session_scope,
)
from infrastructure.redis.client import (
    build_redis_client,
    close_redis_client,
    ping_redis_client,
)
from infrastructure.redis.contracts import (
    ChatRateLimiter,
    GlobalRateLimiter,
    OperatorPresenceHelper,
    SLADeadlineScheduler,
    SLATimeoutProcessor,
    TicketLockManager,
    TicketStreamConsumer,
    TicketStreamPublisher,
)
from infrastructure.redis.fsm import build_fsm_storage
from infrastructure.redis.locks import RedisTicketLockManager
from infrastructure.redis.presence import RedisOperatorPresenceHelper
from infrastructure.redis.rate_limit import RedisChatRateLimiter, RedisGlobalRateLimiter
from infrastructure.redis.sla import RedisSLADeadlineScheduler, RedisSLATimeoutProcessor
from infrastructure.redis.streams import (
    RedisTicketStreamConsumer,
    RedisTicketStreamPublisher,
)


@dataclass(slots=True)
class RedisWorkflowRuntime:
    ticket_lock_manager: TicketLockManager
    global_rate_limiter: GlobalRateLimiter
    chat_rate_limiter: ChatRateLimiter
    operator_presence: OperatorPresenceHelper
    sla_deadline_scheduler: SLADeadlineScheduler
    ticket_stream_publisher: TicketStreamPublisher
    ticket_stream_consumer: TicketStreamConsumer
    sla_timeout_processor: SLATimeoutProcessor


@dataclass(slots=True)
class AppRuntime:
    settings: Settings
    db_engine: AsyncEngine
    db_session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    fsm_storage: BaseStorage
    redis_workflow: RedisWorkflowRuntime
    authorization_service_factory: AuthorizationServiceFactory
    helpdesk_service_factory: HelpdeskServiceFactory
    diagnostics_service: DiagnosticsService
    dispatcher: Dispatcher | None = None
    bot: Bot | None = None


def build_authorization_service(
    session: AsyncSession,
    *,
    super_admin_telegram_user_ids: frozenset[int],
) -> AuthorizationService:
    return AuthorizationService(
        operator_repository=SqlAlchemyOperatorRepository(session),
        super_admin_telegram_user_ids=super_admin_telegram_user_ids,
    )


def build_authorization_service_factory(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    super_admin_telegram_user_ids: frozenset[int],
) -> AuthorizationServiceFactory:
    @asynccontextmanager
    async def provide() -> AsyncIterator[AuthorizationService]:
        async with session_scope(session_factory) as session:
            yield build_authorization_service(
                session,
                super_admin_telegram_user_ids=super_admin_telegram_user_ids,
            )

    return provide


def build_helpdesk_service(
    session: AsyncSession,
    *,
    super_admin_telegram_user_ids: frozenset[int],
    sla_deadline_scheduler: SLADeadlineScheduler | None = None,
) -> HelpdeskService:
    return HelpdeskService(
        ticket_repository=SqlAlchemyTicketRepository(session),
        ticket_message_repository=SqlAlchemyTicketMessageRepository(session),
        ticket_event_repository=SqlAlchemyTicketEventRepository(session),
        operator_repository=SqlAlchemyOperatorRepository(session),
        macro_repository=SqlAlchemyMacroRepository(session),
        sla_policy_repository=SqlAlchemySLAPolicyRepository(session),
        tag_repository=SqlAlchemyTagRepository(session),
        ticket_tag_repository=SqlAlchemyTicketTagRepository(session),
        sla_deadline_scheduler=sla_deadline_scheduler,
        super_admin_telegram_user_ids=super_admin_telegram_user_ids,
    )


def build_helpdesk_service_factory(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    super_admin_telegram_user_ids: frozenset[int],
    sla_deadline_scheduler: SLADeadlineScheduler | None = None,
) -> HelpdeskServiceFactory:
    @asynccontextmanager
    async def provide() -> AsyncIterator[HelpdeskService]:
        async with session_scope(session_factory) as session:
            yield build_helpdesk_service(
                session,
                super_admin_telegram_user_ids=super_admin_telegram_user_ids,
                sla_deadline_scheduler=sla_deadline_scheduler,
            )

    return provide


def build_redis_workflow_runtime(redis: Redis) -> RedisWorkflowRuntime:
    sla_deadline_scheduler = RedisSLADeadlineScheduler(redis)
    return RedisWorkflowRuntime(
        ticket_lock_manager=RedisTicketLockManager(redis),
        global_rate_limiter=RedisGlobalRateLimiter(redis),
        chat_rate_limiter=RedisChatRateLimiter(redis),
        operator_presence=RedisOperatorPresenceHelper(redis),
        sla_deadline_scheduler=sla_deadline_scheduler,
        ticket_stream_publisher=RedisTicketStreamPublisher(redis),
        ticket_stream_consumer=RedisTicketStreamConsumer(redis),
        sla_timeout_processor=RedisSLATimeoutProcessor(sla_deadline_scheduler),
    )


def build_diagnostics_service(
    *,
    settings: Settings,
    db_engine: AsyncEngine,
    redis: Redis,
    fsm_storage: BaseStorage,
    redis_workflow: RedisWorkflowRuntime,
    bot: Bot | None,
    dispatcher: Dispatcher | None,
) -> DiagnosticsService:
    return DiagnosticsService(
        database_check=lambda: ping_database_engine(db_engine),
        redis_check=lambda: ping_redis_client(redis),
        dry_run=settings.app.dry_run,
        bot_configured=bool(settings.bot.token.strip()),
        bot_initialized=bot is not None,
        dispatcher_initialized=dispatcher is not None,
        fsm_storage_initialized=fsm_storage is not None,
        redis_workflow_initialized=redis_workflow is not None,
    )


def _validate_startup_settings(settings: Settings) -> None:
    if settings.app.dry_run:
        return

    if not settings.bot.token.strip():
        raise RuntimeError("Невозможно запустить polling: BOT__TOKEN не задан.")


def _database_target(settings: Settings) -> str:
    return (
        settings.database.url
        or f"{settings.database.host}:{settings.database.port}/{settings.database.database}"
    )


def _redis_target(settings: Settings) -> str:
    return settings.redis.url or f"{settings.redis.host}:{settings.redis.port}/{settings.redis.db}"


async def _close_runtime_resources(
    *,
    db_engine: AsyncEngine | None = None,
    redis: Redis | None = None,
    fsm_storage: BaseStorage | None = None,
    bot: Bot | None = None,
) -> None:
    logger = logging.getLogger(__name__)

    if bot is not None:
        try:
            await bot.session.close()
        except Exception:
            logger.exception("Failed to close Telegram bot session cleanly.")

    if fsm_storage is not None:
        try:
            await fsm_storage.close()
        except Exception:
            logger.exception("Failed to close FSM storage cleanly.")

    if redis is not None:
        try:
            await close_redis_client(redis)
        except Exception:
            logger.exception("Failed to close Redis client cleanly.")

    if db_engine is not None:
        try:
            await dispose_engine(db_engine)
        except Exception:
            logger.exception("Failed to dispose SQLAlchemy engine cleanly.")


async def build_runtime(settings: Settings) -> AppRuntime:
    logger = logging.getLogger(__name__)
    _validate_startup_settings(settings)
    logger.info(
        "Initializing runtime dependencies database=%s redis=%s dry_run=%s",
        _database_target(settings),
        _redis_target(settings),
        settings.app.dry_run,
    )

    db_engine = build_engine(settings.database)
    db_session_factory = build_session_factory(db_engine)
    super_admin_telegram_user_ids = frozenset(settings.authorization.super_admin_telegram_user_ids)
    authorization_service_factory = build_authorization_service_factory(
        db_session_factory,
        super_admin_telegram_user_ids=super_admin_telegram_user_ids,
    )
    redis: Redis | None = None
    fsm_storage: BaseStorage | None = None
    redis_workflow: RedisWorkflowRuntime | None = None
    helpdesk_service_factory: HelpdeskServiceFactory | None = None
    diagnostics_service: DiagnosticsService | None = None
    bot: Bot | None = None
    dispatcher: Dispatcher | None = None

    try:
        logger.info("Checking PostgreSQL connectivity.")
        await ping_database_engine(db_engine)
        logger.info("PostgreSQL connectivity check passed.")

        redis = build_redis_client(settings.redis)
        logger.info("Checking Redis connectivity.")
        await ping_redis_client(redis)
        logger.info("Redis connectivity check passed.")

        fsm_storage = build_fsm_storage(redis)
        redis_workflow = build_redis_workflow_runtime(redis)
        helpdesk_service_factory = build_helpdesk_service_factory(
            db_session_factory,
            super_admin_telegram_user_ids=super_admin_telegram_user_ids,
            sla_deadline_scheduler=redis_workflow.sla_deadline_scheduler,
        )

        if settings.bot.token.strip():
            logger.info("Initializing Telegram bot runtime.")
            bot = build_bot(settings.bot)
            dispatcher = build_dispatcher(
                storage=fsm_storage,
                settings=settings,
                authorization_service_factory=authorization_service_factory,
                helpdesk_service_factory=helpdesk_service_factory,
                global_rate_limiter=redis_workflow.global_rate_limiter,
                chat_rate_limiter=redis_workflow.chat_rate_limiter,
                operator_presence=redis_workflow.operator_presence,
                ticket_lock_manager=redis_workflow.ticket_lock_manager,
                ticket_stream_publisher=redis_workflow.ticket_stream_publisher,
            )
        else:
            logger.info(
                "Telegram bot runtime is skipped because BOT__TOKEN is empty "
                "and dry-run mode is enabled."
            )

        diagnostics_service = build_diagnostics_service(
            settings=settings,
            db_engine=db_engine,
            redis=redis,
            fsm_storage=fsm_storage,
            redis_workflow=redis_workflow,
            bot=bot,
            dispatcher=dispatcher,
        )
        if dispatcher is not None:
            dispatcher.workflow_data["diagnostics_service"] = diagnostics_service

        logger.info("Runtime dependencies initialized successfully.")

        return AppRuntime(
            settings=settings,
            db_engine=db_engine,
            db_session_factory=db_session_factory,
            redis=redis,
            fsm_storage=fsm_storage,
            redis_workflow=redis_workflow,
            authorization_service_factory=authorization_service_factory,
            helpdesk_service_factory=helpdesk_service_factory,
            diagnostics_service=diagnostics_service,
            dispatcher=dispatcher,
            bot=bot,
        )
    except Exception:
        logger.exception("Runtime initialization failed.")
        await _close_runtime_resources(
            db_engine=db_engine,
            redis=redis,
            fsm_storage=fsm_storage,
            bot=bot,
        )
        raise


async def close_runtime(runtime: AppRuntime) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Closing runtime resources.")
    await _close_runtime_resources(
        db_engine=runtime.db_engine,
        redis=runtime.redis,
        fsm_storage=runtime.fsm_storage,
        bot=runtime.bot,
    )
    logger.info("Runtime resources closed.")
