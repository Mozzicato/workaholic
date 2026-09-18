"""Job descriptions the candidate is applying against (PRD §31).

The advert is kept as the user pasted it, because they must be able to see what they applied to
(PRD §31). It is untrusted text from an outside party: it is stored, shown and analysed, and it
never licenses a claim about the candidate.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobDescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (Index("ix_job_descriptions_user_id_updated_at", "user_id", "updated_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))
    # Exactly what the user pasted. Never edited, never sent anywhere as instructions.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    # The structured reading of it (`app.schemas.job.JobAnalysis`), or empty before analysis.
    analysis: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    analysis_model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(48))
