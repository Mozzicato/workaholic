"""Request and response shapes for interviews."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.interview import InterviewRole, InterviewStatus


class InterviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InterviewStart(InterviewModel):
    resume_id: uuid.UUID | None = None
    target_role: str | None = Field(default=None, max_length=120)


class AnswerCreate(InterviewModel):
    # Long enough for a thorough answer, bounded so a body cannot be used as a payload.
    text: str = Field(min_length=1, max_length=4000)


class MessageRead(InterviewModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    sequence: int
    role: InterviewRole
    content: str
    created_at: datetime


class SessionRead(InterviewModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    resume_id: uuid.UUID | None
    target_role: str | None
    status: InterviewStatus
    questions_asked: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SessionWithTranscript(InterviewModel):
    session: SessionRead
    messages: list[MessageRead]


class TurnRead(InterviewModel):
    """What one answer produced: the reply, and what it changed in the record."""

    session: SessionRead
    reply: MessageRead
    recorded: list[str]
    #  Things the model proposed that the answer did not support. Shown so nothing is silent.
    dropped: list[str]
    completed: bool
