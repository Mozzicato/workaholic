import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, OptionalLLM, SessionDep
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.interview import (
    AnswerCreate,
    InterviewStart,
    MessageRead,
    SessionRead,
    SessionWithTranscript,
    TurnRead,
)
from app.services.interview import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])

NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "No such interview for this account"}
}
CLOSED: dict[int | str, dict[str, object]] = {
    409: {"model": ErrorResponse, "description": "The interview has already finished"}
}


@router.post(
    "",
    response_model=SessionWithTranscript,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERROR_RESPONSES,
)
async def start_interview(
    user: CurrentUser, session: SessionDep, llm: OptionalLLM, payload: InterviewStart
) -> SessionWithTranscript:
    """Begin an interview. It opens with a question chosen from what the record is missing.

    The AI provider is optional here: without one the interview asks plain questions rather
    than failing, because collecting the record matters more than the phrasing.
    """
    service = InterviewService(session, llm)
    started = await service.start(
        user, resume_id=payload.resume_id, target_role=payload.target_role
    )
    messages = await service.transcript(user, started.id)
    return SessionWithTranscript(
        session=SessionRead.model_validate(started),
        messages=[MessageRead.model_validate(message) for message in messages],
    )


@router.get("", response_model=list[SessionRead], responses=AUTH_ERROR_RESPONSES)
async def list_interviews(user: CurrentUser, session: SessionDep) -> list[SessionRead]:
    sessions = await InterviewService(session).list_for_user(user)
    return [SessionRead.model_validate(item) for item in sessions]


@router.get(
    "/{interview_id}",
    response_model=SessionWithTranscript,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def read_interview(
    user: CurrentUser, session: SessionDep, interview_id: uuid.UUID
) -> SessionWithTranscript:
    service = InterviewService(session)
    found = await service.get(user, interview_id)
    messages = await service.transcript(user, interview_id)
    return SessionWithTranscript(
        session=SessionRead.model_validate(found),
        messages=[MessageRead.model_validate(message) for message in messages],
    )


@router.post(
    "/{interview_id}/answers",
    response_model=TurnRead,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND, **CLOSED},
)
async def answer_question(
    user: CurrentUser,
    session: SessionDep,
    llm: OptionalLLM,
    interview_id: uuid.UUID,
    payload: AnswerCreate,
) -> TurnRead:
    """Answer the last question. The answer is recorded, and the next question comes back."""
    turn = await InterviewService(session, llm).answer(user, interview_id, payload.text)
    return TurnRead(
        session=SessionRead.model_validate(turn.session),
        reply=MessageRead.model_validate(turn.reply),
        recorded=turn.recorded,
        dropped=turn.dropped,
        completed=turn.completed,
    )


@router.post(
    "/{interview_id}/abandon",
    response_model=SessionRead,
    responses={**AUTH_ERROR_RESPONSES, **NOT_FOUND},
)
async def abandon_interview(
    user: CurrentUser, session: SessionDep, interview_id: uuid.UUID
) -> SessionRead:
    """Stop an interview. Everything already recorded stays in the career record."""
    return SessionRead.model_validate(await InterviewService(session).abandon(user, interview_id))
