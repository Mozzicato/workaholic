from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.candidate import (
    AdviceRead,
    CandidateProfileRead,
    CandidateProfileUpdate,
    ProfileAdviceRead,
    ProfileReadinessRead,
    ReadinessItemRead,
)
from app.schemas.errors import AUTH_ERROR_RESPONSES
from app.services.candidate import CandidateProfileService
from app.services.resume.advice import Severity, advise
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


@router.get("/advice", response_model=ProfileAdviceRead, responses=AUTH_ERROR_RESPONSES)
async def read_advice(
    user: CurrentUser, session: SessionDep, role: str | None = None
) -> ProfileAdviceRead:
    """What would make this record produce a better resume, worst first.

    Advice, never a refusal: someone in a hurry can ignore all of it and still get a resume.
    """
    profile = await CandidateProfileService(session).get_or_create(user)
    found = advise(profile, target_role=role)
    return ProfileAdviceRead(
        items=[
            AdviceRead(
                key=item.key,
                severity=int(item.severity),
                action=str(item.action),
                title=item.title,
                detail=item.detail,
                todo=item.todo,
                item_id=item.item_id,
            )
            for item in found
        ],
        critical=sum(1 for item in found if item.severity is Severity.CRITICAL),
        important=sum(1 for item in found if item.severity is Severity.IMPORTANT),
    )
