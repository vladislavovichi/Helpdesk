from __future__ import annotations

from typing import cast

import grpc
import pytest

from application.errors import (
    BackendUnavailableError,
    ConcurrencyConflictError,
    ForbiddenError,
    InternalApplicationError,
    NotFoundError,
    RateLimitError,
    ValidationAppError,
)
from backend.grpc.client import _translate_rpc_error
from backend.grpc.server_base import abort_for_exception


class _AbortCalled(Exception):
    pass


class _FakeGrpcContext:
    code: grpc.StatusCode | None = None
    details: str | None = None

    async def abort(self, code: grpc.StatusCode, details: str) -> None:
        self.code = code
        self.details = details
        raise _AbortCalled


class _FakeRpcError:
    def __init__(self, code: grpc.StatusCode, details: str) -> None:
        self._code = code
        self._details = details

    def code(self) -> grpc.StatusCode:
        return self._code

    def details(self) -> str:
        return self._details


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (NotFoundError("нет"), grpc.StatusCode.NOT_FOUND),
        (ForbiddenError("нельзя"), grpc.StatusCode.PERMISSION_DENIED),
        (ValidationAppError("плохо"), grpc.StatusCode.INVALID_ARGUMENT),
        (RateLimitError("часто"), grpc.StatusCode.RESOURCE_EXHAUSTED),
        (BackendUnavailableError("нет связи"), grpc.StatusCode.UNAVAILABLE),
        (ConcurrencyConflictError("конфликт"), grpc.StatusCode.ABORTED),
        (InternalApplicationError("сломалось"), grpc.StatusCode.INTERNAL),
    ],
)
async def test_application_errors_map_to_grpc_status(
    exc: Exception,
    expected_status: grpc.StatusCode,
) -> None:
    context = _FakeGrpcContext()

    with pytest.raises(_AbortCalled):
        await abort_for_exception(
            cast(grpc.aio.ServicerContext, context),
            exc,
            method="test.Method",
        )

    assert context.code is expected_status
    assert context.details == str(exc)


@pytest.mark.parametrize(
    ("status", "expected_type"),
    [
        (grpc.StatusCode.NOT_FOUND, NotFoundError),
        (grpc.StatusCode.PERMISSION_DENIED, ForbiddenError),
        (grpc.StatusCode.INVALID_ARGUMENT, ValidationAppError),
        (grpc.StatusCode.RESOURCE_EXHAUSTED, RateLimitError),
        (grpc.StatusCode.UNAVAILABLE, BackendUnavailableError),
        (grpc.StatusCode.ABORTED, ConcurrencyConflictError),
        (grpc.StatusCode.INTERNAL, InternalApplicationError),
    ],
)
def test_grpc_client_errors_translate_to_application_errors(
    status: grpc.StatusCode,
    expected_type: type[Exception],
) -> None:
    exc = cast(grpc.aio.AioRpcError, _FakeRpcError(status, "детали"))

    translated = _translate_rpc_error(exc)

    assert isinstance(translated, expected_type)
    assert str(translated) == "детали"
