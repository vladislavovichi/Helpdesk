from __future__ import annotations

import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.runtime import RedisWorkflowRuntime
from app.runtime_factories import (
    build_helpdesk_ai_generation_profile,
    build_helpdesk_ai_provider,
    build_helpdesk_service_factory,
    build_redis_workflow_runtime,
)
from backend.grpc.server import build_helpdesk_backend_server
from backend.runtime import BackendRuntime
from infrastructure.config.settings import Settings
from infrastructure.db.session import (
    build_engine,
    build_session_factory,
    dispose_engine,
    ping_database_engine,
)
from infrastructure.redis.client import (
    build_redis_client,
    close_redis_client,
    ping_redis_client,
)
from infrastructure.startup_checks import (
    StartupDependencyCheck,
    run_startup_dependency_checks,
    validate_backend_startup_settings,
)


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
) -> None:
    logger = logging.getLogger(__name__)

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


async def build_runtime(settings: Settings) -> BackendRuntime:
    logger = logging.getLogger(__name__)
    try:
        validate_backend_startup_settings(settings)
    except Exception:
        logger.exception("Backend startup configuration is invalid.")
        raise
    logger.info(
        "Initializing backend runtime database=%s redis=%s grpc_bind=%s",
        _database_target(settings),
        _redis_target(settings),
        settings.backend_service.bind_target,
    )

    db_engine = build_engine(settings.database)
    db_session_factory = build_session_factory(db_engine)
    redis: Redis | None = None
    redis_workflow: RedisWorkflowRuntime | None = None

    try:
        redis = build_redis_client(settings.redis)
        await run_startup_dependency_checks(
            component="backend",
            checks=(
                StartupDependencyCheck(
                    name="postgresql",
                    target=_database_target(settings),
                    check=lambda: ping_database_engine(db_engine),
                ),
                StartupDependencyCheck(
                    name="redis",
                    target=_redis_target(settings),
                    check=lambda: ping_redis_client(redis),
                ),
            ),
            settings=settings,
            logger=logger,
        )

        redis_workflow = build_redis_workflow_runtime(redis)
        ai_provider = build_helpdesk_ai_provider(settings)
        ai_generation_profile = build_helpdesk_ai_generation_profile(settings)
        helpdesk_service_factory = build_helpdesk_service_factory(
            db_session_factory,
            super_admin_telegram_user_ids=frozenset(
                settings.authorization.super_admin_telegram_user_ids
            ),
            ai_provider=ai_provider,
            ai_generation_profile=ai_generation_profile,
            include_internal_notes_in_ticket_reports=(
                settings.exports.include_internal_notes_in_ticket_reports
            ),
            sla_deadline_scheduler=redis_workflow.sla_deadline_scheduler,
        )
        grpc_server = build_helpdesk_backend_server(
            helpdesk_service_factory=helpdesk_service_factory,
            bind_target=settings.backend_service.bind_target,
            auth_config=settings.backend_auth,
        )

        logger.info("Backend runtime dependencies initialized successfully.")
        return BackendRuntime(
            settings=settings,
            db_engine=db_engine,
            db_session_factory=db_session_factory,
            redis=redis,
            redis_workflow=redis_workflow,
            helpdesk_service_factory=helpdesk_service_factory,
            grpc_server=grpc_server,
        )
    except Exception:
        logger.exception("Backend runtime initialization failed.")
        await _close_runtime_resources(db_engine=db_engine, redis=redis)
        raise


async def close_runtime(runtime: BackendRuntime) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Closing backend runtime resources.")
    await _close_runtime_resources(db_engine=runtime.db_engine, redis=runtime.redis)
    logger.info("Backend runtime resources closed.")
