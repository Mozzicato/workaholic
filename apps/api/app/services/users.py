from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.users import UserRepository
from app.services.auth.base import AuthenticatedPrincipal


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def resolve(self, principal: AuthenticatedPrincipal) -> User:
        """Return the account for a verified principal, creating it on first sign-in."""
        user = await self._users.get_by_auth_subject(principal.subject)
        if user is None:
            await self._users.insert_if_absent(
                auth_subject=principal.subject,
                auth_provider=principal.provider,
                email=principal.email,
                name=principal.name,
            )
            await self._session.commit()
            user = await self._users.get_by_auth_subject(principal.subject)
            if user is None:  # pragma: no cover - the row was just written
                raise RuntimeError("user provisioning failed")
            return user

        if principal.email and user.email != principal.email:
            # The identity provider owns the email address; keep our copy in sync.
            user.email = principal.email
            await self._session.commit()
        return user
