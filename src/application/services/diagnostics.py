from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

AsyncDependencyCheck = Callable[[], Awaitable[bool]]


@dataclass(slots=True, frozen=True)
class DiagnosticsCheck:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True, frozen=True)
class DiagnosticsReport:
    checks: tuple[DiagnosticsCheck, ...]

    @property
    def is_healthy(self) -> bool:
        return all(check.ok for check in self.checks)


@dataclass(slots=True)
class DiagnosticsService:
    database_check: AsyncDependencyCheck
    redis_check: AsyncDependencyCheck
    backend_check: AsyncDependencyCheck
    dry_run: bool
    bot_configured: bool
    bot_initialized: bool
    dispatcher_initialized: bool
    fsm_storage_initialized: bool
    redis_workflow_initialized: bool

    async def collect_report(self) -> DiagnosticsReport:
        checks = [
            DiagnosticsCheck(
                name="bootstrap",
                ok=True,
                detail="runtime инициализирован",
            ),
            await self._run_check(
                name="postgresql",
                check=self.database_check,
                success_detail="подключение установлено",
            ),
            await self._run_check(
                name="redis",
                check=self.redis_check,
                success_detail="подключение установлено",
            ),
            await self._run_check(
                name="backend_grpc",
                check=self.backend_check,
                success_detail="внутренний gRPC backend доступен",
            ),
            DiagnosticsCheck(
                name="bot_runtime",
                ok=self._is_bot_runtime_ready(),
                detail=self._build_bot_runtime_detail(),
            ),
        ]
        return DiagnosticsReport(checks=tuple(checks))

    async def _run_check(
        self,
        *,
        name: str,
        check: AsyncDependencyCheck,
        success_detail: str,
    ) -> DiagnosticsCheck:
        try:
            is_ready = await check()
        except Exception as exc:
            return DiagnosticsCheck(
                name=name,
                ok=False,
                detail=f"{exc.__class__.__name__}: {exc}",
            )

        if is_ready:
            return DiagnosticsCheck(name=name, ok=True, detail=success_detail)

        return DiagnosticsCheck(
            name=name,
            ok=False,
            detail="проверка вернула отрицательный результат",
        )

    def _is_bot_runtime_ready(self) -> bool:
        if self.dry_run:
            return self.fsm_storage_initialized and self.redis_workflow_initialized

        return (
            self.bot_configured
            and self.bot_initialized
            and self.dispatcher_initialized
            and self.fsm_storage_initialized
            and self.redis_workflow_initialized
        )

    def _build_bot_runtime_detail(self) -> str:
        if self.dry_run:
            if self.fsm_storage_initialized and self.redis_workflow_initialized:
                return "polling отключен из-за APP__DRY_RUN=true"
            return "часть Telegram runtime не инициализирована в dry-run режиме"

        if not self.bot_configured:
            return "BOT__TOKEN не задан"
        if not self.bot_initialized:
            return "экземпляр бота не инициализирован"
        if not self.dispatcher_initialized:
            return "dispatcher не инициализирован"
        if not self.fsm_storage_initialized:
            return "FSM storage не инициализирован"
        if not self.redis_workflow_initialized:
            return "Redis workflow runtime не инициализирован"
        return "Telegram runtime готов"
