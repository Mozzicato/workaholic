"""Resume JSON: the validated document a resume version stores (PRD §18).

Two rules shape this schema.

The first is provenance. Every bullet carries the profile item and the original bullet it was
written from, so any line on a finished resume can be traced back to something the user wrote.
A bullet with no source cannot be represented here at all.

The second is the division of labour in PRD §19 and §2.2: the model owns language, the record
owns facts. Employers, titles, dates, schools, certifications and skills are copied from the
candidate profile by `app.services.resume.generation`; the model never emits them. What the
model returns is wording — rewritten bullets and a summary — and that is checked against the
record before it reaches this schema.
"""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION: Literal["1"] = "1"
"""Bump on a breaking change to the document shape, and keep the reader for older versions."""

_MONTH_PATTERN = re.compile(r"^\d{4}(-(0[1-9]|1[0-2]))?$")

MonthString = Annotated[str, Field(pattern=_MONTH_PATTERN.pattern, max_length=7)]


class DocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class ResumeBasics(DocumentModel):
    """Contact details, copied from the profile verbatim."""

    full_name: str = Field(max_length=120)
    headline: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    links: list["ResumeLink"] = Field(default_factory=list, max_length=10)


class ResumeLink(DocumentModel):
    label: str = Field(max_length=40)
    url: str = Field(max_length=500)


class Bullet(DocumentModel):
    """One line of a resume, and the profile text it was written from."""

    text: str = Field(min_length=1, max_length=500)
    source_item_id: str = Field(min_length=1, max_length=36)
    source_bullet_index: int = Field(ge=0)


class ResumeExperience(DocumentModel):
    item_id: str = Field(min_length=1, max_length=36)
    employer: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    is_current: bool = False
    start_date: MonthString | None = None
    end_date: MonthString | None = None
    bullets: list[Bullet] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def check_dates(self) -> "ResumeExperience":
        if self.is_current and self.end_date is not None:
            raise ValueError("A current role cannot have an end date")
        if (
            self.start_date
            and self.end_date
            and _month_key(self.end_date) < _month_key(self.start_date)
        ):
            raise ValueError("end_date is before start_date")
        return self


class ResumeProject(DocumentModel):
    item_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=120)
    url: str | None = Field(default=None, max_length=500)
    start_date: MonthString | None = None
    end_date: MonthString | None = None
    bullets: list[Bullet] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=40)


class ResumeEducation(DocumentModel):
    item_id: str = Field(min_length=1, max_length=36)
    institution: str = Field(min_length=1, max_length=200)
    qualification: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    start_date: MonthString | None = None
    end_date: MonthString | None = None
    details: list[str] = Field(default_factory=list, max_length=10)


class ResumeSkillGroup(DocumentModel):
    """Skills grouped for display. Both the group and its entries come from the profile."""

    category: str | None = Field(default=None, max_length=120)
    skills: list[str] = Field(min_length=1, max_length=60)


class ResumeCertification(DocumentModel):
    item_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issued_date: MonthString | None = None


class ResumeDocument(DocumentModel):
    """A complete resume, ready to render. Nothing here may lack a source in the profile."""

    schema_version: Literal["1"] = SCHEMA_VERSION
    basics: ResumeBasics
    summary: str | None = Field(default=None, max_length=800)
    experience: list[ResumeExperience] = Field(default_factory=list, max_length=20)
    education: list[ResumeEducation] = Field(default_factory=list, max_length=10)
    projects: list[ResumeProject] = Field(default_factory=list, max_length=20)
    skills: list[ResumeSkillGroup] = Field(default_factory=list, max_length=12)
    certifications: list[ResumeCertification] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def check_not_empty(self) -> "ResumeDocument":
        if not (self.experience or self.projects or self.education):
            raise ValueError("A resume needs at least one role, project or qualification")
        return self


def _month_key(value: str) -> str:
    """Pads a bare year so "2025" and "2025-06" compare correctly."""
    return value if "-" in value else f"{value}-01"
