import re

import httpx
import pytest

from tests.conftest import AppFactory, running


async def test_health_reports_process_alive(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_when_database_and_redis_reachable(client: httpx.AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}


@pytest.mark.usefixtures("db_engine")
async def test_not_ready_when_redis_unreachable(make_app: AppFactory) -> None:
    app = make_app(redis_url="redis://127.0.0.1:6390/0")  # nothing listens here

    async with running(app) as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "redis": "unavailable"},
    }


async def test_every_response_gets_a_generated_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert re.fullmatch(r"req_[0-9a-f]{32}", response.headers["X-Request-ID"])


async def test_safe_caller_request_id_is_propagated(client: httpx.AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "trace-from-web-1234"})

    assert response.headers["X-Request-ID"] == "trace-from-web-1234"


@pytest.mark.parametrize(
    "unsafe_id", ["short", "has spaces in it", "x" * 200, "<script>alert</script>"]
)
async def test_unsafe_caller_request_id_is_replaced(
    client: httpx.AsyncClient, unsafe_id: str
) -> None:
    response = await client.get("/health", headers={"X-Request-ID": unsafe_id})

    assert response.headers["X-Request-ID"] != unsafe_id
    assert response.headers["X-Request-ID"].startswith("req_")


@pytest.mark.usefixtures("db_engine")
async def test_ready_without_redis_checks_only_configured_dependencies(
    make_app: AppFactory,
) -> None:
    # Redis is added only when a feature needs it; until then readiness must not require it.
    async with running(make_app(redis_url=None)) as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
