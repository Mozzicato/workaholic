"""What a job description says, and how the candidate's record measures against it."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ShortText = Annotated[str, Field(min_length=1, max_length=120)]


class JobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobAnalysis(JobModel):
    """The structured reading of an advert (PRD §31). Every list may be empty."""

    role: str = Field(default="", max_length=200)
    seniority: str = Field(default="", max_length=60)
    required_skills: list[ShortText] = Field(default_factory=list, max_length=40)
    preferred_skills: list[ShortText] = Field(default_factory=list, max_length=40)
    responsibilities: list[str] = Field(default_factory=list, max_length=30)
    qualifications: list[str] = Field(default_factory=list, max_length=20)
    keywords: list[ShortText] = Field(default_factory=list, max_length=60)
    domain_terms: list[ShortText] = Field(default_factory=list, max_length=40)
    education_requirements: list[str] = Field(default_factory=list, max_length=10)
    experience_requirements: list[str] = Field(default_factory=list, max_length=10)


class MatchState(StrEnum):
    """How well the record supports one requirement (PRD §32)."""

    MATCHED = "MATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    NOT_FOUND = "NOT_FOUND"


class RequirementMatch(JobModel):
    requirement: str
    state: MatchState
    kind: str  # "required" | "preferred"
    # Where in the record it was found, in the user's words. Empty when NOT_FOUND.
    evidence: list[str] = Field(default_factory=list, max_length=5)
    explanation: str


class MatchReport(JobModel):
    """What the record can and cannot support for this job. Nothing is added by producing it."""

    job_id: uuid.UUID
    matches: list[RequirementMatch]
    matched: int
    partially_matched: int
    not_found: int

    @property
    def missing(self) -> list[str]:
        return [item.requirement for item in self.matches if item.state is MatchState.NOT_FOUND]


class SkillGapRead(JobModel):
    """Something the job asks for that the record does not support."""

    skill: str
    adjacent: list[str]


class ProjectIdeaRead(JobModel):
    """Something small enough to finish that would earn the missing skill honestly."""

    title: str
    covers: list[str]
    summary: str
    steps: list[str]


class CoachingRead(JobModel):
    """What to do about the gap — never what to claim."""

    job_id: uuid.UUID
    gaps: list[SkillGapRead]
    ideas: list[ProjectIdeaRead]
    caveat: str


class JobCreate(JobModel):
    title: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    # A long advert is normal; a novel is not.
    raw_text: str = Field(min_length=20, max_length=20000)


class JobUpdate(JobModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)


class JobRead(JobModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str
    company: str | None
    source_url: str | None
    raw_text: str
    analysis: JobAnalysis
    analysis_model: str | None
    prompt_version: str | None
    created_at: datetime
    updated_at: datetime


class JobSummary(JobModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str
    company: str | None
    created_at: datetime
    updated_at: datetime


class TailorRequest(JobModel):
    """Tailor an existing version of this resume to a job."""

    job_id: uuid.UUID
    version_id: uuid.UUID | None = None  # defaults to the resume's current version


class ChangeSummary(JobModel):
    """What tailoring moved, and what it structurally cannot touch (PRD §33)."""

    changed: list[str]
    unchanged: list[str]
    missing_requirements: list[str]


class AtsCheckRead(JobModel):
    category: str
    name: str
    passed: bool
    detail: str


class AtsCategoryRead(JobModel):
    category: str
    score: int
    maximum: int
    explanation: str


class AtsReportRead(JobModel):
    """The Workaholic ATS Compatibility Score, its parts, and the checks behind it (PRD §35)."""

    score: int
    maximum: int
    categories: list[AtsCategoryRead]
    checks: list[AtsCheckRead]
    caveat: str
