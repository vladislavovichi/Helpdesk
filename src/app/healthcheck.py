from __future__ import annotations

import asyncio

from app.bootstrap import build_runtime, close_runtime
from infrastructure.config.settings import get_settings
from infrastructure.logging import configure_logging


def _format_healthcheck_output(lines: list[str]) -> str:
    return "\n".join(lines)


async def run() -> int:
    settings = get_settings()
    configure_logging(settings.logging, app=settings.app)

    runtime = await build_runtime(settings)
    try:
        report = await runtime.diagnostics_service.collect_report()
    finally:
        await close_runtime(runtime)

    lines = [
        "OK" if report.is_healthy else "DEGRADED",
        *[
            f"[{'OK' if check.ok else 'FAIL'}] {check.name}: {check.detail}"
            for check in report.checks
        ],
    ]
    print(_format_healthcheck_output(lines))
    return 0 if report.is_healthy else 1


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
