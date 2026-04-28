from __future__ import annotations

from http import HTTPStatus

from application.errors import (
    AIUnavailableError,
    BackendUnavailableError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationAppError,
)
from mini_app.http_errors import application_error_status, safe_application_error_code


def test_http_error_mapping_is_explicit_for_application_errors() -> None:
    assert application_error_status(NotFoundError()) is HTTPStatus.NOT_FOUND
    assert application_error_status(ForbiddenError()) is HTTPStatus.FORBIDDEN
    assert application_error_status(ValidationAppError()) is HTTPStatus.BAD_REQUEST
    assert application_error_status(RateLimitError()) is HTTPStatus.TOO_MANY_REQUESTS
    assert application_error_status(BackendUnavailableError()) is HTTPStatus.SERVICE_UNAVAILABLE
    assert application_error_status(AIUnavailableError()) is HTTPStatus.SERVICE_UNAVAILABLE


def test_ai_routes_hide_backend_error_code_behind_ai_unavailable() -> None:
    assert (
        safe_application_error_code(BackendUnavailableError(), is_ai_route=True)
        == "ai_unavailable"
    )
    assert (
        safe_application_error_code(AIUnavailableError(), is_ai_route=True)
        == "ai_unavailable"
    )
    assert (
        safe_application_error_code(BackendUnavailableError(), is_ai_route=False)
        == "backend_unavailable"
    )


def test_forbidden_error_preserves_existing_mini_app_codes() -> None:
    assert safe_application_error_code(ForbiddenError(), is_ai_route=False) == "access_denied"
    assert safe_application_error_code(ForbiddenError(), is_ai_route=True) == "forbidden"
