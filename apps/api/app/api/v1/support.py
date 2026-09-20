"""What a user sends to whoever runs Workaholic: a message, or a template to add."""

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUser, SessionDep
from app.core.errors import AppError, ErrorCode
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.support import FeedbackCreate, FeedbackRead, TemplateRequestRead
from app.services.documents.extraction import identify
from app.services.support import MAX_TEMPLATE_BYTES, SupportService

router = APIRouter(tags=["support"])


@router.post(
    "/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERROR_RESPONSES,
)
async def send_feedback(
    user: CurrentUser, session: SessionDep, payload: FeedbackCreate
) -> FeedbackRead:
    """Say something to the people who make this. It reaches an administrator, and nobody else."""
    entry = await SupportService(session).record_feedback(
        user, message=payload.message, page=payload.page, email=payload.email
    )
    return FeedbackRead.model_validate(entry)


@router.post(
    "/template-requests",
    response_model=TemplateRequestRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTH_ERROR_RESPONSES,
        422: {"model": ErrorResponse, "description": "The file could not be used"},
    },
)
async def request_a_template(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(description="A resume template, as PDF or Word"),
    note: str | None = Form(default=None, max_length=2000),
) -> TemplateRequestRead:
    """Send in a template you already have, so it can be built into Workaholic.

    The file is kept for an administrator to look at, and is never read into anyone's record.
    It is identified by its bytes, like any other upload: a name proves nothing.
    """
    content = await file.read()
    if not content:
        raise AppError(ErrorCode.VALIDATION_ERROR, "That file was empty. Try again.", 422)
    if len(content) > MAX_TEMPLATE_BYTES:
        raise AppError(ErrorCode.VALIDATION_ERROR, "That file is larger than 8 MB.", 422)
    kind = identify(content)  # refuses anything that is not a PDF or a Word file
    entry = await SupportService(session).record_template_request(
        user,
        filename=file.filename or f"template.{kind}",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        note=note,
    )
    return TemplateRequestRead.model_validate(entry)
