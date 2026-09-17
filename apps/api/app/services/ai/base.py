"""The provider-neutral AI interface.

Application services depend on `LLMProvider`, never on a vendor SDK, so the backing model
platform (Azure Foundry today; Groq, Gemini, OpenAI or Anthropic later) is a configuration
choice rather than a rewrite.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0  # included in output_tokens; billed as output
    cached_input_tokens: int = 0  # included in input_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
        )


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    model: str
    usage: TokenUsage
    finish_reason: str | None
    trace_id: str
    latency_ms: float


@dataclass(frozen=True, slots=True)
class StructuredResult[T: BaseModel]:
    value: T
    model: str
    usage: TokenUsage  # summed across attempts
    attempts: int
    trace_id: str
    latency_ms: float


class LLMProvider(Protocol):
    """A chat model that can generate text and schema-validated structured output.

    `operation` names the business step (e.g. "interview.next_question") for tracing and
    cost attribution. `model` overrides the configured default, which benchmarking uses.
    """

    @property
    def name(self) -> str: ...

    @property
    def default_model(self) -> str: ...

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> GenerationResult: ...

    async def structured_output[T: BaseModel](
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> StructuredResult[T]:
        """Return output validated against `schema`.

        Schema validation is necessary but not sufficient: callers must still run business
        and evidence validation before anything reaches the database.
        """
        ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        operation: str,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]: ...

    async def aclose(self) -> None: ...
