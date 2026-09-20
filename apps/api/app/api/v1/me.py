from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, SessionDep, is_admin
from app.schemas.errors import AUTH_ERROR_RESPONSES
from app.schemas.user import UserRead
from app.services.support import SupportService

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserRead, responses=AUTH_ERROR_RESPONSES)
async def read_current_user(request: Request, user: CurrentUser) -> UserRead:
    """The signed-in user's account. Created automatically on first sign-in."""
    return UserRead.model_validate(user).model_copy(update={"is_admin": is_admin(request, user)})


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, responses=AUTH_ERROR_RESPONSES)
async def delete_current_user(user: CurrentUser, session: SessionDep) -> None:
    """Erase this account and everything in it: record, resumes, drafts, conversations, evidence.

    There is no undo, and nothing is kept back except feedback already sent, which is detached
    from the account. Signing in with the same address afterwards starts an empty account.
    """
    await SupportService(session).delete_user(user.id)
