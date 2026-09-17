"""Test fixtures.

Tests run against real PostgreSQL and Redis (docker-compose locally, service containers
in CI). Only the identity provider's key endpoint is simulated: tokens are signed with a
locally generated key pair and verified by the production verification code.
"""

import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
import pytest_asyncio
from alembic.config import Config
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command
from app.core.config import _SETTINGS_CONFIG, Settings
from app.factory import create_app
from app.services.auth.supabase import SupabaseAuthProvider

API_DIR = Path(__file__).resolve().parents[1]
SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
ALLOWED_ORIGIN = "http://localhost:3000"


class SuiteEnvironment(BaseSettings):
    model_config = _SETTINGS_CONFIG

    test_database_url: str
    redis_url: str = "redis://127.0.0.1:6379/0"


@pytest.fixture(scope="session")
def test_env() -> SuiteEnvironment:
    return SuiteEnvironment()


def build_settings(test_env: SuiteEnvironment, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "log_level": "WARNING",
        "cors_origins": [ALLOWED_ORIGIN],
        "database_url": test_env.test_database_url,
        "redis_url": test_env.redis_url,
        "supabase_url": SUPABASE_URL,
        "supabase_secret_key": SecretStr("sb_secret_test"),
        "sentry_dsn": None,
    }
    values.update(overrides)
    # Ignore the developer's .env (AI keys, providers) so tests are reproducible.
    return Settings(_env_file=None, **values)


# ── Database ────────────────────────────────────────────────────────────────


def _upgrade_to_head(connection: Connection) -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest_asyncio.fixture(scope="session")
async def db_engine(test_env: SuiteEnvironment) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_env.test_database_url)
    async with engine.begin() as connection:
        # Rebuild from migrations every run: this also tests the migrations themselves.
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(_upgrade_to_head)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_database(db_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with db_engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE users CASCADE"))


# ── Identity provider simulation ────────────────────────────────────────────


@dataclass
class SigningKey:
    kid: str
    private_key: ec.EllipticCurvePrivateKey = field(
        default_factory=lambda: ec.generate_private_key(ec.SECP256R1())
    )

    def public_jwk(self) -> dict[str, Any]:
        jwk: dict[str, Any] = jwt.algorithms.ECAlgorithm.to_jwk(
            self.private_key.public_key(), as_dict=True
        )
        return {**jwk, "kid": self.kid, "alg": "ES256", "use": "sig"}


@dataclass
class FakeIdentityProvider:
    keys: list[SigningKey]
    jwks_requests: int = 0
    available: bool = True

    def handler(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) != JWKS_URL:
            return httpx.Response(404)
        self.jwks_requests += 1
        if not self.available:
            return httpx.Response(503)
        return httpx.Response(200, json={"keys": [key.public_jwk() for key in self.keys]})

    def token(
        self,
        subject: str | None = None,
        *,
        email: str | None = "ada@example.com",
        key: SigningKey | None = None,
        expires_in: int = 3600,
        **claim_overrides: Any,
    ) -> str:
        signing_key = key or self.keys[0]
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": subject or str(uuid.uuid4()),
            "aud": "authenticated",
            "iss": ISSUER,
            "iat": now,
            "exp": now + expires_in,
            "role": "authenticated",
            "email": email,
            "app_metadata": {"provider": "email"},
            "user_metadata": {},
            "is_anonymous": False,
        }
        claims.update(claim_overrides)
        claims = {name: value for name, value in claims.items() if value is not ...}
        return jwt.encode(
            claims, signing_key.private_key, algorithm="ES256", headers={"kid": signing_key.kid}
        )


@pytest.fixture
def idp() -> FakeIdentityProvider:
    return FakeIdentityProvider(keys=[SigningKey(kid="key-1")])


# ── Application ─────────────────────────────────────────────────────────────

AppFactory = Callable[..., FastAPI]


@pytest.fixture
def make_app(test_env: SuiteEnvironment, idp: FakeIdentityProvider) -> AppFactory:
    def factory(**setting_overrides: Any) -> FastAPI:
        settings = build_settings(test_env, **setting_overrides)
        transport = httpx.MockTransport(idp.handler)
        return create_app(settings, auth_provider=SupabaseAuthProvider(settings, transport))

    return factory


@pytest_asyncio.fixture
async def app(make_app: AppFactory, db_engine: AsyncEngine) -> FastAPI:
    return make_app()


@asynccontextmanager
async def running(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Start the app's lifespan and yield an HTTP client bound to it."""
    async with LifespanManager(app) as manager:
        transport = httpx.ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://api.test") as client:
            yield client


@pytest_asyncio.fixture
async def session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session for tests that need to reach past the API, e.g. to write model-proposed evidence.

    Must close: an open transaction here blocks the TRUNCATE that cleans up after each test.
    """
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with running(app) as client:
        yield client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
