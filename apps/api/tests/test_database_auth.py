"""Passwordless PostgreSQL: the managed identity's Entra token is the connection password."""

import time
from typing import Any

import pytest
from azure.core.credentials import AccessToken
from pydantic import SecretStr

from app.core.config import Settings
from app.core.database import POSTGRES_ENTRA_SCOPE, database_connect_args


class FakeCredential:
    def __init__(self) -> None:
        self.calls = 0

    async def get_token(self, *scopes: str, **_: Any) -> AccessToken:
        self.calls += 1
        assert scopes == (POSTGRES_ENTRA_SCOPE,)
        return AccessToken(f"entra-token-{self.calls}", int(time.time()) + 3600)

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> "FakeCredential":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


def test_password_auth_adds_nothing() -> None:
    connect_args, credential = database_connect_args("password", production=False, client_id=None)

    assert connect_args == {}
    assert credential is None


async def test_entra_auth_supplies_a_fresh_token_as_the_password() -> None:
    fake = FakeCredential()

    connect_args, owned = database_connect_args(
        "entra_id", production=True, client_id="client", credential=fake
    )

    password = connect_args["password"]
    assert callable(password)  # asyncpg calls it for every new connection
    assert await password() == "entra-token-1"
    assert owned is None  # caller-supplied credentials are not closed by us


def production_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "production",
        "cors_origins": ["https://app.example.com"],
        "database_url": "postgresql+asyncpg://workaholic-api-id@db.example.com/workaholic",
        "supabase_url": "https://project.supabase.co",
        "supabase_secret_key": SecretStr("unused"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_entra_database_requires_the_managed_identity_client_id() -> None:
    with pytest.raises(ValueError, match="AZURE_CLIENT_ID"):
        production_settings(database_auth="entra_id")

    settings = production_settings(database_auth="entra_id", azure_client_id="client-id")
    assert settings.database_auth == "entra_id"


def test_supabase_secret_key_is_optional_until_admin_actions_ship() -> None:
    settings = production_settings(supabase_secret_key=None)

    assert settings.supabase_secret_key is None
