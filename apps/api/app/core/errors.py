"""Consistent API error format.

Every error response has the shape:

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

Codes are stable identifiers the frontend can branch on. Messages are safe to show to users.
Internal exception details are logged, never returned.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_PROVIDER_UNAVAILABLE = "AUTH_PROVIDER_UNAVAILABLE"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """An expected failure with a user-safe message."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class UnauthenticatedError(AppError):
    def __init__(self, message: str = "Please sign in to continue.") -> None:
        super().__init__(ErrorCode.UNAUTHENTICATED, message, 401)


class SessionExpiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.SESSION_EXPIRED, "Your session has expired. Please sign in again.", 401
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "We couldn't find that.") -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, 404)


class AuthProviderUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AUTH_PROVIDER_UNAVAILABLE,
            "We couldn't verify your sign-in right now. Please try again in a moment.",
            503,
        )


_STATUS_TO_CODE: dict[int, tuple[ErrorCode, str]] = {
    401: (ErrorCode.UNAUTHENTICATED, "Please sign in to continue."),
    403: (ErrorCode.FORBIDDEN, "You don't have access to this."),
    404: (ErrorCode.NOT_FOUND, "We couldn't find that."),
    405: (ErrorCode.METHOD_NOT_ALLOWED, "That action isn't supported here."),
    409: (ErrorCode.CONFLICT, "That conflicts with the current state. Refresh and try again."),
    429: (ErrorCode.RATE_LIMITED, "You're doing that too often. Please wait and try again."),
    503: (ErrorCode.SERVICE_UNAVAILABLE, "This service is temporarily unavailable."),
}

INTERNAL_ERROR_MESSAGE = (
    "Something went wrong on our side. Your information is safe. Please try again."
)


def request_id_of(request: Request) -> str | None:
    request_id: str | None = request.scope.get("state", {}).get("request_id")
    return request_id


def error_payload(
    code: ErrorCode,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message, "request_id": request_id}
    if details:
        error["details"] = details
    return {"error": error}


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id, details),
        headers=headers,
    )


def _code_for_status(status_code: int) -> tuple[ErrorCode, str]:
    if status_code in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[status_code]
    if status_code >= 500:
        return ErrorCode.INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE
    return ErrorCode.VALIDATION_ERROR, "That request isn't valid."


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return error_response(
        exc.status_code, exc.code, exc.message, request_id_of(request), exc.details, headers
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    code, message = _code_for_status(exc.status_code)
    return error_response(
        exc.status_code, code, message, request_id_of(request), headers=exc.headers
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    # Report where and why validation failed, but never echo submitted values back:
    # they may contain resume or job-description content.
    details = [
        {"field": ".".join(str(part) for part in error.get("loc", ())), "issue": error.get("msg")}
        for error in exc.errors()
    ]
    return error_response(
        422,
        ErrorCode.VALIDATION_ERROR,
        "Some of the information provided isn't valid.",
        request_id_of(request),
        details,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
