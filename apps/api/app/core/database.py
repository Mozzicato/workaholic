from collections.abc import AsyncIterator
from typing import Any, Literal

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.azure_identity import create_azure_credential
from app.core.config import Settings

# Token audience for Azure Database for PostgreSQL with Microsoft Entra authentication.
POSTGRES_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

DatabaseAuth = Literal["password", "entra_id"]


def database_connect_args(
    auth: DatabaseAuth,
    *,
    production: bool,
    client_id: str | None,
    credential: AsyncTokenCredential | None = None,
) -> tuple[dict[str, Any], AsyncTokenCredential | None]:
    """asyncpg connection arguments for the configured authentication mode.

    With `entra_id` the password is an async callable: asyncpg calls it for every new
    connection, so each one authenticates with a fresh Entra token and no database password
    exists anywhere. Returns the credential the caller must close, if one was created here.
    """
    if auth == "password":
        return {}, None
    owned = credential is None
    token_credential = credential or create_azure_credential(
        production=production, client_id=client_id
    )
    provider = get_bearer_token_provider(token_credential, POSTGRES_ENTRA_SCOPE)
    return {"password": provider}, token_credential if owned else None


class Database:
    """Owns the connection pool for one process. Created at startup, disposed at shutdown."""

    def __init__(self, settings: Settings, credential: AsyncTokenCredential | None = None) -> None:
        connect_args, self._credential = database_connect_args(
            settings.database_auth,
            production=settings.is_production,
            client_id=settings.azure_client_id,
            credential=credential,
        )
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            connect_args=connect_args,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            # Recycle well within the Entra token lifetime; new connections get new tokens.
            pool_recycle=1800,
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessionmaker() as session:
            yield session

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()
        if self._credential is not None:
            await self._credential.close()
