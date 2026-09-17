"""Azure / Microsoft Foundry models through the Azure OpenAI v1 API.

Authentication, in order of preference:

1. Microsoft Entra ID (default, `AZURE_AI_AUTH=entra_id`). No secret exists anywhere.
   - Production (Azure Container Apps): the app's user-assigned managed identity,
     selected with `AZURE_CLIENT_ID`. The identity needs the *Cognitive Services OpenAI
     User* role on the Foundry resource.
   - Development: `DefaultAzureCredential`, which picks up `az login`.
2. API key (`AZURE_AI_AUTH=api_key` + `AZURE_AI_API_KEY`), for environments where
   identity-based access isn't possible. Not recommended for production.

Reference: https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle
"""

import httpx
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncOpenAI

from app.core.azure_identity import create_azure_credential
from app.core.config import Settings
from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider

# Token audience for the Azure OpenAI v1 API.
AZURE_AI_TOKEN_SCOPE = "https://ai.azure.com/.default"  # noqa: S105 - an OAuth scope, not a secret


def azure_v1_base_url(endpoint: str) -> str:
    """Accepts `https://<resource>.openai.azure.com` or `.services.ai.azure.com`."""
    endpoint = endpoint.rstrip("/")
    if not endpoint.endswith("/openai/v1"):
        endpoint = f"{endpoint}/openai/v1"
    return f"{endpoint}/"


def build_azure_provider(
    settings: Settings,
    *,
    credential: AsyncTokenCredential | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> OpenAICompatibleProvider:
    if not settings.azure_ai_endpoint or not settings.azure_ai_model:
        raise ValueError("Azure AI provider requires AZURE_AI_ENDPOINT and AZURE_AI_MODEL")

    on_close = None
    if settings.azure_ai_auth == "api_key":
        if settings.azure_ai_api_key is None:
            raise ValueError("AZURE_AI_AUTH=api_key requires AZURE_AI_API_KEY")
        client = AsyncOpenAI(
            base_url=azure_v1_base_url(settings.azure_ai_endpoint),
            api_key=settings.azure_ai_api_key.get_secret_value(),
            timeout=settings.ai_timeout_seconds,
            max_retries=settings.ai_max_retries,
            http_client=http_client,
        )
    else:
        token_credential = credential or create_azure_credential(
            production=settings.is_production, client_id=settings.azure_client_id
        )
        client = AsyncOpenAI(
            base_url=azure_v1_base_url(settings.azure_ai_endpoint),
            # The client calls this before each request; tokens are cached and refreshed.
            api_key=get_bearer_token_provider(token_credential, AZURE_AI_TOKEN_SCOPE),
            timeout=settings.ai_timeout_seconds,
            max_retries=settings.ai_max_retries,
            http_client=http_client,
        )
        if credential is None:
            on_close = token_credential.close

    return OpenAICompatibleProvider(
        name="azure",
        client=client,
        default_model=settings.azure_ai_model,
        max_output_tokens=settings.ai_max_output_tokens,
        reasoning_effort=settings.ai_reasoning_effort,
        structured_output_mode=settings.ai_structured_output_mode,
        structured_output_attempts=settings.ai_structured_output_attempts,
        on_close=on_close,
    )
