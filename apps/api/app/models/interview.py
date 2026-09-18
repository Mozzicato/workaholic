"""Interview sessions and their transcripts (PRD §25).

Durable interview state lives here, in PostgreSQL. Redis may cache an active session later, but
nothing may depend on it: everything needed to resume an interview is in these two tables.

Transcripts are career history in the user's own words. They are never written to logs, and the
`source_reference` on an `Evidence` row points back to the message a claim came from, so any
line on a finished resume can be traced to the sentence the user actually said.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.candidate import _enum


class InterviewStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InterviewRole(StrEnum):
    """Who said it. Only these two: there is no hidden third voice in a transcript."""

    AGENT = "agent"
    USER = "user"


class InterviewSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One conversation that collects evidence for a candidate profile."""

    __tablename__ = "interview_sessions"
    __table_args__ = (Index("ix_interview_sessions_user_id_updated_at", "user_id", "updated_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    # An interview can be started from a resume, but it fills the profile, which outlives it.
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL")
    )
    target_role: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[InterviewStatus] = mapped_column(
        _enum(InterviewStatus, "interview_status"), default=InterviewStatus.ACTIVE, nullable=False
    )
    # Counted rather than derived: it caps how much one session may spend on model calls.
    questions_asked: Mapped[int] = mapped_column(default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InterviewMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One turn. `sequence` orders the transcript independently of clock skew."""

    __tablename__ = "interview_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_interview_messages_session_sequence"),
        Index("ix_interview_messages_session_id_sequence", "session_id", "sequence"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[InterviewRole] = mapped_column(
        _enum(InterviewRole, "interview_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # What this turn is about, so the next question can avoid ground already covered.
    topic: Mapped[str | None] = mapped_column(String(64))
