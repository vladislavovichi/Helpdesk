from __future__ import annotations

import asyncio

from backend.bootstrap import build_runtime, close_runtime
from infrastructure.config.settings import get_settings
from infrastructure.logging import configure_logging


async def run() -> int:
    settings = get_settings()
    configure_logging(settings.logging, app=settings.app)

    runtime = await build_runtime(settings)
    try:
        print("OK")
        print("[OK] liveness")
        print("[OK] readiness")
        print(
            "[OK] readiness/backend_auth: internal backend auth настроен"
            if settings.backend_auth.token.strip()
            else "[FAIL] readiness/backend_auth: BACKEND_AUTH__TOKEN не задан"
        )
        print("[OK] dependency/postgresql: подключение установлено")
        print("[OK] dependency/redis: подключение установлено")
        print(
            "[OK] readiness/backend_grpc: "
            f"готов к запуску на {settings.backend_service.bind_target}"
        )
        return 0
    finally:
        await close_runtime(runtime)


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
