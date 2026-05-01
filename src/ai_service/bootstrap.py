from __future__ import annotations

import logging

from ai_service.grpc.server import build_ai_service_grpc_server
from ai_service.service import AIApplicationService
from application.ai.contracts import AIProvider, AIProviderError
from infrastructure.ai.provider import build_ai_provider
from infrastructure.config.settings import Settings
from infrastructure.startup_checks import validate_ai_service_startup_settings

from .runtime import AIServiceRuntime


def _build_service(settings: Settings, provider: AIProvider) -> AIApplicationService:
    return AIApplicationService(provider=provider, config=settings.ai)


async def build_runtime(settings: Settings) -> AIServiceRuntime:
    logger = logging.getLogger(__name__)
    validate_ai_service_startup_settings(settings)
    logger.info(
        "Initializing ai-service runtime bind=%s provider=local model=%s",
        settings.ai_service.bind_target,
        settings.ai.effective_model_id,
    )
    provider = build_ai_provider(settings.ai)
    load = getattr(provider, "load", None)
    if load is not None:
        try:
            await load()
        except AIProviderError as exc:
            logger.error(
                "Local AI model startup failed failure_reason=%s model=%s",
                exc.failure_category,
                provider.model_id,
            )
            raise
    logger.info("AI provider is ready provider=local model=%s", provider.model_id)
    service = _build_service(settings, provider)
    grpc_server = build_ai_service_grpc_server(
        service=service,
        bind_target=settings.ai_service.bind_target,
        auth_config=settings.ai_service_auth,
    )
    logger.info("AI-service runtime initialized successfully.")
    return AIServiceRuntime(
        settings=settings,
        service=service,
        grpc_server=grpc_server,
    )


async def close_runtime(runtime: AIServiceRuntime) -> None:
    logging.getLogger(__name__).info(
        "AI-service runtime closed bind=%s",
        runtime.settings.ai_service.bind_target,
    )
