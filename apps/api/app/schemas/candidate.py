"""Request and response shapes for the candidate profile, evidence and resumes.

Every section is strongly typed and size-bounded: JSONB storage must not become a dumping
ground, and unbounded payloads are a denial-of-service vector. Unknown fields are rejected
so typos surface immediately instead of being silently stored.
"""

import re
import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.candidate import (
    DocumentType,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
    ResumeStatus,
)

# "2024" or "2024-09". Day precision is noise on a resume.
_MONTH_PATTERN = re.compile(r"^\d{4}(-(0[1-9]|1[0-2]))?$")

ShortText = Annotated[str, Field(min_length=1, max_length=120)]
MediumText = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(min_length=1, max_length=2000)]
Bullet = Annotated[str, Field(min_length=1, max_length=500)]


class CandidateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileItem(CandidateModel):
    """Items carry a stable id so evidence can reference them across edits."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=36)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class DatedItem(ProfileItem):
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _check_month(cls, value: str | None) -> str | None:
        if value is not None and not _MONTH_PATTERN.match(value):
            raise ValueError("use YYYY or YYYY-MM")
        return value

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class Link(CandidateModel):
    label: ShortText
    url: HttpUrl


class Basics(CandidateModel):
    full_name: ShortText | None = None
    headline: MediumText | None = None
    email: Annotated[str, Field(max_length=320)] | None = None
    phone: Annotated[str, Field(max_length=40)] | None = None
    location: ShortText | None = None
    summary: LongText | None = None


class Links(CandidateModel):
    website: HttpUrl | None = None
    github: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    other: list[Link] = Field(default_factory=list, max_length=10)


class ExperienceItem(DatedItem):
    employer: ShortText
    title: ShortText
    location: ShortText | None = None
    is_current: bool = False
    bullets: list[Bullet] = Field(default_factory=list, max_length=20)
    technologies: list[ShortText] = Field(default_factory=list, max_length=40)


class EducationItem(DatedItem):
    institution: ShortText
    qualification: ShortText
    field_of_study: ShortText | None = None
    grade: ShortText | None = None


class ProjectItem(DatedItem):
    name: ShortText
    description: LongText | None = None
    url: HttpUrl | None = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=40)
    outcomes: list[Bullet] = Field(default_factory=list, max_length=20)


class SkillItem(ProfileItem):
    name: ShortText
    category: ShortText | None = None


class AchievementItem(DatedItem):
    description: Bullet


class CertificationItem(DatedItem):
    name: ShortText
    issuer: ShortText | None = None
    credential_url: HttpUrl | None = None


class LanguageItem(ProfileItem):
    name: ShortText
    proficiency: ShortText | None = None


class CandidateProfileRead(CandidateModel):
    id: uuid.UUID
    basics: Basics
    links: Links
    experience: list[ExperienceItem]
    education: list[EducationItem]
    projects: list[ProjectItem]
    skills: list[SkillItem]
    achievements: list[AchievementItem]
    certifications: list[CertificationItem]
    languages: list[LanguageItem]
    updated_at: datetime


class CandidateProfileUpdate(CandidateModel):
    """Partial update: only the sections present are replaced."""

    basics: Basics | None = None
    links: Links | None = None
    experience: list[ExperienceItem] | None = Field(default=None, max_length=50)
    education: list[EducationItem] | None = Field(default=None, max_length=30)
    projects: list[ProjectItem] | None = Field(default=None, max_length=50)
    skills: list[SkillItem] | None = Field(default=None, max_length=150)
    achievements: list[AchievementItem] | None = Field(default=None, max_length=50)
    certifications: list[CertificationItem] | None = Field(default=None, max_length=30)
    languages: list[LanguageItem] | None = Field(default=None, max_length=20)

    def sections(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True, exclude_none=True, mode="json")


# ── Evidence ─────────────────────────────────────────────────────────────────


class EvidenceCreate(CandidateModel):
    claim: LongText
    source: EvidenceSource = EvidenceSource.USER_INPUT
    source_reference: Annotated[str, Field(max_length=255)] | None = None
    section: ProfileSection | None = None
    item_id: Annotated[str, Field(max_length=36)] | None = None


class EvidenceRead(CandidateModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    claim: str
    status: EvidenceStatus
    source: EvidenceSource
    source_reference: str | None
    section: ProfileSection | None
    item_id: str | None
    created_at: datetime
    confirmed_at: datetime | None

    @property
    def is_factual(self) -> bool:
        return self.status.is_factual


# ── Resumes ──────────────────────────────────────────────────────────────────


class ResumeCreate(CandidateModel):
    title: ShortText
    target_role: ShortText | None = None
    document_type: DocumentType = DocumentType.RESUME


class ResumeUpdate(CandidateModel):
    title: ShortText | None = None
    target_role: ShortText | None = None


class ResumeRead(CandidateModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str
    target_role: str | None
    document_type: DocumentType
    status: ResumeStatus
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
