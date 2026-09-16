"""Per-request context: request IDs, access logging and the last-resort error boundary."""

import re
import time
import uuid

import sentry_sdk
import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import INTERNAL_ERROR_MESSAGE, ErrorCode, error_response

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

logger = structlog.get_logger("app.request")


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            # Accept a caller-supplied ID only if it is safe to log and echo back.
            return candidate if _VALID_REQUEST_ID.fullmatch(candidate) else None
    return None


class RequestContextMiddleware:
    """Assigns every HTTP request an ID and guarantees a consistent error body.

    Implemented as pure ASGI middleware so it wraps streaming responses and unhandled
    exceptions without buffering request bodies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            logger.exception("unhandled_exception")
            sentry_sdk.capture_exception(exc)
            if response_started:
                raise
            response = error_response(
                500, ErrorCode.INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE, request_id
            )
            await response(scope, receive, send_with_request_id)
        finally:
            # Log the path only — query strings can carry user data.
            logger.info(
                "request_completed",
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            structlog.contextvars.unbind_contextvars("request_id")
