import httpx
from openai import AsyncOpenAI

from app.core.config import Settings
from app.services.ai.base import LLMProvider
from app.services.ai.providers.azure import build_azure_provider
from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.services.ai.providers.presets import PRESETS


def build_llm_provider(
    settings: Settings, *, http_client: httpx.AsyncClient | None = None
) -> LLMProvider | None:
    """Create the configured provider, or None when AI is disabled."""
    if settings.ai_provider == "disabled":
        return None
    if settings.ai_provider == "azure":
        return build_azure_provider(settings, http_client=http_client)
    if settings.ai_provider == "openai_compatible":
        return _build_openai_compatible_provider(settings, http_client)
    return _build_preset_provider(settings, http_client)


def _build_openai_compatible_provider(
    settings: Settings, http_client: httpx.AsyncClient | None
) -> OpenAICompatibleProvider:
    if not settings.openai_compatible_base_url or not settings.openai_compatible_model:
        raise ValueError("OpenAI-compatible provider requires a base URL and model")
    api_key = settings.openai_compatible_api_key
    client = AsyncOpenAI(
        base_url=settings.openai_compatible_base_url,
        # Some local servers need no key, but the SDK requires a non-empty value.
        api_key=api_key.get_secret_value() if api_key else "not-required",
        timeout=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
        http_client=http_client,
    )
    return OpenAICompatibleProvider(
        name="openai_compatible",
        client=client,
        default_model=settings.openai_compatible_model,
        max_output_tokens=settings.ai_max_output_tokens,
        reasoning_effort=settings.ai_reasoning_effort,
        structured_output_mode=settings.ai_structured_output_mode,
        structured_output_attempts=settings.ai_structured_output_attempts,
        token_limit_param=settings.openai_compatible_token_limit_param,
    )


def _build_preset_provider(
    settings: Settings, http_client: httpx.AsyncClient | None
) -> OpenAICompatibleProvider:
    name = settings.ai_provider
    if name not in PRESETS:
        raise ValueError(f"Unknown AI provider: {name}")
    preset = PRESETS[name]
    api_key, model = settings.preset_credentials(name)
    client = AsyncOpenAI(
        base_url=preset.base_url,
        api_key=api_key,
        default_headers=dict(preset.default_headers),
        timeout=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
        http_client=http_client,
    )
    return OpenAICompatibleProvider(
        name=name,
        client=client,
        default_model=model,
        max_output_tokens=settings.ai_max_output_tokens,
        reasoning_effort=settings.ai_reasoning_effort if preset.supports_reasoning_effort else None,
        structured_output_mode=preset.structured_output_mode,
        structured_output_attempts=settings.ai_structured_output_attempts,
        token_limit_param=preset.token_limit_param,
    )
