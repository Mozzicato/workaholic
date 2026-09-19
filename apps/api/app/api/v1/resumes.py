import uuid
from typing import Any

from fastapi import APIRouter, Response, status

from app.api.deps import LLM, CurrentUser, Pdf, SessionDep
from app.core.errors import AppError, ErrorCode
from app.models.candidate import DocumentType, ResumeTemplate
from app.prompts.cover_letter import WRITE_PROMPT_VERSION
from app.schemas.candidate import (
    GenerateResumeRequest,
    ResumeCreate,
    ResumeRead,
    ResumeUpdate,
    ResumeVersionRead,
    ResumeVersionSummary,
    TailoredVersionRead,
)
from app.schemas.cover_letter import SCHEMA_VERSION as LETTER_SCHEMA_VERSION
from app.schemas.cover_letter import CoverLetterDocument
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.job import (
    AtsCategoryRead,
    AtsCheckRead,
    AtsReportRead,
    ChangeSummary,
    JobAnalysis,
    TailorRequest,
)
from app.schemas.resume_document import ResumeDocument
from app.services.candidate import CandidateProfileService, EvidenceService, ResumeService
from app.services.cover_letter import CoverLetterService, LetterBrief
from app.services.documents import pdf_text
from app.services.job import JobService, build_report
from app.services.resume import ResumeGenerationService
from app.services.resume.ats import MAX_PER_CATEGORY, assess
from app.services.resume.persistence import save_version
from app.services.resume.rendering import render_html, render_letter_html
from app.services.resume.tailoring import tailor

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
    template = payload.template or resume.template
    # A template picked while writing becomes the resume's own, so the next draft keeps it.
    resume.template = template

    if resume.document_type is DocumentType.COVER_LETTER:
        if payload.brief is None:
            raise MissingBriefError()
        letter, model = await CoverLetterService(session, llm).write(
            user=user,
            resume=resume,
            profile=profile,
            evidence=evidence,
            brief=LetterBrief(
                company=payload.brief.company,
                role=payload.brief.role,
                hiring_manager=payload.brief.hiring_manager,
                job_advert=payload.brief.job_advert,
            ),
        )
        version = await save_version(
            session,
            user=user,
            resume=resume,
            content=letter.model_dump(mode="json"),
            schema_version=LETTER_SCHEMA_VERSION,
            prompt_version=WRITE_PROMPT_VERSION,
            model=model,
            template=template,
        )
    else:
        version = await ResumeGenerationService(session, llm).generate(
            user=user,
            resume=resume,
            profile=profile,
            evidence=evidence,
            template=template,
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
    user: CurrentUser,
    session: SessionDep,
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    template: ResumeTemplate | None = None,
) -> Response:
    """The resume as HTML — the same markup the PDF is printed from.

    `template` shows the same version in another look. Nothing is rewritten: a template is
    presentation, so trying one on needs no new draft and no model.
    """
    service = ResumeService(session)
    resume = await service.get(user, resume_id)
    version = await service.get_version(user, resume_id, version_id)
    html = _render(resume.document_type, version.content, template or version.template)
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
    template: ResumeTemplate | None = None,
) -> Response:
    """The resume as a PDF, printed from the same HTML the preview shows."""
    service = ResumeService(session)
    resume = await service.get(user, resume_id)
    version = await service.get_version(user, resume_id, version_id)
    chosen = template or version.template
    content = await pdf.render(_render(resume.document_type, version.content, chosen))
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


class MissingBriefError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            "A cover letter needs the company you're applying to.",
            422,
        )


def _render(document_type: DocumentType, content: dict[str, Any], template: ResumeTemplate) -> str:
    """The right document, validated against its own schema before it is rendered."""
    if document_type is DocumentType.COVER_LETTER:
        return render_letter_html(CoverLetterDocument.model_validate(content))
    return render_html(ResumeDocument.model_validate(content), template)


@router.post(
    "/{resume_id}/versions/{version_id}/tailored",
    response_model=TailoredVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def tailor_version(
    user: CurrentUser,
    session: SessionDep,
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: TailorRequest,
) -> TailoredVersionRead:
    """Reorder an existing version to lead with what a job asks about.

    Tailoring changes emphasis only: order of roles, projects, bullets and skills. It never
    rewrites a line and never adds one, so it needs no model and cannot invent anything
    (PRD §33).
    """
    service = ResumeService(session)
    resume = await service.get(user, resume_id)
    if resume.document_type is DocumentType.COVER_LETTER:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, "Tailoring applies to resumes, not cover letters.", 422
        )
    version = await service.get_version(user, resume_id, version_id)
    job = await JobService(session).get(user, payload.job_id)
    profile = await CandidateProfileService(session).get_or_create(user)

    analysis = JobAnalysis.model_validate(job.analysis or {})
    report = build_report(job.id, analysis, profile)
    result = tailor(ResumeDocument.model_validate(version.content), analysis, report.matches)

    tailored = await save_version(
        session,
        user=user,
        resume=resume,
        content=result.document.model_dump(mode="json"),
        schema_version=version.schema_version,
        prompt_version=version.prompt_version,
        model=version.model or "",
        template=version.template,
    )
    return TailoredVersionRead(
        version=ResumeVersionRead.model_validate(tailored),
        summary=ChangeSummary(
            changed=result.changed or ["Nothing needed moving: it already leads with this job."],
            unchanged=result.unchanged,
            missing_requirements=result.missing_requirements,
        ),
    )


@router.get(
    "/{resume_id}/versions/{version_id}/ats",
    response_model=AtsReportRead,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def ats_report(
    user: CurrentUser,
    session: SessionDep,
    pdf: Pdf,
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    job_id: uuid.UUID | None = None,
    template: ResumeTemplate | None = None,
) -> AtsReportRead:
    """Check this version against deterministic ATS criteria (PRD §34, §35).

    The PDF is printed and its text read back out, because the only way to know a PDF contains
    text rather than a picture of text is to try to read it.
    """
    service = ResumeService(session)
    resume = await service.get(user, resume_id)
    if resume.document_type is DocumentType.COVER_LETTER:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, "ATS checks apply to resumes, not cover letters.", 422
        )
    version = await service.get_version(user, resume_id, version_id)
    document = ResumeDocument.model_validate(version.content)
    # Checked in the template being looked at: layout is exactly what an ATS can trip over.
    html = render_html(document, template or version.template)

    analysis = None
    if job_id is not None:
        job = await JobService(session).get(user, job_id)
        analysis = JobAnalysis.model_validate(job.analysis or {})

    try:
        printed = await pdf.render(html)
        extracted: str | None = pdf_text(printed)
    except AppError:
        # The score should still be useful when the browser is unavailable.
        extracted = None

    report = assess(document, html=html, pdf_text=extracted, analysis=analysis)
    return AtsReportRead(
        score=report.score,
        maximum=MAX_PER_CATEGORY * len(report.categories),
        categories=[
            AtsCategoryRead(
                category=category.category.value,
                score=category.score,
                maximum=category.maximum,
                explanation=category.explanation,
            )
            for category in report.categories
        ],
        checks=[
            AtsCheckRead(
                category=check.category.value,
                name=check.name,
                passed=check.passed,
                detail=check.detail,
            )
            for check in report.checks
        ],
        caveat=report.caveat,
    )
