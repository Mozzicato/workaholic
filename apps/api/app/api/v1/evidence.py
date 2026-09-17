import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.models.candidate import EvidenceStatus
from app.schemas.candidate import EvidenceCreate, EvidenceRead
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.services.candidate import EvidenceService

router = APIRouter(prefix="/evidence", tags=["evidence"])

NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "No such evidence for this account"}
}


@router.get("", response_model=list[EvidenceRead], responses=AUTH_ERROR_RESPONSES)
async def list_evidence(
    user: CurrentUser,
    session: SessionDep,
    evidence_status: EvidenceStatus | None = Query(default=None, alias="status"),
) -> list[EvidenceRead]:
    """Everything the user has told us, and everything a model has proposed."""
    records = await EvidenceService(session).list_for_user(user, status=evidence_status)
    return [EvidenceRead.model_validate(record) for record in records]


@router.post(
    "",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERROR_RESPONSES,
)
async def add_evidence(
    user: CurrentUser, session: SessionDep, payload: EvidenceCreate
) -> EvidenceRead:
    """Record something the user stated. Their own statements count as fact immediately."""
    evidence = await EvidenceService(session).record(user, payload)
    return EvidenceRead.model_validate(evidence)


@router.post(
    "/{evidence_id}/confirm",
    response_model=EvidenceRead,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def confirm_evidence(
    user: CurrentUser, session: SessionDep, evidence_id: uuid.UUID
) -> EvidenceRead:
    """Confirm a model-proposed or unverified claim, making it usable as fact."""
    evidence = await EvidenceService(session).confirm(user, evidence_id)
    return EvidenceRead.model_validate(evidence)


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def delete_evidence(user: CurrentUser, session: SessionDep, evidence_id: uuid.UUID) -> None:
    await EvidenceService(session).delete(user, evidence_id)
