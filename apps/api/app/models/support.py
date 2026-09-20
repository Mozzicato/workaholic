"""What users send to whoever runs Workaholic: a message, or a template they would like added.

Both are written by the person on purpose, for someone to read — unlike a resume, which is
theirs alone. Neither is ever used as material for a document.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupportStatus(StrEnum):
    NEW = "new"
    DONE = "done"


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Something a user wanted to say. Shown to an administrator, and to nobody else."""

    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_status_created_at", "status", "created_at"),)

    # Kept if the account goes: the point of feedback is to act on it after someone leaves.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str | None] = mapped_column(String(320))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Which page they were on, so a complaint can be placed without asking.
    page: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[SupportStatus] = mapped_column(
        String(16),
        default=SupportStatus.NEW,
        server_default=SupportStatus.NEW.value,
        nullable=False,
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TemplateRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A template someone already has and would like Workaholic to offer.

    The file is held so an administrator can look at it and build the template by hand; it is
    never parsed into anyone's record. It is small, so it lives in the database rather than
    needing storage of its own.
    """

    __tablename__ = "template_requests"
    __table_args__ = (Index("ix_template_requests_status_created_at", "status", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str | None] = mapped_column(String(320))
    note: Mapped[str | None] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[SupportStatus] = mapped_column(
        String(16),
        default=SupportStatus.NEW,
        server_default=SupportStatus.NEW.value,
        nullable=False,
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
