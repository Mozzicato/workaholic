"""Speech failures, in the API's error contract. Messages never echo what was said."""

from app.core.errors import AppError, ErrorCode


class SpeechError(AppError):
    """Base class for speech failures."""


class SpeechNotConfiguredError(SpeechError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_NOT_CONFIGURED,
            "Voice isn't available right now. You can type your answer instead.",
            503,
        )


class SpeechUnavailableError(SpeechError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_UNAVAILABLE,
            "We couldn't hear that just now. Try again, or type your answer instead.",
            503,
        )


class AudioRejectedError(SpeechError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, 422)


class NothingHeardError(SpeechError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            "We didn't catch any words in that recording. Try again, closer to the microphone.",
            422,
        )
