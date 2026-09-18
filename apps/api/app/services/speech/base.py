"""The provider-neutral speech interface (PRD §27).

The interview agent never sees a speech SDK. It receives text, and how that text was produced —
Azure today, something else tomorrow — is a configuration choice.

Audio is not stored. It arrives in memory, is transcribed, and is discarded; only the transcript
is written down, and only after the person has seen it and pressed send.
"""

from dataclasses import dataclass
from typing import Protocol

__all__ = ["Audio", "SpeechToTextProvider", "Transcription"]

MAX_AUDIO_BYTES = 10 * 1024 * 1024
"""About ten minutes of compressed speech. An answer is a sentence, not a podcast."""

ALLOWED_AUDIO_TYPES = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/flac",
    }
)


@dataclass(frozen=True, slots=True)
class Audio:
    """One recording, held in memory only."""

    content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True, slots=True)
class Transcription:
    text: str
    model: str
    provider: str
    latency_ms: float


class SpeechToTextProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def transcribe(self, audio: Audio, *, language: str | None = None) -> Transcription: ...

    async def aclose(self) -> None: ...
