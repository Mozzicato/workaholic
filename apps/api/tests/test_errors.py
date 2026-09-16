"""The API error contract: consistent shape, stable codes, no leaked internals."""

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from fastapi import FastAPI
from pydantic import BaseModel

from tests.conftest import ALLOWED_ORIGIN, running


class _Payload(BaseModel):
    title: str
    years: int


@pytest_asyncio.fixture
async def client_with_failing_routes(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    @app.get("/test/crash")
    async def crash() -> None:
        raise RuntimeError("database password is hunter2")

    @app.post("/test/validate")
    async def validate(payload: _Payload) -> _Payload:
        return payload

    async with running(app) as client:
        yield client


def assert_error(response: httpx.Response, status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    error: dict[str, object] = body["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]
    return error


async def test_unknown_route_uses_error_format(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert_error(response, 404, "NOT_FOUND")


async def test_wrong_method_uses_error_format(client: httpx.AsyncClient) -> None:
    response = await client.post("/health")

    assert_error(response, 405, "METHOD_NOT_ALLOWED")


async def test_unhandled_exception_hides_internal_details(
    client_with_failing_routes: httpx.AsyncClient,
) -> None:
    response = await client_with_failing_routes.get("/test/crash")

    assert_error(response, 500, "INTERNAL_ERROR")
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text


async def test_validation_error_lists_fields_without_echoing_input(
    client_with_failing_routes: httpx.AsyncClient,
) -> None:
    secret_text = "Confidential: led the acquisition of Initech"
    response = await client_with_failing_routes.post(
        "/test/validate", json={"title": secret_text, "years": "not-a-number"}
    )

    error = assert_error(response, 422, "VALIDATION_ERROR")
    details = error["details"]
    assert isinstance(details, list)
    assert [detail["field"] for detail in details] == ["body.years"]
    assert secret_text not in response.text
    assert "not-a-number" not in response.text


async def test_cors_allows_configured_origin(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/api/v1/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


async def test_cors_rejects_unknown_origin(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/api/v1/me",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers


async def test_error_responses_carry_cors_headers(client: httpx.AsyncClient) -> None:
    # Without this the browser hides the error body and the UI can't explain what happened.
    response = await client.get("/api/v1/me", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
