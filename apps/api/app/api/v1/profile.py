from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.candidate import (
    CandidateProfileRead,
    CandidateProfileUpdate,
    ProfileReadinessRead,
    ReadinessItemRead,
)
from app.schemas.errors import AUTH_ERROR_RESPONSES
from app.services.candidate import CandidateProfileService
from app.services.resume.readiness import DocumentKind, assess_readiness

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


@router.get("/readiness", response_model=ProfileReadinessRead, responses=AUTH_ERROR_RESPONSES)
async def read_readiness(user: CurrentUser, session: SessionDep) -> ProfileReadinessRead:
    """What the record still needs before a resume or cover letter can be written from it."""
    profile = await CandidateProfileService(session).get_or_create(user)
    resume = assess_readiness(profile, DocumentKind.RESUME)
    letter = assess_readiness(profile, DocumentKind.COVER_LETTER)
    return ProfileReadinessRead(
        resume_ready=resume.ready,
        cover_letter_ready=letter.ready,
        items=[
            ReadinessItemRead(key=item.key, label=item.label, done=item.done, hint=item.hint)
            for item in resume.items
        ],
    )
