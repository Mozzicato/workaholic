"""AI failures, expressed in the API's error contract.

Messages are safe to show users and never include provider error text, which can echo
prompt content.
"""

from app.core.errors import AppError, ErrorCode


class AIError(AppError):
    """Base class for AI provider failures."""


class AINotConfiguredError(AIError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_NOT_CONFIGURED,
            "AI features aren't available right now.",
            503,
        )


class AIUnavailableError(AIError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_UNAVAILABLE,
            "Our writing assistant is unavailable right now. Your information is safe. "
            "Please try again shortly.",
            503,
        )


class AIBusyError(AIError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_BUSY,
            "Our writing assistant is busy. Please try again in a minute.",
            503,
        )


class AIInvalidOutputError(AIError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_INVALID_OUTPUT,
            "We couldn't produce a reliable result this time. Your information is safe. "
            "Please try again.",
            502,
        )


class AIContentFilteredError(AIError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.AI_CONTENT_FILTERED,
            "Some of this content couldn't be processed. Please rephrase it and try again.",
            422,
        )
