"""Transcription through any OpenAI-compatible audio endpoint.

Azure Foundry and Groq both speak this API, so one implementation covers both and anything else
that follows the same shape. The provider is chosen by configuration, never by the caller.
"""

import time
from typing import Any

import structlog
from openai import APIStatusError, AsyncOpenAI, OpenAIError

from app.services.speech.base import Audio, Transcription
from app.services.speech.errors import NothingHeardError, SpeechUnavailableError

logger = structlog.get_logger(__name__)


class OpenAICompatibleSpeechProvider:
    def __init__(
        self,
        *,
        name: str,
        client: AsyncOpenAI,
        model: str,
        on_close: Any = None,
    ) -> None:
        self._name = name
        self._client = client
        self._model = model
        self._on_close = on_close

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def transcribe(self, audio: Audio, *, language: str | None = None) -> Transcription:
        started = time.perf_counter()
        request: dict[str, Any] = {
            "model": self._model,
            "file": (audio.filename, audio.content, audio.content_type),
            "response_format": "text",
        }
        if language:
            request["language"] = language

        try:
            response = await self._client.audio.transcriptions.create(**request)
        except APIStatusError as exc:
            # Status only: a transcription failure must never log what was said.
            logger.warning("speech.transcribe.failed", provider=self._name, status=exc.status_code)
            raise SpeechUnavailableError() from exc
        except OpenAIError as exc:
            logger.warning(
                "speech.transcribe.failed", provider=self._name, error=type(exc).__name__
            )
            raise SpeechUnavailableError() from exc

        text = (response if isinstance(response, str) else getattr(response, "text", "")).strip()
        latency_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "speech.transcribed",
            provider=self._name,
            model=self._model,
            latency_ms=round(latency_ms, 1),
            # Length only. The words themselves are the user's career history.
            characters=len(text),
        )
        if not text:
            raise NothingHeardError()
        return Transcription(
            text=text, model=self._model, provider=self._name, latency_ms=latency_ms
        )

    async def aclose(self) -> None:
        await self._client.close()
        if self._on_close is not None:
            await self._on_close()
