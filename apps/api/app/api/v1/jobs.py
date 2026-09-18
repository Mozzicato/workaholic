import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, OptionalLLM, SessionDep
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.job import (
    JobAnalysis,
    JobCreate,
    JobRead,
    JobSummary,
    JobUpdate,
    MatchReport,
)
from app.services.candidate import CandidateProfileService
from app.services.job import JobService, build_report

router = APIRouter(prefix="/jobs", tags=["jobs"])

NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "No such job description for this account"}
}


@router.get("", response_model=list[JobSummary], responses=AUTH_ERROR_RESPONSES)
async def list_jobs(user: CurrentUser, session: SessionDep) -> list[JobSummary]:
    jobs = await JobService(session).list_for_user(user)
    return [JobSummary.model_validate(job) for job in jobs]


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERROR_RESPONSES,
)
async def create_job(
    user: CurrentUser, session: SessionDep, llm: OptionalLLM, payload: JobCreate
) -> JobRead:
    """Save an advert and read it into structure.

    The advert is stored exactly as pasted (PRD §31) and is treated as data throughout: it
    describes what an employer wants, never what the candidate has done.
    """
    job = await JobService(session, llm).create(user, payload)
    return JobRead.model_validate(job)


@router.get("/{job_id}", response_model=JobRead, responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND})
async def read_job(user: CurrentUser, session: SessionDep, job_id: uuid.UUID) -> JobRead:
    return JobRead.model_validate(await JobService(session).get(user, job_id))


@router.patch("/{job_id}", response_model=JobRead, responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND})
async def update_job(
    user: CurrentUser, session: SessionDep, job_id: uuid.UUID, payload: JobUpdate
) -> JobRead:
    return JobRead.model_validate(await JobService(session).update(user, job_id, payload))


@router.post(
    "/{job_id}/analysis", response_model=JobRead, responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND}
)
async def reanalyse_job(
    user: CurrentUser, session: SessionDep, llm: OptionalLLM, job_id: uuid.UUID
) -> JobRead:
    """Read the advert again, for one saved before AI was available or after a prompt change."""
    return JobRead.model_validate(await JobService(session, llm).reanalyse(user, job_id))


@router.get(
    "/{job_id}/match", response_model=MatchReport, responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND}
)
async def match_job(user: CurrentUser, session: SessionDep, job_id: uuid.UUID) -> MatchReport:
    """What the record supports for this job, and what it does not.

    Reading this changes nothing: a requirement the record cannot support stays missing until the
    user records evidence for it themselves (PRD §32).
    """
    job = await JobService(session).get(user, job_id)
    profile = await CandidateProfileService(session).get_or_create(user)
    return build_report(job.id, JobAnalysis.model_validate(job.analysis or {}), profile)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def delete_job(user: CurrentUser, session: SessionDep, job_id: uuid.UUID) -> None:
    await JobService(session).delete(user, job_id)
