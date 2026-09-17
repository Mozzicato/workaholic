import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.candidate import ResumeCreate, ResumeRead, ResumeUpdate
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.services.candidate import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"])

NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "No such resume for this account"}
}
CONFLICT: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "A resume with that name already exists"}
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
