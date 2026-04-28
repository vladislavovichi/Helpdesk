from __future__ import annotations

from http import HTTPStatus
from typing import Any

from application.errors import (
    AIUnavailableError,
    ApplicationError,
    BackendUnavailableError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationAppError,
)

MINI_APP_UNAVAILABLE_MESSAGE = "Mini App временно недоступен. Попробуйте ещё раз чуть позже."


def application_error_status(exc: ApplicationError) -> HTTPStatus:
    if isinstance(exc, NotFoundError):
        return HTTPStatus.NOT_FOUND
    if isinstance(exc, ForbiddenError):
        return HTTPStatus.FORBIDDEN
    if isinstance(exc, ValidationAppError):
        return HTTPStatus.BAD_REQUEST
    if isinstance(exc, RateLimitError):
        return HTTPStatus.TOO_MANY_REQUESTS
    if isinstance(exc, (BackendUnavailableError, AIUnavailableError)):
        return HTTPStatus.SERVICE_UNAVAILABLE
    return HTTPStatus.INTERNAL_SERVER_ERROR


def safe_application_error_code(
    exc: ApplicationError,
    *,
    is_ai_route: bool,
) -> str:
    if isinstance(exc, ForbiddenError):
        return "forbidden" if is_ai_route else "access_denied"
    if is_ai_route and isinstance(exc, (BackendUnavailableError, AIUnavailableError)):
        return "ai_unavailable"
    return exc.code


def mini_app_error_response(
    exc: Exception,
    *,
    is_ai_route: bool,
) -> tuple[HTTPStatus, dict[str, Any]]:
    if isinstance(exc, ApplicationError):
        return application_error_status(exc), {
            "error": exc.public_message,
            "code": safe_application_error_code(exc, is_ai_route=is_ai_route),
        }
    if isinstance(exc, PermissionError):
        return HTTPStatus.FORBIDDEN, {
            "error": str(exc),
            "code": "forbidden" if is_ai_route else "access_denied",
        }
    if isinstance(exc, LookupError):
        return HTTPStatus.NOT_FOUND, {"error": str(exc), "code": "not_found"}
    if isinstance(exc, ValueError):
        return HTTPStatus.BAD_REQUEST, {
            "error": str(exc),
            "code": "validation_error" if is_ai_route else "invalid_request",
        }
    if isinstance(exc, ConnectionError | OSError | RuntimeError | TimeoutError):
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "error": MINI_APP_UNAVAILABLE_MESSAGE,
            "code": "ai_unavailable" if is_ai_route else "backend_unavailable",
        }
    return HTTPStatus.INTERNAL_SERVER_ERROR, {
        "error": "Mini App временно недоступен. Попробуйте ещё раз.",
        "code": "internal_error",
    }
