"""LLM provider for any OpenAI-compatible Chat Completions API.

Azure Foundry's v1 endpoint, OpenAI, Groq, Google's Gemini OpenAI-compatibility endpoint,
Mistral and others all speak this protocol, so one adapter covers them; only the base URL,
credentials and capability flags differ.

Chat Completions is used deliberately instead of the Responses API: it is stateless, so
resume content is not persisted by the model service, and it is the most portable protocol.
"""

import json
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any, Literal, NoReturn

import openai
import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.services.ai.base import ChatMessage, GenerationResult, StructuredResult, TokenUsage
from app.services.ai.errors import (
    AIBusyError,
    AIContentFilteredError,
    AIInvalidOutputError,
    AIUnavailableError,
)

logger = structlog.get_logger("app.ai")

StructuredOutputMode = Literal["json_schema", "json_object"]
TokenLimitParam = Literal["max_completion_tokens", "max_tokens"]


def new_trace_id() -> str:
    return f"ait_{uuid.uuid4().hex}"


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        client: AsyncOpenAI,
        default_model: str,
        max_output_tokens: int,
        reasoning_effort: str | None = None,
        structured_output_mode: StructuredOutputMode = "json_schema",
        structured_output_attempts: int = 2,
        token_limit_param: TokenLimitParam = "max_completion_tokens",  # noqa: S107
        on_close: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._name = name
        self._client = client
        self._default_model = default_model
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort
        self._structured_output_mode = structured_output_mode
        self._structured_output_attempts = structured_output_attempts
        self._token_limit_param = token_limit_param
        self._on_close = on_close

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._default_model

    # ── Public interface ────────────────────────────────────────────────────

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> GenerationResult:
        model = model or self._default_model
        trace_id = new_trace_id()
        started = time.perf_counter()
        try:
            completion = await self._client.chat.completions.create(
                **self._request(messages, model, max_output_tokens)
            )
        except Exception as exc:
            self._raise_mapped(exc, operation=operation, model=model, trace_id=trace_id)

        choice = completion.choices[0]
        if choice.finish_reason == "content_filter":
            self._log_failure(operation, model, trace_id, "ContentFilterFinishReason")
            raise AIContentFilteredError()

        usage = _usage(completion.usage)
        latency_ms = _elapsed_ms(started)
        self._log_success(
            operation,
            model,
            trace_id,
            usage,
            latency_ms,
            choice.finish_reason,
            attempts=1,
            provider_request_id=getattr(completion, "_request_id", None),
        )
        return GenerationResult(
            text=choice.message.content or "",
            model=model,
            usage=usage,
            finish_reason=choice.finish_reason,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )

    async def structured_output[T: BaseModel](
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> StructuredResult[T]:
        model = model or self._default_model
        trace_id = new_trace_id()
        started = time.perf_counter()
        conversation = list(messages)
        if self._structured_output_mode == "json_object":
            conversation.insert(0, _schema_instruction(schema))
        usage = TokenUsage()

        for attempt in range(1, self._structured_output_attempts + 1):
            raw, attempt_usage, finish_reason = await self._complete_json(
                conversation, schema, model, max_output_tokens, operation, trace_id
            )
            usage = usage + attempt_usage
            try:
                if raw is None:
                    raise ValueError("empty or refused response")
                value = schema.model_validate_json(raw)
            except (ValidationError, ValueError) as exc:
                logger.warning(
                    "ai_output_invalid",
                    operation=operation,
                    provider=self._name,
                    model=model,
                    trace_id=trace_id,
                    attempt=attempt,
                    finish_reason=finish_reason,
                    error_type=type(exc).__name__,
                )
                conversation += _repair_messages(raw, exc)
                continue

            latency_ms = _elapsed_ms(started)
            self._log_success(
                operation, model, trace_id, usage, latency_ms, finish_reason, attempts=attempt
            )
            return StructuredResult(
                value=value,
                model=model,
                usage=usage,
                attempts=attempt,
                trace_id=trace_id,
                latency_ms=latency_ms,
            )

        self._log_failure(operation, model, trace_id, "InvalidStructuredOutput", usage=usage)
        raise AIInvalidOutputError()

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        model = model or self._default_model
        trace_id = new_trace_id()
        started = time.perf_counter()
        usage = TokenUsage()
        finish_reason: str | None = None
        try:
            chunks = await self._client.chat.completions.create(
                **self._request(messages, model, max_output_tokens),
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in chunks:
                if chunk.usage is not None:
                    usage = _usage(chunk.usage)
                for choice in chunk.choices:
                    finish_reason = choice.finish_reason or finish_reason
                    if choice.delta.content:
                        yield choice.delta.content
        except Exception as exc:
            self._raise_mapped(exc, operation=operation, model=model, trace_id=trace_id)

        if finish_reason == "content_filter":
            self._log_failure(operation, model, trace_id, "ContentFilterFinishReason")
            raise AIContentFilteredError()
        self._log_success(
            operation, model, trace_id, usage, _elapsed_ms(started), finish_reason, attempts=1
        )

    async def aclose(self) -> None:
        await self._client.close()
        if self._on_close is not None:
            await self._on_close()

    # ── Internals ───────────────────────────────────────────────────────────

    def _request(
        self, messages: Sequence[ChatMessage], model: str, max_output_tokens: int | None
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            self._token_limit_param: max_output_tokens or self._max_output_tokens,
        }
        if self._reasoning_effort is not None:
            request["reasoning_effort"] = self._reasoning_effort
        return request

    async def _complete_json(
        self,
        conversation: Sequence[ChatMessage],
        schema: type[BaseModel],
        model: str,
        max_output_tokens: int | None,
        operation: str,
        trace_id: str,
    ) -> tuple[str | None, TokenUsage, str | None]:
        """One structured-output request. Returns the raw JSON text (None if refused)."""
        response_format: dict[str, Any]
        if self._structured_output_mode == "json_schema":
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": openai.pydantic_function_tool(schema)["function"]["parameters"],
                    "strict": True,
                },
            }
        else:
            response_format = {"type": "json_object"}

        request = self._request(conversation, model, max_output_tokens)
        request["response_format"] = response_format
        try:
            completion = await self._client.chat.completions.create(**request)
        except Exception as exc:
            self._raise_mapped(exc, operation=operation, model=model, trace_id=trace_id)

        choice = completion.choices[0]
        if choice.finish_reason == "content_filter":
            self._log_failure(operation, model, trace_id, "ContentFilterFinishReason")
            raise AIContentFilteredError()
        message = choice.message
        raw = None if getattr(message, "refusal", None) else message.content
        return raw, _usage(completion.usage), choice.finish_reason

    def _raise_mapped(
        self, exc: Exception, *, operation: str, model: str, trace_id: str
    ) -> NoReturn:
        status = getattr(exc, "status_code", None)
        self._log_failure(operation, model, trace_id, type(exc).__name__, status_code=status)
        if isinstance(exc, openai.RateLimitError):
            raise AIBusyError() from exc
        if (
            isinstance(exc, openai.BadRequestError)
            and getattr(exc, "code", None) == "content_filter"
        ):
            raise AIContentFilteredError() from exc
        if isinstance(
            exc, (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError)
        ):
            # Misconfiguration (role assignment, deployment name, endpoint): alert-worthy.
            logger.error(
                "ai_provider_misconfigured",
                provider=self._name,
                model=model,
                trace_id=trace_id,
                status_code=status,
            )
            raise AIUnavailableError() from exc
        if isinstance(exc, openai.APIError):
            raise AIUnavailableError() from exc
        raise exc

    def _log_success(
        self,
        operation: str,
        model: str,
        trace_id: str,
        usage: TokenUsage,
        latency_ms: float,
        finish_reason: str | None,
        *,
        attempts: int,
        provider_request_id: str | None = None,
    ) -> None:
        # Metadata only. Prompts and completions contain career data and are never logged.
        logger.info(
            "ai_call_completed",
            operation=operation,
            provider=self._name,
            model=model,
            trace_id=trace_id,
            latency_ms=latency_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            reasoning_tokens=usage.reasoning_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            finish_reason=finish_reason,
            attempts=attempts,
            provider_request_id=provider_request_id,
        )

    def _log_failure(
        self,
        operation: str,
        model: str,
        trace_id: str,
        error_type: str,
        *,
        status_code: int | None = None,
        usage: TokenUsage | None = None,
    ) -> None:
        logger.warning(
            "ai_call_failed",
            operation=operation,
            provider=self._name,
            model=model,
            trace_id=trace_id,
            error_type=error_type,
            status_code=status_code,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )


