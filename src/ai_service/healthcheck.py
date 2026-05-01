from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from ai_service.grpc.client import build_ai_service_client_factory
from application.contracts.ai import AIServiceStatus
from application.errors import ApplicationError
from infrastructure.config.settings import AIConfig, Settings, get_settings
from infrastructure.health import (
    EXPECTED_HEALTH_FAILURES,
    ProbeCheck,
    ProbeReport,
    ProbeStatus,
)
from infrastructure.logging import configure_logging

EXPECTED_AI_STATUS_FAILURES = (*EXPECTED_HEALTH_FAILURES, ApplicationError)


async def run() -> int:
    settings = get_settings()
    configure_logging(settings.logging, app=settings.app)

    status_error: Exception | None = None
    try:
        status = await _read_ai_service_status(settings)
    except EXPECTED_AI_STATUS_FAILURES as exc:
        status_error = exc
        status = AIServiceStatus(
            service="helpdesk-ai-service",
            status="unavailable",
            provider="local",
            model_id=settings.ai.effective_model_id,
            model_loaded=False,
        )
    report = ProbeReport(
        checks=(
            ProbeCheck(
                name="bootstrap",
                category="liveness",
                status=ProbeStatus.OK,
                detail="health probe запущен",
                affects_readiness=False,
            ),
            ProbeCheck(
                name="ai_service_auth",
                category="readiness",
                status=(
                    ProbeStatus.OK if settings.ai_service_auth.token.strip() else ProbeStatus.FAIL
                ),
                detail=(
                    "internal ai-service auth настроен"
                    if settings.ai_service_auth.token.strip()
                    else "AI_SERVICE_AUTH__TOKEN не задан"
                ),
            ),
            ProbeCheck(
                name="local_ai_model",
                category="operations",
                status=ProbeStatus.OK if status.model_loaded else ProbeStatus.FAIL,
                detail=build_ai_provider_visibility_detail(
                    settings.ai,
                    model_loaded=status.model_loaded,
                    model_id=status.model_id,
                    device=status.device,
                    dtype=status.dtype,
                    cache_dir=status.cache_dir,
                    max_concurrent_requests=status.max_concurrent_requests,
                ),
            ),
            await _run_probe(
                name="ai_service_grpc",
                category="service",
                detail=f"ai-service gRPC отвечает на {settings.ai_service.target}",
                probe=lambda: _status_is_ready(status, status_error),
            ),
        )
    )
    print(report.render())
    return report.exit_code


async def _read_ai_service_status(settings: Settings) -> AIServiceStatus:
    async with build_ai_service_client_factory(
        settings.ai_service,
        auth_config=settings.ai_service_auth,
        resilience_config=settings.resilience,
    )() as client:
        return await client.get_service_status()


async def _status_is_ready(status: AIServiceStatus, status_error: Exception | None) -> bool:
    if status_error is not None:
        raise status_error
    return (
        status.service == "helpdesk-ai-service" and status.status == "ready" and status.model_loaded
    )


async def _run_probe(
    *,
    name: str,
    category: str,
    detail: str,
    probe: Callable[[], Awaitable[bool]],
) -> ProbeCheck:
    try:
        ok = await probe()
    except EXPECTED_AI_STATUS_FAILURES as exc:
        return ProbeCheck(
            name=name,
            category=category,
            status=ProbeStatus.FAIL,
            detail=f"{exc.__class__.__name__}: {exc}",
        )

    if ok:
        return ProbeCheck(
            name=name,
            category=category,
            status=ProbeStatus.OK,
            detail=detail,
        )

    return ProbeCheck(
        name=name,
        category=category,
        status=ProbeStatus.FAIL,
        detail="проверка вернула отрицательный результат",
    )


def build_ai_provider_visibility_detail(
    config: AIConfig,
    *,
    model_loaded: bool,
    model_id: str | None,
    device: str | None = None,
    dtype: str | None = None,
    cache_dir: str | None = None,
    max_concurrent_requests: int | None = None,
) -> str:
    return (
        "provider=local "
        f"model_id={model_id or config.effective_model_id} "
        f"loaded={str(model_loaded).lower()} "
        f"device={device or config.local_device} "
        f"dtype={dtype or config.local_dtype} "
        f"cache_dir={cache_dir or config.local_cache_dir} "
        "max_concurrent_requests="
        f"{max_concurrent_requests or config.local_max_concurrent_requests}"
    )


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
