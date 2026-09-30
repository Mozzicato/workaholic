"""Request and response shapes for the candidate profile, evidence and resumes.

Every section is strongly typed and size-bounded: JSONB storage must not become a dumping
ground, and unbounded payloads are a denial-of-service vector. Unknown fields are rejected
so typos surface immediately instead of being silently stored.
"""

import re
import uuid
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.candidate import (
    DocumentType,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
    ResumeStatus,
    ResumeTemplate,
)
from app.schemas.job import ChangeSummary

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
    # Either may be unknown while an interview is still in progress; at least one must be known.
    employer: ShortText | None = None
    title: ShortText | None = None
    location: ShortText | None = None
    is_current: bool = False
    bullets: list[Bullet] = Field(default_factory=list, max_length=20)
    technologies: list[ShortText] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def check_identifiable(self) -> Self:
        if not (self.employer or self.title):
            raise ValueError("A role needs an employer or a job title")
        return self


class EducationItem(DatedItem):
    institution: ShortText
    qualification: ShortText | None = None
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
    """`start_date` is when it was issued."""

    name: ShortText
    issuer: ShortText | None = None
    credential_url: HttpUrl | None = None

    @model_validator(mode="before")
    @classmethod
    def _repair_issued_date(cls, data: Any) -> Any:
        # Interviews before 2026-09-19 stored the date as `issued_date`, which this schema does not
        # have, so reading such a profile failed outright. Read it as what it always meant.
        if isinstance(data, dict) and "issued_date" in data:
            data = dict(data)
            issued = data.pop("issued_date")
            data.setdefault("start_date", issued)
        return data


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


class ReadinessItemRead(BaseModel):
    key: str
    label: str
    done: bool
    hint: str


class ProfileReadinessRead(BaseModel):
    """What a document needs from the record, checked before anything is written."""

    resume_ready: bool
    cover_letter_ready: bool
    items: list[ReadinessItemRead]


class AdviceRead(BaseModel):
    """One thing that would make this record produce a better resume."""

    key: str
    severity: int
    action: str
    title: str
    detail: str
    todo: str
    item_id: str | None


class ProfileAdviceRead(BaseModel):
    """What to fix, worst first, and whether anything is seriously wrong."""

    items: list[AdviceRead]
    critical: int
    important: int


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
        """The sections the request actually sent, each dumped in full.

        `exclude_unset` applies all the way down, which would drop the id generated for a new
        item — and an item whose id changes on every read cannot be referenced by evidence. So
        the set of sections is decided by what was sent, and their contents are dumped complete.
        """
        sent = self.model_dump(exclude_unset=True, exclude_none=True, mode="json")
        complete = self.model_dump(exclude_none=True, mode="json")
        return {name: complete[name] for name in sent}


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
    template: ResumeTemplate = ResumeTemplate.CLASSIC


class ResumeUpdate(CandidateModel):
    title: ShortText | None = None
    target_role: ShortText | None = None
    template: ResumeTemplate | None = None


class ResumeRead(CandidateModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str
    target_role: str | None
    document_type: DocumentType
    template: ResumeTemplate
    status: ResumeStatus
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ResumeVersionRead(CandidateModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    label: str
    template: ResumeTemplate
    schema_version: str
    prompt_version: str
    model: str | None
    content: dict[str, Any]
    created_at: datetime


class ResumeVersionSummary(CandidateModel):
    """A version without its content, for listing."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    label: str
    template: ResumeTemplate
    created_at: datetime


class LetterBriefRequest(CandidateModel):
    """Who a cover letter is for. Required when the document is a cover letter."""

    company: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=120)
    hiring_manager: str | None = Field(default=None, max_length=120)
    # The advert shapes which experience leads, and never licenses a claim of its own.
    job_advert: str | None = Field(default=None, max_length=6000)


class GenerateResumeRequest(CandidateModel):
    # Omitted: the template the resume was created with. Given: used, and remembered.
    template: ResumeTemplate | None = None
    brief: LetterBriefRequest | None = None


class TailoredVersionRead(CandidateModel):
    """A tailored version, and the account of what moved."""

    version: ResumeVersionRead
    summary: "ChangeSummary"
