from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthenticatedError
from app.models.user import User
from app.services.ai.base import LLMProvider
from app.services.ai.errors import AINotConfiguredError
from app.services.auth.base import AuthProvider
from app.services.users import UserService

_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in request.app.state.database.session():
        yield session


def get_auth_provider(request: Request) -> AuthProvider:
    provider: AuthProvider = request.app.state.auth_provider
    return provider


def get_llm(request: Request) -> LLMProvider:
    """The configured AI provider. Endpoints that need AI fail clearly when it's disabled."""
    provider: LLMProvider | None = request.app.state.llm
    if provider is None:
        raise AINotConfiguredError()
    return provider


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    auth_provider: Annotated[AuthProvider, Depends(get_auth_provider)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """The authenticated user, derived only from a verified token.

    Identity is never taken from request bodies, query parameters or custom headers.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError()
    principal = await auth_provider.verify_access_token(credentials.credentials)
    return await UserService(session).resolve(principal)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
LLM = Annotated[LLMProvider, Depends(get_llm)]
