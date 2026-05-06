from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from urllib.parse import ParseResult, urlparse

from application.errors import ApplicationError
from infrastructure.config.settings import MiniAppConfig
from mini_app.api import MiniAppGateway
from mini_app.auth import (
    TelegramMiniAppAuthError,
    TelegramMiniAppUser,
    validate_telegram_mini_app_init_data,
)
from mini_app.http_errors import mini_app_error_response
from mini_app.launch import ResolvedMiniAppLaunch, resolve_mini_app_launch
from mini_app.responses import serve_file, write_json
from mini_app.routes.admin import handle_admin_routes
from mini_app.routes.ai import is_ai_route
from mini_app.routes.analytics import handle_analytics_routes
from mini_app.routes.dashboard import handle_dashboard_routes
from mini_app.routes.queue import handle_queue_routes
from mini_app.routes.session import handle_session_route, require_operator_session
from mini_app.routes.tickets import handle_ticket_routes

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class MiniAppHttpDependencies:
    gateway: MiniAppGateway
    config: MiniAppConfig
    bot_token: str
    static_dir: Path


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
    deps = MiniAppHttpDependencies(
        gateway=gateway,
        config=config,
        bot_token=bot_token,
        static_dir=static_dir,
    )

    class MiniAppRequestHandler(BaseHTTPRequestHandler):
        dependencies = deps
        gateway = deps.gateway
        config = deps.config
        bot_token = deps.bot_token
        static_dir = deps.static_dir

        def do_GET(self) -> None:  # noqa: N802
            dispatch_mini_app_request(self, "GET")

        def do_POST(self) -> None:  # noqa: N802
            dispatch_mini_app_request(self, "POST")

        def do_PUT(self) -> None:  # noqa: N802
            dispatch_mini_app_request(self, "PUT")

        def log_message(self, format: str, *args: object) -> None:
            logger.info("mini-app http %s - %s", self.address_string(), format % args)

        def _dispatch(self, method: str) -> None:
            if not hasattr(self, "requestline"):
                self.requestline = f"{method} {self.path} HTTP/1.1"
            if not hasattr(self, "request_version"):
                self.request_version = "HTTP/1.1"
            if not hasattr(self, "client_address"):
                self.client_address = ("127.0.0.1", 0)
            if not hasattr(self, "wfile"):
                self.wfile = BytesIO()
            dispatch_mini_app_request(self, method)

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
            MiniAppRouteDispatcher(self).handle_authenticated_request(
                method=method,
                path=path,
                parsed=parsed,
                launch=launch,
                user=user,
                session=session,
            )

        def _load_session(
            self,
        ) -> tuple[ResolvedMiniAppLaunch, TelegramMiniAppUser, dict[str, Any]]:
            return MiniAppSessionLoader(self).load()

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            MiniAppJsonResponder(self).write(status, payload)

    return MiniAppRequestHandler


def dispatch_mini_app_request(handler: BaseHTTPRequestHandler, method: str) -> None:
    parsed = urlparse(handler.path)
    path = parsed.path
    try:
        dispatcher = MiniAppRouteDispatcher(handler)
        if dispatcher.handle_public_request(method=method, path=path, parsed=parsed):
            return
        if not path.startswith("/api/"):
            MiniAppJsonResponder(handler).not_found()
            return

        handler_adapter: Any = handler
        launch, user, session = handler_adapter._load_session()
        dispatcher.handle_authenticated_request(
            method=method,
            path=path,
            parsed=parsed,
            launch=launch,
            user=user,
            session=session,
        )
    except Exception as exc:  # noqa: BLE001
        MiniAppErrorResponder(handler).write_exception(method=method, path=path, exc=exc)


@dataclass(slots=True)
class MiniAppJsonResponder:
    handler: BaseHTTPRequestHandler

    def write(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        writer = getattr(self.handler, "_write_json", None)
        if writer is not None and not getattr(
            self.handler,
            "_mini_app_json_responder_active",
            False,
        ):
            active_handler: Any = self.handler
            active_handler._mini_app_json_responder_active = True
            try:
                writer(status, payload)
            finally:
                active_handler._mini_app_json_responder_active = False
            return
        write_json(self.handler, status, payload)

    def not_found(self) -> None:
        self.write(HTTPStatus.NOT_FOUND, {"error": "Маршрут Mini App не найден."})


@dataclass(slots=True)
class MiniAppRouteDispatcher:
    handler: BaseHTTPRequestHandler

    def handle_public_request(
        self,
        *,
        method: str,
        path: str,
        parsed: ParseResult,
    ) -> bool:
        del parsed
        deps = self._deps
        if method == "GET" and path == "/healthz":
            MiniAppJsonResponder(self.handler).write(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "mini_app": {
                        "public_url": deps.config.public_url or None,
                        "public_url_valid": deps.config.public_url_is_valid,
                        "detail": deps.config.public_url_status_detail,
                    },
                },
            )
            return True
        if method == "GET" and (path == "/" or path == "/index.html"):
            serve_file(
                self.handler,
                deps.static_dir / "index.html",
                static_dir=deps.static_dir,
                content_type="text/html; charset=utf-8",
            )
            return True
        if method == "GET" and path.startswith("/assets/"):
            asset_path = path.removeprefix("/assets/")
            serve_file(
                self.handler,
                deps.static_dir / "assets" / asset_path,
                static_dir=deps.static_dir,
            )
            return True
        return False

    def handle_authenticated_request(
        self,
        *,
        method: str,
        path: str,
        parsed: ParseResult,
        launch: ResolvedMiniAppLaunch,
        user: TelegramMiniAppUser,
        session: dict[str, Any],
    ) -> None:
        if handle_session_route(
            self.handler,
            method=method,
            path=path,
            launch=launch,
            session=session,
        ):
            return
        if not require_operator_session(self.handler, path=path, session=session):
            return
        if self._handle_endpoint_routes(
            method=method,
            path=path,
            parsed=parsed,
            user=user,
            session=session,
        ):
            return
        MiniAppJsonResponder(self.handler).not_found()

    def _handle_endpoint_routes(
        self,
        *,
        method: str,
        path: str,
        parsed: ParseResult,
        user: TelegramMiniAppUser,
        session: dict[str, Any],
    ) -> bool:
        return (
            handle_dashboard_routes(self.handler, method=method, path=path, user=user)
            or handle_queue_routes(self.handler, method=method, path=path, user=user)
            or handle_admin_routes(
                self.handler,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
                session=session,
            )
            or handle_ticket_routes(
                self.handler,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
            )
            or handle_analytics_routes(
                self.handler,
                method=method,
                path=path,
                parsed=parsed,
                user=user,
            )
        )

    @property
    def _deps(self) -> MiniAppHttpDependencies:
        return cast(MiniAppHttpDependencies, self.handler.dependencies)  # type: ignore[attr-defined]


