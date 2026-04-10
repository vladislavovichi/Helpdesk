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
        print("[OK] postgresql: подключение установлено")
        print("[OK] redis: подключение установлено")
        print(f"[OK] backend_grpc: готов к запуску на {settings.backend_service.bind_target}")
        return 0
    finally:
        await close_runtime(runtime)


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
