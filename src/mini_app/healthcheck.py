from __future__ import annotations

import http.client

from infrastructure.config.settings import get_settings
from infrastructure.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.logging, app=settings.app)
    host = settings.mini_app.listen_host
    if host == "0.0.0.0":
        host = "127.0.0.1"

    connection = http.client.HTTPConnection(
        host=host,
        port=settings.mini_app.port,
        timeout=5,
    )
    try:
        connection.request("GET", "/healthz")
        response = connection.getresponse()
        raise SystemExit(0 if response.status == 200 else 1)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
