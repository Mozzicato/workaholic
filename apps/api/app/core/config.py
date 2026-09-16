from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parents[2]
# `.parent` (unlike `.parents[n]`) never raises, which matters inside the container where
# the API lives at /app and there is no repository root above it.
_REPO_ROOT = _API_DIR.parent.parent

Environment = Literal["development", "test", "production"]

# Values come from environment variables. For local development they are also read from
# the repository-root `.env` (missing files are ignored); in production Azure injects them.
_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=(_REPO_ROOT / ".env", _API_DIR / ".env"),
    env_file_encoding="utf-8",
    extra="ignore",
)


class MigrationSettings(BaseSettings):
    """The subset needed to run migrations, so deploy jobs don't need every secret."""

    model_config = _SETTINGS_CONFIG

    database_url: str


class Settings(BaseSettings):
    """Application configuration."""

    model_config = _SETTINGS_CONFIG

    environment: Environment = "development"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 5

    redis_url: str

    supabase_url: str
    supabase_secret_key: SecretStr
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_ttl_seconds: int = 600

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("supabase_url")
    @classmethod
    def _normalise_supabase_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("sentry_dsn", mode="before")
    @classmethod
    def _empty_dsn_is_none(cls, value: object) -> object:
        return value or None

    @model_validator(mode="after")
    def _check_production_safety(self) -> Self:
        if self.is_production:
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must list explicit origins in production")
            if not self.supabase_url.startswith("https://"):
                raise ValueError("SUPABASE_URL must use https in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def supabase_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
