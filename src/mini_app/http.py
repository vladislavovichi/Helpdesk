from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, urlparse

from application.errors import ApplicationError
from domain.enums.roles import UserRole
from infrastructure.config.settings import MiniAppConfig
from mini_app.api import MiniAppGateway
from mini_app.auth import (
    TelegramMiniAppAuthError,
    TelegramMiniAppUser,
    validate_telegram_mini_app_init_data,
)
from mini_app.http_errors import application_error_status, safe_application_error_code
from mini_app.launch import ResolvedMiniAppLaunch, resolve_mini_app_launch
from mini_app.responses import serve_file, write_json
from mini_app.routes.admin import handle_admin_routes
from mini_app.routes.ai import is_ai_route
from mini_app.routes.dashboard import handle_dashboard_routes
from mini_app.routes.tickets import handle_ticket_routes

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MiniAppHttpServer:
    config: MiniAppConfig
    bot_token: str
    gateway: MiniAppGateway
    static_dir: Path
    server: ThreadingHTTPServer | None = None

    def build_server(self) -> ThreadingHTTPServer:
        handler_cls = build_handler_class(
            gateway=self.gateway,
            config=self.config,
            bot_token=self.bot_token,
            static_dir=self.static_dir,
        )
        self.server = ThreadingHTTPServer((self.config.listen_host, self.config.port), handler_cls)
        return self.server


