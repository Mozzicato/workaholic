"""Building the configured speech provider, or none at all."""

import httpx
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.core.azure_identity import create_azure_credential
from app.core.config import PresetProviderName, Settings
from app.services.ai.providers.azure import AZURE_AI_TOKEN_SCOPE
from app.services.ai.providers.presets import PRESETS
from app.services.speech.base import SpeechToTextProvider
from app.services.speech.openai_compatible import OpenAICompatibleSpeechProvider


def build_speech_provider(
    settings: Settings, *, http_client: httpx.AsyncClient | None = None
) -> SpeechToTextProvider | None:
    """The configured provider, or None when voice is turned off."""
    if settings.stt_provider == "disabled":
        return None
    if settings.stt_provider == "azure":
        return _build_azure(settings, http_client)
    return _build_groq(settings, http_client)


def _build_azure(
    settings: Settings, http_client: httpx.AsyncClient | None
) -> OpenAICompatibleSpeechProvider:
    """Audio uses the deployment-scoped Azure path, not the v1 API the chat models use.

    `AsyncAzureOpenAI` builds `/openai/deployments/<model>/audio/transcriptions?api-version=…`,
    which is the only route that serves transcription on this resource.
    """
    if not settings.azure_ai_endpoint:
        raise ValueError("Azure speech requires AZURE_AI_ENDPOINT")

    endpoint = settings.azure_ai_endpoint.rstrip("/")
    on_close = None

    # Arguments are passed explicitly rather than unpacked: these overloads are keyword-only,
    # and a dict hides which combination is actually being used.
    if settings.azure_ai_auth == "api_key":
        if settings.azure_ai_api_key is None:
            raise ValueError("AZURE_AI_AUTH=api_key requires AZURE_AI_API_KEY")
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=settings.azure_stt_api_version,
            api_key=settings.azure_ai_api_key.get_secret_value(),
            timeout=settings.stt_timeout_seconds,
            max_retries=settings.ai_max_retries,
            http_client=http_client,
        )
    else:
        # The same Entra identity that reaches the chat models reaches the audio ones.
        credential = create_azure_credential(
            production=settings.is_production, client_id=settings.azure_client_id
        )
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=settings.azure_stt_api_version,
            azure_ad_token_provider=get_bearer_token_provider(credential, AZURE_AI_TOKEN_SCOPE),
            timeout=settings.stt_timeout_seconds,
            max_retries=settings.ai_max_retries,
            http_client=http_client,
        )
        on_close = credential.close

    return OpenAICompatibleSpeechProvider(
        name="azure", client=client, model=settings.stt_model, on_close=on_close
    )


def _build_groq(
    settings: Settings, http_client: httpx.AsyncClient | None
) -> OpenAICompatibleSpeechProvider:
    """Groq's Whisper, for running without Azure. The key comes from configuration as usual."""
    name: PresetProviderName = "groq"
    preset = PRESETS[name]
    api_key, _ = settings.preset_credentials(name)
    client = AsyncOpenAI(
        base_url=preset.base_url,
        api_key=api_key,
        timeout=settings.stt_timeout_seconds,
        max_retries=settings.ai_max_retries,
        http_client=http_client,
    )
    return OpenAICompatibleSpeechProvider(name=name, client=client, model=settings.stt_model)
