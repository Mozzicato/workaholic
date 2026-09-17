import uuid

from fastapi import APIRouter, status

from app.api.deps import LLM, CurrentUser, SessionDep
from app.schemas.candidate import (
    GenerateResumeRequest,
    ResumeCreate,
    ResumeRead,
    ResumeUpdate,
    ResumeVersionRead,
    ResumeVersionSummary,
)
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.services.candidate import CandidateProfileService, EvidenceService, ResumeService
from app.services.resume import ResumeGenerationService

router = APIRouter(prefix="/resumes", tags=["resumes"])

NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "No such resume for this account"}
}
CONFLICT: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "A resume with that name already exists"}
}
GENERATION_ERRORS: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The record has nothing to write from, or the wording went beyond it. "
            "`details` names what needs confirming; nothing is saved either way."
        ),
    },
    503: {"model": ErrorResponse, "description": "The writing assistant is unavailable"},
}


@router.get("", response_model=list[ResumeRead], responses=AUTH_ERROR_RESPONSES)
async def list_resumes(user: CurrentUser, session: SessionDep) -> list[ResumeRead]:
    resumes = await ResumeService(session).list_for_user(user)
    return [ResumeRead.model_validate(resume) for resume in resumes]


@router.post(
    "",
    response_model=ResumeRead,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH_ERROR_RESPONSES, **CONFLICT},
)
async def create_resume(
    user: CurrentUser, session: SessionDep, payload: ResumeCreate
) -> ResumeRead:
    """Start a resume. It holds no content until generation runs against confirmed evidence."""
    resume = await ResumeService(session).create(user, payload)
    return ResumeRead.model_validate(resume)


@router.get(
    "/{resume_id}", response_model=ResumeRead, responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND}
)
async def read_resume(user: CurrentUser, session: SessionDep, resume_id: uuid.UUID) -> ResumeRead:
    return ResumeRead.model_validate(await ResumeService(session).get(user, resume_id))


@router.patch(
    "/{resume_id}",
    response_model=ResumeRead,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND, **CONFLICT},
)
async def update_resume(
    user: CurrentUser, session: SessionDep, resume_id: uuid.UUID, payload: ResumeUpdate
) -> ResumeRead:
    resume = await ResumeService(session).update(user, resume_id, payload)
    return ResumeRead.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def delete_resume(user: CurrentUser, session: SessionDep, resume_id: uuid.UUID) -> None:
    await ResumeService(session).delete(user, resume_id)


@router.post(
    "/{resume_id}/versions",
    response_model=ResumeVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND, **GENERATION_ERRORS},
)
async def generate_version(
    user: CurrentUser,
    session: SessionDep,
    llm: LLM,
    resume_id: uuid.UUID,
    payload: GenerateResumeRequest,
) -> ResumeVersionRead:
    """Write a new version of this resume from the career record.

    Synchronous by design at this stage: one request, one document, and the caller learns
    immediately if the wording could not be supported. Nothing is written unless it passes.
    """
    resume = await ResumeService(session).get(user, resume_id)
    profile = await CandidateProfileService(session).get_or_create(user)
    evidence = await EvidenceService(session).list_for_user(user)
    version = await ResumeGenerationService(session, llm).generate(
        user=user,
        resume=resume,
        profile=profile,
        evidence=evidence,
        template=payload.template,
    )
    return ResumeVersionRead.model_validate(version)


@router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeVersionSummary],
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def list_versions(
    user: CurrentUser, session: SessionDep, resume_id: uuid.UUID
) -> list[ResumeVersionSummary]:
    versions = await ResumeService(session).list_versions(user, resume_id)
    return [ResumeVersionSummary.model_validate(version) for version in versions]


@router.get(
    "/{resume_id}/versions/{version_id}",
    response_model=ResumeVersionRead,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def read_version(
    user: CurrentUser, session: SessionDep, resume_id: uuid.UUID, version_id: uuid.UUID
) -> ResumeVersionRead:
    version = await ResumeService(session).get_version(user, resume_id, version_id)
    return ResumeVersionRead.model_validate(version)
