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
AIProviderName = Literal[
    "disabled", "azure", "openai_compatible", "gemini", "groq", "mistral", "openrouter"
]
PresetProviderName = Literal["gemini", "groq", "mistral", "openrouter"]
# Speech runs on the same providers, so a change of AI platform carries voice with it.
STTProviderName = Literal["disabled", "azure", "groq"]
AzureAIAuth = Literal["entra_id", "api_key"]
StructuredOutputMode = Literal["json_schema", "json_object"]
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high"]
TokenLimitParam = Literal["max_completion_tokens", "max_tokens"]
DatabaseAuth = Literal["password", "entra_id"]

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

    environment: Environment = "development"
    database_url: str
    database_auth: DatabaseAuth = "password"
    azure_client_id: str | None = None


class Settings(BaseSettings):
    """Application configuration."""

    model_config = _SETTINGS_CONFIG

    environment: Environment = "development"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: str
    # "entra_id": passwordless, the managed identity's Entra token is the password.
    database_auth: DatabaseAuth = "password"
    database_pool_size: int = 5
    database_max_overflow: int = 5

    # Optional until a feature needs it (background jobs, rate limiting). Infrastructure is
    # added incrementally, so the API must run without Redis.
    redis_url: str | None = None

    supabase_url: str
    # Not used yet; required only once server-side admin actions (account deletion) ship.
    supabase_secret_key: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_ttl_seconds: int = 600

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0

    # ── AI provider ──────────────────────────────────────────────────────────
    # Which LLM backend the application uses. "disabled" keeps AI features off.
    ai_provider: AIProviderName = "disabled"
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_max_output_tokens: int = Field(default=4000, ge=256)
    # Only sent when set; reasoning models bill hidden reasoning tokens as output.
    ai_reasoning_effort: ReasoningEffort | None = None
    ai_structured_output_mode: StructuredOutputMode = "json_schema"
    ai_structured_output_attempts: int = Field(default=2, ge=1, le=4)

    # ── Speech to text ───────────────────────────────────────────────────────
    # Voice is an interface over the interview (PRD section 26); "disabled" leaves the
    # interview text-only, which it is designed to work as.
    stt_provider: STTProviderName = "disabled"
    stt_model: str = "gpt-4o-transcribe"
    stt_timeout_seconds: float = 120.0
    # Audio is not served by the Azure OpenAI v1 API: transcription is only available on the
    # deployment-scoped path, which requires a dated API version (verified against the live
    # resource, 2026-09-18 — /openai/v1/audio/transcriptions answers DeploymentNotFound).
    azure_stt_api_version: str = "2025-04-01-preview"
    # A spoken answer, not a lecture. Enforced before any audio reaches a provider.
    stt_max_seconds: int = Field(default=180, ge=10, le=600)

    # Azure / Microsoft Foundry (primary). The model is the *deployment name*.
    azure_ai_endpoint: str | None = None
    azure_ai_model: str | None = None
    azure_ai_auth: AzureAIAuth = "entra_id"
    azure_ai_api_key: SecretStr | None = None
    # Client ID of the user-assigned managed identity in Azure Container Apps.
    azure_client_id: str | None = None

    # Any OpenAI-compatible Chat Completions API (Groq, Gemini, Mistral, OpenAI, ...).
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: SecretStr | None = None
    openai_compatible_model: str | None = None
    openai_compatible_token_limit_param: TokenLimitParam = "max_completion_tokens"  # noqa: S105

    # Named development/benchmark providers. Fictional data only: free tiers may train on inputs.
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None
    mistral_api_key: SecretStr | None = None
    mistral_model: str | None = None
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str | None = None
    # Real resume data may only reach providers with data-processing terms (Azure).
    ai_allow_non_azure_in_production: bool = False

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

    @field_validator(
        "sentry_dsn",
        "redis_url",
        "azure_ai_endpoint",
        "azure_ai_model",
        "azure_ai_api_key",
        "azure_client_id",
        "supabase_secret_key",
        "openai_compatible_base_url",
        "openai_compatible_api_key",
        "openai_compatible_model",
        "ai_reasoning_effort",
        "gemini_api_key",
        "gemini_model",
        "groq_api_key",
        "groq_model",
        "mistral_api_key",
        "mistral_model",
        "openrouter_api_key",
        "openrouter_model",
        mode="before",
    )
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        return value or None

    @field_validator("azure_ai_endpoint", "openai_compatible_base_url")
    @classmethod
    def _require_https(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(
            ("https://", "http://localhost", "http://127.0.0.1")
        ):
            raise ValueError("AI endpoints must use https")
        return value.rstrip("/") if value else value

    @model_validator(mode="after")
    def _check_production_safety(self) -> Self:
        if self.is_production:
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must list explicit origins in production")
            if not self.supabase_url.startswith("https://"):
                raise ValueError("SUPABASE_URL must use https in production")
            uses_entra = self.database_auth == "entra_id" or (
                self.ai_provider == "azure" and self.azure_ai_auth == "entra_id"
            )
            if uses_entra and not self.azure_client_id:
                raise ValueError(
                    "AZURE_CLIENT_ID (the user-assigned managed identity) is required in "
                    "production when Microsoft Entra authentication is used"
                )
        return self

    @model_validator(mode="after")
    def _check_speech_provider(self) -> Self:
        if self.stt_provider == "azure" and not self.azure_ai_endpoint:
            raise ValueError("STT_PROVIDER=azure requires AZURE_AI_ENDPOINT")
        if not self.stt_model and self.stt_provider != "disabled":
            raise ValueError("A speech provider requires STT_MODEL")
        return self

    @model_validator(mode="after")
    def _check_ai_provider(self) -> Self:
        if self.ai_provider == "azure":
            missing = [
                name
                for name, value in (
                    ("AZURE_AI_ENDPOINT", self.azure_ai_endpoint),
                    ("AZURE_AI_MODEL", self.azure_ai_model),
                )
                if not value
            ]
            if self.azure_ai_auth == "api_key" and not self.azure_ai_api_key:
                missing.append("AZURE_AI_API_KEY")
            if missing:
                raise ValueError(f"AI_PROVIDER=azure requires {', '.join(missing)}")
        if self.ai_provider == "openai_compatible" and not (
            self.openai_compatible_base_url and self.openai_compatible_model
        ):
            raise ValueError(
                "AI_PROVIDER=openai_compatible requires OPENAI_COMPATIBLE_BASE_URL "
                "and OPENAI_COMPATIBLE_MODEL"
            )
        if self.ai_provider in ("gemini", "groq", "mistral", "openrouter"):
            prefix = self.ai_provider.upper()
            if getattr(self, f"{self.ai_provider}_api_key") is None:
                raise ValueError(f"AI_PROVIDER={self.ai_provider} requires {prefix}_API_KEY")
            if getattr(self, f"{self.ai_provider}_model") is None:
                raise ValueError(f"AI_PROVIDER={self.ai_provider} requires {prefix}_MODEL")
        if (
            self.is_production
            and self.ai_provider not in ("azure", "disabled")
            and not self.ai_allow_non_azure_in_production
        ):
            raise ValueError(
                "Production must use AI_PROVIDER=azure (or set "
                "AI_ALLOW_NON_AZURE_IN_PRODUCTION=true after reviewing the provider's data terms)"
            )
        return self

    def preset_credentials(self, name: PresetProviderName) -> tuple[str, str]:
        key: SecretStr | None = getattr(self, f"{name}_api_key")
        model: str | None = getattr(self, f"{name}_model")
        if key is None or model is None:
            raise ValueError(f"{name.upper()}_API_KEY and {name.upper()}_MODEL are required")
        return key.get_secret_value(), model

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
