from __future__ import annotations

import logging
from pathlib import Path

from backend.grpc.client import build_helpdesk_backend_client_factory
from infrastructure.config.settings import get_settings
from infrastructure.logging import configure_logging
from mini_app.api import MiniAppGateway
from mini_app.http import MiniAppHttpServer


def main() -> None:
    settings = get_settings()
    configure_logging(settings.logging, app=settings.app)

    logger = logging.getLogger(__name__)
    gateway = MiniAppGateway(
        backend_client_factory=build_helpdesk_backend_client_factory(
            settings.backend_service,
            auth_config=settings.backend_auth,
            resilience_config=settings.resilience,
        )
    )
    server = MiniAppHttpServer(
        config=settings.mini_app,
        bot_token=settings.bot.token,
        gateway=gateway,
        static_dir=Path(__file__).resolve().parent / "static",
    ).build_server()

    logger.info(
        "Starting Mini App HTTP gateway bind=%s:%s public_url=%s",
        settings.mini_app.listen_host,
        settings.mini_app.port,
        settings.mini_app.public_url or "<not-set>",
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Mini App shutdown requested.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
