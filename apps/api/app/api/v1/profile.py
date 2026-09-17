from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.candidate import CandidateProfileRead, CandidateProfileUpdate
from app.schemas.errors import AUTH_ERROR_RESPONSES
from app.services.candidate import CandidateProfileService

router = APIRouter(prefix="/profile", tags=["candidate profile"])


@router.get("", response_model=CandidateProfileRead, responses=AUTH_ERROR_RESPONSES)
async def read_profile(user: CurrentUser, session: SessionDep) -> CandidateProfileRead:
    """The signed-in user's career record, created empty on first use."""
    profile = await CandidateProfileService(session).get_or_create(user)
    return CandidateProfileRead.model_validate(profile, from_attributes=True)


@router.patch("", response_model=CandidateProfileRead, responses=AUTH_ERROR_RESPONSES)
async def update_profile(
    user: CurrentUser, session: SessionDep, update: CandidateProfileUpdate
) -> CandidateProfileRead:
    """Replace the sections present in the request. Omitted sections are untouched."""
    profile = await CandidateProfileService(session).update_sections(user, update)
    return CandidateProfileRead.model_validate(profile, from_attributes=True)
