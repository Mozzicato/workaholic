from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Identity proven by a verified access token.

    `subject` is the identity provider's stable user ID. It is the only field that
    establishes identity; everything else is descriptive.
    """

    subject: str
    provider: str
    email: str | None
    name: str | None


class AuthProvider(Protocol):
    """Verifies access tokens issued by the external identity provider.

    Business logic depends on this interface, not on a vendor SDK, so the identity
    provider can be replaced without touching the rest of the application.
    """

    async def verify_access_token(self, token: str) -> AuthenticatedPrincipal:
        """Return the principal for a valid token.

        Raises `UnauthenticatedError` / `SessionExpiredError` for bad tokens and
        `AuthProviderUnavailableError` when verification keys cannot be fetched.
        """
        ...

    async def aclose(self) -> None: ...
