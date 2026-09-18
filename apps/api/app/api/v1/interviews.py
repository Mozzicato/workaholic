import uuid

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import CurrentUser, OptionalLLM, SessionDep, Speech
from app.schemas.errors import AUTH_ERROR_RESPONSES, ErrorResponse
from app.schemas.interview import (
    AnswerCreate,
    InterviewStart,
    MessageRead,
    SessionRead,
    SessionWithTranscript,
    TranscriptionRead,
    TurnRead,
)
from app.services.interview import InterviewService
from app.services.speech import ALLOWED_AUDIO_TYPES, MAX_AUDIO_BYTES, Audio, AudioRejectedError

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


@router.post(
    "/{interview_id}/transcriptions",
    response_model=TranscriptionRead,
    responses={
        **AUTH_ERROR_RESPONSES,
        **NOT_FOUND,
        422: {"model": ErrorResponse, "description": "The recording could not be used"},
        503: {"model": ErrorResponse, "description": "Voice is unavailable; typing still works"},
    },
)
async def transcribe_answer(
    user: CurrentUser,
    session: SessionDep,
    speech: Speech,
    interview_id: uuid.UUID,
    audio: UploadFile = File(description="A spoken answer, recorded in the browser"),
) -> TranscriptionRead:
    """Turn a recording into text for the person to check before they send it.

    The recording is held in memory, transcribed, and dropped. It is never written to disk, to
    the database or to a log, and this endpoint records nothing against the interview: only the
    answer the person actually sends is kept (PRD section 27).
    """
    # Scoped to the owner first: an interview id that is not theirs never reaches a provider.
    await InterviewService(session).get(user, interview_id)

    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise AudioRejectedError("That file type isn't supported. Record the answer again.")

    content = await audio.read()
    if not content:
        raise AudioRejectedError("That recording was empty. Try again.")
    if len(content) > MAX_AUDIO_BYTES:
        raise AudioRejectedError("That recording is too long. Keep answers under a few minutes.")

    transcription = await speech.transcribe(
        Audio(
            content=content,
            filename=audio.filename or "answer.webm",
            content_type=content_type,
        )
    )
    return TranscriptionRead(text=transcription.text)
