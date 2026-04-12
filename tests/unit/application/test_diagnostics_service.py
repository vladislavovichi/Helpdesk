from __future__ import annotations

from application.services.diagnostics import DiagnosticsService


async def test_collect_report_returns_healthy_status_for_ready_runtime() -> None:
    service = DiagnosticsService(
        database_check=_ok_check,
        redis_check=_ok_check,
        backend_check=_ok_check,
        backend_auth_configured=True,
        dry_run=False,
        bot_configured=True,
        bot_initialized=True,
        dispatcher_initialized=True,
        fsm_storage_initialized=True,
        redis_workflow_initialized=True,
    )

    report = await service.collect_report()

    assert report.is_healthy is True
    assert [(check.category, check.name, check.ok) for check in report.checks] == [
        ("liveness", "bootstrap", True),
        ("readiness", "backend_auth", True),
        ("dependency", "postgresql", True),
        ("dependency", "redis", True),
        ("dependency", "backend_grpc", True),
        ("readiness", "bot_runtime", True),
    ]


async def test_collect_report_marks_failed_dependency_and_bot_runtime() -> None:
    service = DiagnosticsService(
        database_check=_ok_check,
        redis_check=_failing_check,
        backend_check=_ok_check,
        backend_auth_configured=False,
        dry_run=False,
        bot_configured=False,
        bot_initialized=False,
        dispatcher_initialized=False,
        fsm_storage_initialized=True,
        redis_workflow_initialized=True,
    )

    report = await service.collect_report()

    assert report.is_healthy is False
    checks_by_name = {check.name: check for check in report.checks}
    assert checks_by_name["backend_auth"].ok is False
    assert checks_by_name["redis"].ok is False
    assert "boom" in checks_by_name["redis"].detail
    assert checks_by_name["bot_runtime"].ok is False
    assert checks_by_name["bot_runtime"].detail == "BOT__TOKEN не задан"


async def test_collect_report_accepts_dry_run_without_bot_initialization() -> None:
    service = DiagnosticsService(
        database_check=_ok_check,
        redis_check=_ok_check,
        backend_check=_ok_check,
        backend_auth_configured=True,
        dry_run=True,
        bot_configured=False,
        bot_initialized=False,
        dispatcher_initialized=False,
        fsm_storage_initialized=True,
        redis_workflow_initialized=True,
    )

    report = await service.collect_report()

    assert report.is_healthy is True
    checks_by_name = {check.name: check for check in report.checks}
    assert checks_by_name["bot_runtime"].ok is True
    assert "APP__DRY_RUN=true" in checks_by_name["bot_runtime"].detail


async def _ok_check() -> bool:
    return True


async def _failing_check() -> bool:
    raise RuntimeError("boom")