def build_handler_class(
    *,
    gateway: MiniAppGateway,
    config: MiniAppConfig,
    bot_token: str,
    static_dir: Path,
) -> type[BaseHTTPRequestHandler]:
    gateway_ref = gateway
    config_ref = config
    bot_token_ref = bot_token
    static_dir_ref = static_dir

    class MiniAppRequestHandler(BaseHTTPRequestHandler):
        gateway = gateway_ref
        config = config_ref
        bot_token = bot_token_ref
        static_dir = static_dir_ref

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._dispatch("PUT")

        def log_message(self, format: str, *args: object) -> None:
            logger.info("mini-app http %s - %s", self.address_string(), format % args)

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            try:
                if self._handle_public_request(method=method, path=path, parsed=parsed):
                    return
                if not path.startswith("/api/"):
                    self._write_json(HTTPStatus.NOT_FOUND, {"error": "Маршрут Mini App не найден."})
                    return

                launch, user, session = self._load_session()
                self._handle_authenticated_request(
                    method=method,
                    path=path,
                    parsed=parsed,
                    launch=launch,
                    user=user,
                    session=session,
                )
            except TelegramMiniAppAuthError as exc:
                logger.warning(
                    (
                        "Mini App auth failed method=%s path=%s code=%s source=%s "
                        "client_source=%s telegram_webapp=%s telegram_user=%s "
                        "attempted_sources=%s diagnostics=%s"
                    ),
                    method,
                    path,
                    exc.code,
                    getattr(self, "_request_launch_source", "<unresolved>"),
                    getattr(self, "_request_client_source", "<unknown>"),
                    getattr(self, "_request_telegram_webapp", "<unknown>"),
                    getattr(self, "_request_telegram_user", "<unknown>"),
                    getattr(self, "_request_attempted_sources", "<none>"),
                    getattr(self, "_request_launch_diagnostics", "<none>"),
                )
                self._write_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "error": str(exc),
                        "code": "unauthorized" if is_ai_route(path) else exc.code,
                    },
                )
            except ApplicationError as exc:
                status = application_error_status(exc)
                self._write_json(
                    status,
                    {
                        "error": exc.public_message,
                        "code": safe_application_error_code(
                            exc,
                            is_ai_route=is_ai_route(path),
                        ),
                    },
                )
            except PermissionError as exc:
                self._write_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error": str(exc),
                        "code": "forbidden" if is_ai_route(path) else "access_denied",
                    },
                )
            except LookupError as exc:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": str(exc), "code": "not_found"},
                )
            except ValueError as exc:
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": str(exc),
                        "code": "validation_error" if is_ai_route(path) else "invalid_request",
                    },
                )
            except (ConnectionError, OSError, RuntimeError, TimeoutError) as exc:
                logger.warning(
                    "Mini App backend dependency failed method=%s path=%s error=%s",
                    method,
                    path,
                    exc,
                )
                self._write_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error": "Mini App временно недоступен. Попробуйте ещё раз чуть позже.",
                        "code": ("ai_unavailable" if is_ai_route(path) else "backend_unavailable"),
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("Mini App request failed method=%s path=%s", method, self.path)
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": "Mini App временно недоступен. Попробуйте ещё раз.",
                        "code": "internal_error",
                    },
                )

        def _handle_public_request(
            self,
            *,
            method: str,
            path: str,
            parsed: ParseResult,
        ) -> bool:
            del parsed
            if method == "GET" and path == "/healthz":
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "mini_app": {
                            "public_url": self.config.public_url or None,
                            "public_url_valid": self.config.public_url_is_valid,
                            "detail": self.config.public_url_status_detail,
                        },
                    },
                )
                return True
            if method == "GET" and (path == "/" or path == "/index.html"):
                serve_file(
                    self,
                    self.static_dir / "index.html",
                    static_dir=self.static_dir,
                    content_type="text/html; charset=utf-8",
                )
                return True
            if method == "GET" and path.startswith("/assets/"):
                asset_path = path.removeprefix("/assets/")
                serve_file(
                    self,
                    self.static_dir / "assets" / asset_path,
                    static_dir=self.static_dir,
                )
                return True
            return False

        def _handle_authenticated_request(
            self,
            *,
            method: str,
            path: str,
            parsed: ParseResult,
            launch: ResolvedMiniAppLaunch,
            user: TelegramMiniAppUser,
            session: dict[str, Any],
        ) -> None:
            if method == "GET" and path == "/api/session":
                self._write_json(
                    HTTPStatus.OK,
                    {
                        **session,
                        "launch": {
                            "source": launch.source,
                            "client_source": launch.client_source,
                        },
                    },
                )
                return

            if session["access"]["role"] == UserRole.USER.value:
                self._write_json(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error": (
                            "Рабочее место доступно только операторам и суперадминистраторам."
                        ),
                        "code": "forbidden" if is_ai_route(path) else "access_denied",
                    },
                )
                return

            if handle_dashboard_routes(
                self,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
            ):
                return
            if handle_admin_routes(
                self,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
                session=session,
            ):
                return
            if handle_ticket_routes(
                self,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
            ):
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Маршрут Mini App не найден."})

        def _load_session(
            self,
        ) -> tuple[ResolvedMiniAppLaunch, TelegramMiniAppUser, dict[str, Any]]:
            launch = self._resolve_launch()
            validated = validate_telegram_mini_app_init_data(
                init_data=launch.init_data,
                bot_token=self.bot_token,
                max_age_seconds=self.config.init_data_ttl_seconds,
            )
            session = asyncio.run(self.gateway.get_session(user=validated.user))
            return launch, validated.user, session

        def _resolve_launch(self) -> ResolvedMiniAppLaunch:
            launch = resolve_mini_app_launch(path=self.path, headers=dict(self.headers.items()))
            self._request_launch_source = launch.source
            self._request_client_source = launch.client_source or "<unknown>"
            self._request_telegram_webapp = _format_presence(launch.is_telegram_webapp)
            self._request_telegram_user = _format_presence(launch.has_telegram_user)
            self._request_attempted_sources = ",".join(launch.attempted_sources) or "<none>"
            self._request_launch_diagnostics = ",".join(launch.diagnostics) or "<none>"
            if launch.has_init_data:
                logger.debug(
                    (
                        "Mini App launch resolved source=%s client_source=%s path=%s "
                        "telegram_webapp=%s telegram_user=%s platform=%s version=%s "
                        "attempted_sources=%s diagnostics=%s"
                    ),
                    launch.source,
                    launch.client_source or "<unknown>",
                    urlparse(self.path).path,
                    _format_presence(launch.is_telegram_webapp),
                    _format_presence(launch.has_telegram_user),
                    launch.client_platform or "<unknown>",
                    launch.client_version or "<unknown>",
                    ",".join(launch.attempted_sources) or "<none>",
                    ",".join(launch.diagnostics) or "<none>",
                )
                return launch

            logger.warning(
                (
                    "Mini App launch missing source=%s client_source=%s path=%s "
                    "telegram_webapp=%s telegram_user=%s platform=%s version=%s "
                    "attempted_sources=%s diagnostics=%s"
                ),
                launch.source,
                launch.client_source or "<unknown>",
                urlparse(self.path).path,
                _format_presence(launch.is_telegram_webapp),
                _format_presence(launch.has_telegram_user),
                launch.client_platform or "<unknown>",
                launch.client_version or "<unknown>",
                ",".join(launch.attempted_sources) or "<none>",
                ",".join(launch.diagnostics) or "<none>",
            )
            return launch

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            write_json(self, status, payload)

    return MiniAppRequestHandler


def _format_presence(value: bool | None) -> str:
    if value is True:
        return "present"
    if value is False:
        return "missing"
    return "unknown"
