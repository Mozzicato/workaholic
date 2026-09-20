"""The administrator's view: how the product is being used, and what users have sent in.

Only aggregates and the messages people wrote on purpose. No resume, profile section, interview
answer or job advert is readable here, by anyone.
"""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import AdminUser, SessionDep
from app.core.errors import AppError, ErrorCode, NotFoundError
from app.models.support import SupportStatus
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.support import (
    AdminStats,
    AdminUserRead,
    FeedbackRead,
    SupportUpdate,
    TemplateRequestRead,
)
from app.services.support import SupportService

router = APIRouter(prefix="/admin", tags=["admin"])

FORBIDDEN: dict[int | str, dict[str, object]] = {
    403: {"model": ErrorResponse, "description": "Not an administrator"}
}
RESPONSES = {**AUTH_ERROR_RESPONSES, **FORBIDDEN}


@router.get("/stats", response_model=AdminStats, responses=RESPONSES)
async def read_stats(admin: AdminUser, session: SessionDep) -> AdminStats:
    """How much of the product is being used. Counts only."""
    return await SupportService(session).stats()


@router.get("/users", response_model=list[AdminUserRead], responses=RESPONSES)
async def list_users(admin: AdminUser, session: SessionDep) -> list[AdminUserRead]:
    """Accounts, newest first: how to reach someone, and how far they have got."""
    return await SupportService(session).users()


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**RESPONSES, 404: {"model": ErrorResponse, "description": "No such account"}},
)
async def delete_user(admin: AdminUser, session: SessionDep, user_id: uuid.UUID) -> None:
    """Erase an account and everything it owns. There is no undo.

    An administrator cannot delete their own account this way: losing the only administrator to
    a misplaced click would leave nobody able to run the place.
    """
    if user_id == admin.id:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "This would delete your own administrator account. Use the account page instead.",
            422,
        )
    if not await SupportService(session).delete_user(user_id):
        raise NotFoundError("We couldn't find that account.")


@router.get("/feedback", response_model=list[FeedbackRead], responses=RESPONSES)
async def list_feedback(
    admin: AdminUser, session: SessionDep, status_filter: SupportStatus | None = None
) -> list[FeedbackRead]:
    entries = await SupportService(session).feedback(status=status_filter)
    return [FeedbackRead.model_validate(entry) for entry in entries]


@router.patch("/feedback/{feedback_id}", response_model=FeedbackRead, responses=RESPONSES)
async def update_feedback(
    admin: AdminUser, session: SessionDep, feedback_id: uuid.UUID, payload: SupportUpdate
) -> FeedbackRead:
    service = SupportService(session)
    entry = await service.feedback_item(feedback_id)
    if entry is None:
        raise NotFoundError("We couldn't find that message.")
    await service.set_status(entry, payload.status)
    return FeedbackRead.model_validate(entry)


@router.get("/template-requests", response_model=list[TemplateRequestRead], responses=RESPONSES)
async def list_template_requests(
    admin: AdminUser, session: SessionDep
) -> list[TemplateRequestRead]:
    entries = await SupportService(session).template_requests()
    return [TemplateRequestRead.model_validate(entry) for entry in entries]


@router.get(
    "/template-requests/{request_id}/file",
    response_class=Response,
    responses={**RESPONSES, 200: {"content": {"application/octet-stream": {}}}},
)
async def download_template_request(
    admin: AdminUser, session: SessionDep, request_id: uuid.UUID
) -> Response:
    """The file someone sent in, to look at and build from."""
    entry = await SupportService(session).template_request(request_id)
    if entry is None:
        raise NotFoundError("We couldn't find that request.")
    safe = "".join(
        character if character.isalnum() or character in "-_." else "-"
        for character in entry.filename
    )
    return Response(
        content=entry.content,
        media_type=entry.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe[:80] or "template"}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/template-requests/{request_id}", response_model=TemplateRequestRead, responses=RESPONSES
)
async def update_template_request(
    admin: AdminUser, session: SessionDep, request_id: uuid.UUID, payload: SupportUpdate
) -> TemplateRequestRead:
    service = SupportService(session)
    entry = await service.template_request(request_id)
    if entry is None:
        raise NotFoundError("We couldn't find that request.")
    await service.set_status(entry, payload.status)
    return TemplateRequestRead.model_validate(entry)


@router.delete(
    "/template-requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=RESPONSES,
)
async def delete_template_request(
    admin: AdminUser, session: SessionDep, request_id: uuid.UUID
) -> None:
    """Delete the file once the template has been built, or if it should not have been sent."""
    service = SupportService(session)
    entry = await service.template_request(request_id)
    if entry is None:
        raise NotFoundError("We couldn't find that request.")
    await service.delete_template_request(entry)
