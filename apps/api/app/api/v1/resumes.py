import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import LLM, CurrentUser, Pdf, SessionDep
from app.schemas.candidate import (
    GenerateResumeRequest,
    ResumeCreate,
    ResumeRead,
    ResumeUpdate,
    ResumeVersionRead,
    ResumeVersionSummary,
)
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.resume_document import ResumeDocument
from app.services.candidate import CandidateProfileService, EvidenceService, ResumeService
from app.services.resume import ResumeGenerationService
from app.services.resume.rendering import render_html

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


@router.get(
    "/{resume_id}/versions/{version_id}/preview",
    response_class=Response,
    responses={
        **AUTH_ERROR_RESPONSES,
        **NOT_FOUND,
        200: {"content": {"text/html": {}}, "description": "The rendered resume"},
    },
)
async def preview_version(
    user: CurrentUser, session: SessionDep, resume_id: uuid.UUID, version_id: uuid.UUID
) -> Response:
    """The resume as HTML — the same markup the PDF is printed from."""
    version = await ResumeService(session).get_version(user, resume_id, version_id)
    html = render_html(ResumeDocument.model_validate(version.content), version.template)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        # A resume is personal: never cached by a proxy, never stored on disk by the browser.
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{resume_id}/versions/{version_id}/pdf",
    response_class=Response,
    responses={
        **AUTH_ERROR_RESPONSES,
        **NOT_FOUND,
        200: {"content": {"application/pdf": {}}, "description": "The resume as a PDF"},
        503: {"model": ErrorResponse, "description": "The renderer is unavailable"},
    },
)
async def download_version_pdf(
    user: CurrentUser,
    session: SessionDep,
    pdf: Pdf,
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
) -> Response:
    """The resume as a PDF, printed from the same HTML the preview shows."""
    service = ResumeService(session)
    resume = await service.get(user, resume_id)
    version = await service.get_version(user, resume_id, version_id)
    document = ResumeDocument.model_validate(version.content)
    content = await pdf.render(render_html(document, version.template))
    filename = _filename(resume.title, version.version_number)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _filename(title: str, version_number: int) -> str:
    """A safe ASCII filename: a header is no place for whatever the user named their resume."""
    safe = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in title.strip().replace(" ", "-")
    ).strip("-")
    return f"{(safe[:60] or 'resume')}-v{version_number}.pdf"
