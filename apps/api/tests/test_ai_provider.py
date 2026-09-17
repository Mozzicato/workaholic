"""AI provider layer, exercised against a simulated OpenAI-compatible endpoint.

No real model is called: these tests pin down request shape, authentication, output
validation, error mapping and the no-content logging rule.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from azure.core.credentials import AccessToken
from pydantic import BaseModel, SecretStr

from app.core.config import Settings
from app.core.logging import configure_logging
from app.services.ai.base import ChatMessage
from app.services.ai.errors import (
    AIBusyError,
    AIContentFilteredError,
    AIInvalidOutputError,
    AIUnavailableError,
)
from app.services.ai.factory import build_llm_provider
from app.services.ai.providers.azure import (
    AZURE_AI_TOKEN_SCOPE,
    azure_v1_base_url,
    build_azure_provider,
)

ENDPOINT = "https://workaholic-ai.openai.azure.com"
SECRET_RESUME_TEXT = "Led the confidential Initech migration for 40,000 users"


class Project(BaseModel):
    name: str
    technologies: list[str]


def completion(
    content: str | None,
    *,
    finish_reason: str = "stop",
    refusal: str | None = None,
    prompt_tokens: int = 120,
    completion_tokens: int = 80,
    reasoning_tokens: int = 30,
) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "gpt-5-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }


@dataclass
class FakeModelServer:
    responses: list[httpx.Response] = field(default_factory=list)
    requests: list[httpx.Request] = field(default_factory=list)

    def reply(self, body: dict[str, Any], status: int = 200) -> None:
        self.responses.append(httpx.Response(status, json=body))

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def body(self, index: int = -1) -> dict[str, Any]:
        parsed: dict[str, Any] = json.loads(self.requests[index].content)
        return parsed

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))


class FakeCredential:
    def __init__(self) -> None:
        self.scopes: list[tuple[str, ...]] = []

    async def get_token(self, *scopes: str, **_: Any) -> AccessToken:
        self.scopes.append(scopes)
        return AccessToken("entra-token-123", int(time.time()) + 3600)

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> "FakeCredential":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


def azure_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "database_url": "postgresql+asyncpg://unused/unused",
        "supabase_url": "https://test-project.supabase.co",
        "supabase_secret_key": SecretStr("sb_secret_test"),
        "ai_provider": "azure",
        "azure_ai_endpoint": ENDPOINT,
        "azure_ai_model": "gpt-5-mini",
        "azure_ai_auth": "api_key",
        "azure_ai_api_key": SecretStr("azure-key-abc"),
        "ai_max_retries": 0,
    }
    values.update(overrides)
    # Ignore the developer's .env so real keys never influence test outcomes.
    return Settings(_env_file=None, **values)


@pytest.fixture
def server() -> FakeModelServer:
    return FakeModelServer()


ProviderFactory = Callable[..., Any]


@pytest.fixture
def make_provider(server: FakeModelServer) -> ProviderFactory:
    def factory(**overrides: Any) -> Any:
        return build_llm_provider(azure_settings(**overrides), http_client=server.client())

    return factory


MESSAGES = [
    ChatMessage(role="system", content="Extract projects."),
    ChatMessage(role="user", content=SECRET_RESUME_TEXT),
]


# ── Endpoint and authentication ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://res.openai.azure.com",
        "https://res.openai.azure.com/",
        "https://res.openai.azure.com/openai/v1",
        "https://res.openai.azure.com/openai/v1/",
    ],
)
def test_azure_v1_base_url_is_normalised(endpoint: str) -> None:
    assert azure_v1_base_url(endpoint) == "https://res.openai.azure.com/openai/v1/"


async def test_azure_api_key_auth_calls_v1_chat_completions(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion("hello"))
    provider = make_provider()

    result = await provider.generate(MESSAGES, operation="test.generate")

    request = server.requests[0]
    assert str(request.url) == f"{ENDPOINT}/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer azure-key-abc"
    assert result.text == "hello"
    await provider.aclose()


async def test_azure_entra_id_auth_sends_managed_identity_token(server: FakeModelServer) -> None:
    server.reply(completion("hello"))
    credential = FakeCredential()
    provider = build_azure_provider(
        azure_settings(azure_ai_auth="entra_id", azure_ai_api_key=None),
        credential=credential,
        http_client=server.client(),
    )

    await provider.generate(MESSAGES, operation="test.generate")

    assert server.requests[0].headers["Authorization"] == "Bearer entra-token-123"
    assert credential.scopes == [(AZURE_AI_TOKEN_SCOPE,)]
    await provider.aclose()


def test_ai_disabled_builds_no_provider() -> None:
    assert build_llm_provider(azure_settings(ai_provider="disabled")) is None


@pytest.mark.parametrize(
    ("overrides", "missing"),
    [
        ({"azure_ai_endpoint": None}, "AZURE_AI_ENDPOINT"),
        ({"azure_ai_model": None}, "AZURE_AI_MODEL"),
        ({"azure_ai_api_key": None}, "AZURE_AI_API_KEY"),
    ],
)
def test_incomplete_azure_configuration_fails_fast(overrides: dict[str, Any], missing: str) -> None:
    with pytest.raises(ValueError, match=missing):
        azure_settings(**overrides)


def test_entra_id_needs_no_api_key() -> None:
    settings = azure_settings(azure_ai_auth="entra_id", azure_ai_api_key=None)
    assert settings.azure_ai_api_key is None


def test_ai_endpoint_must_use_https() -> None:
    with pytest.raises(ValueError, match="https"):
        azure_settings(azure_ai_endpoint="http://res.openai.azure.com")


# ── Request shape ─────────────────────────────────────────────────────────────


async def test_request_uses_configured_model_and_token_limit(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion("ok"))
    provider = make_provider(ai_max_output_tokens=1500, ai_reasoning_effort="low")

    await provider.generate(MESSAGES, operation="test.generate")

    body = server.body()
    assert body["model"] == "gpt-5-mini"
    assert body["max_completion_tokens"] == 1500
    assert body["reasoning_effort"] == "low"
    assert "temperature" not in body  # unsupported by reasoning models
    assert "store" not in body  # nothing persisted service-side


async def test_model_can_be_overridden_per_call(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion("ok"))
    provider = make_provider()

    result = await provider.generate(MESSAGES, operation="benchmark", model="gpt-5-nano")

    assert server.body()["model"] == "gpt-5-nano"
    assert result.model == "gpt-5-nano"


async def test_usage_is_reported(server: FakeModelServer, make_provider: ProviderFactory) -> None:
    server.reply(completion("ok", prompt_tokens=500, completion_tokens=200, reasoning_tokens=150))
    provider = make_provider()

    result = await provider.generate(MESSAGES, operation="test.generate")

    assert (result.usage.input_tokens, result.usage.output_tokens) == (500, 200)
    assert result.usage.reasoning_tokens == 150
    assert result.trace_id.startswith("ait_")


# ── Structured output ─────────────────────────────────────────────────────────


async def test_structured_output_uses_strict_json_schema(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion(json.dumps({"name": "Marketplace", "technologies": ["FastAPI"]})))
    provider = make_provider()

    result = await provider.structured_output(MESSAGES, Project, operation="test.extract")

    assert result.value == Project(name="Marketplace", technologies=["FastAPI"])
    assert result.attempts == 1
    response_format = server.body()["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False


async def test_invalid_structured_output_is_repaired_with_feedback(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion(json.dumps({"name": "Marketplace"}), completion_tokens=10))
    server.reply(
        completion(json.dumps({"name": "Marketplace", "technologies": []}), completion_tokens=12)
    )
    provider = make_provider(ai_structured_output_attempts=2)

    result = await provider.structured_output(MESSAGES, Project, operation="test.extract")

    assert result.attempts == 2
    assert result.usage.output_tokens == 22  # usage summed across attempts
    repair_prompt = server.body(1)["messages"][-1]["content"]
    assert "technologies" in repair_prompt
    assert SECRET_RESUME_TEXT not in repair_prompt


async def test_persistently_invalid_output_raises(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion("not json"))
    server.reply(completion("{}"))
    provider = make_provider(ai_structured_output_attempts=2)

    with pytest.raises(AIInvalidOutputError):
        await provider.structured_output(MESSAGES, Project, operation="test.extract")
    assert len(server.requests) == 2


async def test_refusal_is_treated_as_invalid_output(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion(None, refusal="I can't help with that."))
    provider = make_provider(ai_structured_output_attempts=1)

    with pytest.raises(AIInvalidOutputError):
        await provider.structured_output(MESSAGES, Project, operation="test.extract")


async def test_json_object_mode_embeds_schema_instruction(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion(json.dumps({"name": "A", "technologies": []})))
    provider = make_provider(ai_structured_output_mode="json_object")

    await provider.structured_output(MESSAGES, Project, operation="test.extract")

    body = server.body()
    assert body["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in body["messages"][0]["content"]


# ── Streaming ────────────────────────────────────────────────────────────────


async def test_stream_yields_text_deltas(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    def chunk(
        delta: dict[str, Any], finish: str | None = None, usage: dict[str, Any] | None = None
    ) -> str:
        payload = {
            "id": "c",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "gpt-5-mini",
            "choices": [] if usage else [{"index": 0, "delta": delta, "finish_reason": finish}],
            "usage": usage,
        }
        return f"data: {json.dumps(payload)}\n\n"

    stream_body = (
        chunk({"role": "assistant", "content": "Hel"})
        + chunk({"content": "lo"})
        + chunk({}, finish="stop")
        + chunk({}, usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7})
        + "data: [DONE]\n\n"
    )
    server.responses.append(
        httpx.Response(200, content=stream_body, headers={"content-type": "text/event-stream"})
    )
    provider = make_provider()

    parts = [part async for part in provider.stream(MESSAGES, operation="test.stream")]

    assert "".join(parts) == "Hello"
    assert server.body()["stream_options"] == {"include_usage": True}


# ── Error mapping ─────────────────────────────────────────────────────────────


def api_error(code: str | None, message: str = "error") -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "type": "invalid_request_error"}}


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (429, api_error("429"), AIBusyError),
        (
            400,
            api_error("content_filter", f"Filtered: {SECRET_RESUME_TEXT}"),
            AIContentFilteredError,
        ),
        (401, api_error("PermissionDenied"), AIUnavailableError),
        (403, api_error("AuthorizationFailed"), AIUnavailableError),
        (404, api_error("DeploymentNotFound"), AIUnavailableError),
        (500, api_error("server_error"), AIUnavailableError),
    ],
)
async def test_provider_errors_map_to_safe_application_errors(
    server: FakeModelServer,
    make_provider: ProviderFactory,
    status: int,
    body: dict[str, Any],
    expected: type[Exception],
) -> None:
    server.reply(body, status=status)
    provider = make_provider()

    with pytest.raises(expected) as caught:
        await provider.generate(MESSAGES, operation="test.generate")

    assert SECRET_RESUME_TEXT not in str(caught.value)


async def test_content_filter_finish_reason_is_reported(
    server: FakeModelServer, make_provider: ProviderFactory
) -> None:
    server.reply(completion("", finish_reason="content_filter"))
    provider = make_provider()

    with pytest.raises(AIContentFilteredError):
        await provider.generate(MESSAGES, operation="test.generate")


async def test_network_failure_maps_to_unavailable(
    make_provider: ProviderFactory, server: FakeModelServer
) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = build_llm_provider(
        azure_settings(), http_client=httpx.AsyncClient(transport=httpx.MockTransport(broken))
    )
    assert provider is not None

    with pytest.raises(AIUnavailableError):
        await provider.generate(MESSAGES, operation="test.generate")


# ── Privacy ──────────────────────────────────────────────────────────────────


async def test_prompts_and_completions_are_never_logged(
    server: FakeModelServer, make_provider: ProviderFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    # Use the production logging pipeline, bound to this test's captured stdout.
    configure_logging(azure_settings(log_level="INFO"))
    server.reply(completion(json.dumps({"name": SECRET_RESUME_TEXT, "technologies": []})))
    server.reply(api_error("content_filter", SECRET_RESUME_TEXT), status=400)
    provider = make_provider()

    await provider.structured_output(MESSAGES, Project, operation="test.extract")
    with pytest.raises(AIContentFilteredError):
        await provider.generate(MESSAGES, operation="test.generate")

    captured = capsys.readouterr()
    assert "ai_call_completed" in captured.out
    assert SECRET_RESUME_TEXT not in captured.out + captured.err


# ── OpenAI-compatible providers ───────────────────────────────────────────────


async def test_openai_compatible_provider_supports_legacy_token_param(
    server: FakeModelServer,
) -> None:
    server.reply(completion("ok"))
    settings = azure_settings(
        ai_provider="openai_compatible",
        openai_compatible_base_url="https://api.example-llm.dev/v1",
        openai_compatible_api_key=SecretStr("other-key"),
        openai_compatible_model="small-model",
        openai_compatible_token_limit_param="max_tokens",
    )
    provider = build_llm_provider(settings, http_client=server.client())
    assert provider is not None

    await provider.generate(MESSAGES, operation="test.generate")

    request = server.requests[0]
    assert str(request.url) == "https://api.example-llm.dev/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer other-key"
    assert server.body()["model"] == "small-model"
    assert "max_tokens" in server.body()
    assert "max_completion_tokens" not in server.body()


def test_async_azure_credentials_have_their_http_transport_installed() -> None:
    # azure-identity's async credentials need aiohttp at runtime; the tests above inject a fake
    # credential, so guard the real dependency explicitly.
    from azure.core.pipeline.transport import AioHttpTransport

    assert AioHttpTransport is not None


# ── Named presets ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("provider", "expected_url"),
    [
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
        ("groq", "https://api.groq.com/openai/v1/chat/completions"),
        ("mistral", "https://api.mistral.ai/v1/chat/completions"),
        ("openrouter", "https://openrouter.ai/api/v1/chat/completions"),
    ],
)
async def test_named_presets_use_their_endpoint_key_and_model(
    server: FakeModelServer, provider: str, expected_url: str
) -> None:
    server.reply(completion("ok"))
    settings = azure_settings(
        ai_provider=provider,
        ai_reasoning_effort="low",
        **{f"{provider}_api_key": SecretStr(f"{provider}-key"), f"{provider}_model": "small"},
    )
    llm = build_llm_provider(settings, http_client=server.client())
    assert llm is not None

    await llm.generate(MESSAGES, operation="test.generate")

    request = server.requests[0]
    assert str(request.url) == expected_url
    assert request.headers["Authorization"] == f"Bearer {provider}-key"
    body = server.body()
    assert body["model"] == "small"
    # Reasoning effort is only forwarded to providers that accept it.
    assert ("reasoning_effort" in body) == (provider in ("gemini", "groq"))


def test_named_preset_requires_its_own_key_and_model() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        azure_settings(ai_provider="groq", groq_model="small")
    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        azure_settings(ai_provider="gemini", gemini_api_key=SecretStr("k"))


def test_production_refuses_non_azure_providers_by_default() -> None:
    production = {
        "environment": "production",
        "cors_origins": ["https://app.example.com"],
        "ai_provider": "groq",
        "groq_api_key": SecretStr("k"),
        "groq_model": "small",
    }
    with pytest.raises(ValueError, match="AI_PROVIDER=azure"):
        azure_settings(**production)
    assert azure_settings(**production, ai_allow_non_azure_in_production=True).ai_provider == "groq"
