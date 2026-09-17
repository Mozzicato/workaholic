"""Candidate profile, evidence and resumes.

The candidate profile is the canonical career record (PRD §14). Sections are stored as
separate JSONB columns rather than one blob so each can be queried and updated on its own.

Evidence (PRD §15) records where each claim came from. Only `USER_PROVIDED` and
`USER_CONFIRMED` evidence may become a factual resume claim; `MODEL_INFERRED` and
`UNVERIFIED` must be confirmed by the user first.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EvidenceStatus(StrEnum):
    USER_PROVIDED = "USER_PROVIDED"
    USER_CONFIRMED = "USER_CONFIRMED"
    MODEL_INFERRED = "MODEL_INFERRED"
    UNVERIFIED = "UNVERIFIED"

    @property
    def is_factual(self) -> bool:
        """Whether a claim with this status may appear as fact on a resume."""
        return self in (EvidenceStatus.USER_PROVIDED, EvidenceStatus.USER_CONFIRMED)


class EvidenceSource(StrEnum):
    USER_INPUT = "user_input"
    USER_INTERVIEW = "user_interview"
    UPLOADED_DOCUMENT = "uploaded_document"
    MODEL_SUGGESTION = "model_suggestion"


class ProfileSection(StrEnum):
    BASICS = "basics"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    SKILLS = "skills"
    ACHIEVEMENTS = "achievements"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    LINKS = "links"


class DocumentType(StrEnum):
    RESUME = "resume"
    CV = "cv"


class ResumeStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    # Stored as VARCHAR with a CHECK constraint: new values need no PostgreSQL type migration.
    return Enum(
        enum_type, name=name, native_enum=False, values_callable=lambda e: [m.value for m in e]
    )


class CandidateProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One canonical career record per user."""

    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Object sections.
    basics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    links: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # List sections; every item carries its own `id` so evidence can point at it.
    education: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    experience: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    projects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    skills: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    achievements: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    certifications: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    languages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Provenance for a claim: what was said, where it came from, and how sure we are."""

    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_user_id_status", "user_id", "status"),
        Index("ix_evidence_profile_item", "candidate_profile_id", "item_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )

    claim: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EvidenceStatus] = mapped_column(
        _enum(EvidenceStatus, "evidence_status"), nullable=False
    )
    source: Mapped[EvidenceSource] = mapped_column(
        _enum(EvidenceSource, "evidence_source"), nullable=False
    )
    # Where the claim came from: an interview message, an uploaded document, a form field.
    source_reference: Mapped[str | None] = mapped_column(String(255))
    # Optional link to the profile section and item this claim supports.
    section: Mapped[ProfileSection | None] = mapped_column(_enum(ProfileSection, "profile_section"))
    item_id: Mapped[str | None] = mapped_column(String(36))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A document generated from candidate evidence — never the source of truth itself."""

    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uq_resumes_user_id_title"),
        Index("ix_resumes_user_id_updated_at", "user_id", "updated_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(120))
    document_type: Mapped[DocumentType] = mapped_column(
        _enum(DocumentType, "document_type"), default=DocumentType.RESUME, nullable=False
    )
    status: Mapped[ResumeStatus] = mapped_column(
        _enum(ResumeStatus, "resume_status"), default=ResumeStatus.DRAFT, nullable=False
    )
    # Set in Phase 3, when generation produces versions.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column()