@dataclass(slots=True)
class MiniAppSessionLoader:
    handler: BaseHTTPRequestHandler

    def load(self) -> tuple[ResolvedMiniAppLaunch, TelegramMiniAppUser, dict[str, Any]]:
        deps = self._deps
        launch = self._resolve_launch()
        validated = validate_telegram_mini_app_init_data(
            init_data=launch.init_data,
            bot_token=deps.bot_token,
            max_age_seconds=deps.config.init_data_ttl_seconds,
        )
        session = asyncio.run(deps.gateway.get_session(user=validated.user))
        return launch, validated.user, session

    def _resolve_launch(self) -> ResolvedMiniAppLaunch:
        launch = resolve_mini_app_launch(
            path=self.handler.path,
            headers=dict(self.handler.headers.items()),
        )
        self._store_launch_diagnostics(launch)
        _log_launch_resolution(path=self.handler.path, launch=launch)
        return launch

    def _store_launch_diagnostics(self, launch: ResolvedMiniAppLaunch) -> None:
        handler: Any = self.handler
        handler._request_launch_source = launch.source
        handler._request_client_source = launch.client_source or "<unknown>"
        handler._request_telegram_webapp = _format_presence(launch.is_telegram_webapp)
        handler._request_telegram_user = _format_presence(launch.has_telegram_user)
        handler._request_attempted_sources = ",".join(launch.attempted_sources) or "<none>"
        handler._request_launch_diagnostics = ",".join(launch.diagnostics) or "<none>"

    @property
    def _deps(self) -> MiniAppHttpDependencies:
        return cast(MiniAppHttpDependencies, self.handler.dependencies)  # type: ignore[attr-defined]


@dataclass(slots=True)
class MiniAppErrorResponder:
    handler: BaseHTTPRequestHandler

    def write_exception(self, *, method: str, path: str, exc: Exception) -> None:
        responder = MiniAppJsonResponder(self.handler)
        if isinstance(exc, TelegramMiniAppAuthError):
            self._log_auth_failure(method=method, path=path, exc=exc)
            responder.write(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": str(exc),
                    "code": "unauthorized" if is_ai_route(path) else exc.code,
                },
            )
            return
        if isinstance(exc, ApplicationError):
            status, payload = mini_app_error_response(exc, is_ai_route=is_ai_route(path))
            responder.write(status, payload)
            return
        if isinstance(exc, ConnectionError | OSError | RuntimeError | TimeoutError):
            logger.warning(
                "Mini App backend dependency failed method=%s path=%s error=%s",
                method,
                path,
                exc,
            )
        elif not isinstance(exc, PermissionError | LookupError | ValueError):
            logger.exception("Mini App request failed method=%s path=%s", method, self.handler.path)
        status, payload = mini_app_error_response(exc, is_ai_route=is_ai_route(path))
        responder.write(status, payload)

    def _log_auth_failure(
        self,
        *,
        method: str,
        path: str,
        exc: TelegramMiniAppAuthError,
    ) -> None:
        logger.warning(
            (
                "Mini App auth failed method=%s path=%s code=%s source=%s "
                "client_source=%s telegram_webapp=%s telegram_user=%s "
                "attempted_sources=%s diagnostics=%s"
            ),
            method,
            path,
            exc.code,
            getattr(self.handler, "_request_launch_source", "<unresolved>"),
            getattr(self.handler, "_request_client_source", "<unknown>"),
            getattr(self.handler, "_request_telegram_webapp", "<unknown>"),
            getattr(self.handler, "_request_telegram_user", "<unknown>"),
            getattr(self.handler, "_request_attempted_sources", "<none>"),
            getattr(self.handler, "_request_launch_diagnostics", "<none>"),
        )


def _log_launch_resolution(*, path: str, launch: ResolvedMiniAppLaunch) -> None:
    log = logger.debug if launch.has_init_data else logger.warning
    state = "resolved" if launch.has_init_data else "missing"
    log(
        (
            "Mini App launch %s source=%s client_source=%s path=%s "
            "telegram_webapp=%s telegram_user=%s platform=%s version=%s "
            "attempted_sources=%s diagnostics=%s"
        ),
        state,
        launch.source,
        launch.client_source or "<unknown>",
        urlparse(path).path,
        _format_presence(launch.is_telegram_webapp),
        _format_presence(launch.has_telegram_user),
        launch.client_platform or "<unknown>",
        launch.client_version or "<unknown>",
        ",".join(launch.attempted_sources) or "<none>",
        ",".join(launch.diagnostics) or "<none>",
    )


def _format_presence(value: bool | None) -> str:
    if value is True:
        return "present"
    if value is False:
        return "missing"
    return "unknown"
