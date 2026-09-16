from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.errors import AUTH_ERROR_RESPONSES
from app.schemas.user import UserRead

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserRead, responses=AUTH_ERROR_RESPONSES)
async def read_current_user(user: CurrentUser) -> UserRead:
    """The signed-in user's account. Created automatically on first sign-in."""
    return UserRead.model_validate(user)
