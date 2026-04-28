from __future__ import annotations

from http import HTTPStatus

from application.errors import (
    AIUnavailableError,
    ApplicationError,
    BackendUnavailableError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationAppError,
)


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
    if is_ai_route and isinstance(exc, (BackendUnavailableError, AIUnavailableError)):
        return "ai_unavailable"
    return exc.code