def _usage(raw: Any) -> TokenUsage:
    if raw is None:
        return TokenUsage()
    completion_details = getattr(raw, "completion_tokens_details", None)
    prompt_details = getattr(raw, "prompt_tokens_details", None)
    return TokenUsage(
        input_tokens=raw.prompt_tokens or 0,
        output_tokens=raw.completion_tokens or 0,
        reasoning_tokens=getattr(completion_details, "reasoning_tokens", None) or 0,
        cached_input_tokens=getattr(prompt_details, "cached_tokens", None) or 0,
    )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def _schema_instruction(schema: type[BaseModel]) -> ChatMessage:
    return ChatMessage(
        role="system",
        content=(
            "Respond with a single JSON object that conforms to this JSON Schema. "
            "Do not include any other text.\n"
            f"{json.dumps(schema.model_json_schema())}"
        ),
    )


def _repair_messages(raw: str | None, exc: Exception) -> list[ChatMessage]:
    if isinstance(exc, ValidationError):
        # Locations and messages only; never echo input values back into logs or prompts.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'root'}: {error['msg']}"
            for error in exc.errors(include_input=False, include_url=False)
        )
    else:
        problems = "the response was empty or not valid JSON"
    return [
        ChatMessage(role="assistant", content=raw or ""),
        ChatMessage(
            role="user",
            content=(
                "That response did not match the required JSON schema "
                f"({problems}). Reply again with only valid JSON that matches the schema."
            ),
        ),
    ]
