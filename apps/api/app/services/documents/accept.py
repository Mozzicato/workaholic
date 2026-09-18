"""Accepting what the user confirmed from an uploaded resume (PRD §37, final step).

The user has seen the proposal and ticked what is true. Those items join the career record, and
each one is recorded as evidence from an uploaded document, confirmed by the user — so a line on
a resume later can be traced back to "you confirmed this from the CV you uploaded".

Merging is conservative: a role, project, school or skill already in the record is not added a
second time, and a contact detail the user already filled in is never overwritten by the upload.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import (
    CandidateProfile,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
)
from app.models.user import User
from app.services.candidate import CandidateProfileService
from app.services.documents.parsing import DocumentContents

__all__ = ["AcceptResult", "accept_import"]


class AcceptResult:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.skipped: list[str] = []


async def accept_import(
    session: AsyncSession, user: User, accepted: DocumentContents
) -> tuple[CandidateProfile, AcceptResult]:
    profile = await CandidateProfileService(session).get_or_create(user)
    result = AcceptResult()
    evidence: list[tuple[ProfileSection, str, str]] = []

    basics = dict(profile.basics or {})
    for field, value in (
        ("full_name", accepted.full_name),
        ("email", accepted.email),
        ("phone", accepted.phone),
        ("location", accepted.location),
        ("headline", accepted.headline),
        ("summary", accepted.summary),
    ):
        if value and not basics.get(field):
            basics[field] = value
            result.added.append(f"{field.replace('_', ' ')}")

    experience = _copy(profile.experience)
    known_roles = {_key(item.get("employer"), item.get("title")) for item in experience}
    for role in accepted.roles:
        label = " at ".join(part for part in (role.title, role.employer) if part)
        if _key(role.employer, role.title) in known_roles:
            result.skipped.append(label)
            continue
        item_id = str(uuid.uuid4())
        experience.append(
            {
                "id": item_id,
                "employer": role.employer or None,
                "title": role.title or None,
                "start_date": role.start_date or None,
                "end_date": role.end_date or None,
                "is_current": False,
                "bullets": role.bullets,
                "technologies": role.technologies,
            }
        )
        result.added.append(label)
        evidence.append((ProfileSection.EXPERIENCE, item_id, label))
        evidence.extend((ProfileSection.EXPERIENCE, item_id, line) for line in role.bullets)

    projects = _copy(profile.projects)
    known_projects = {_key(item.get("name")) for item in projects}
    for project in accepted.projects:
        if _key(project.name) in known_projects:
            result.skipped.append(project.name)
            continue
        item_id = str(uuid.uuid4())
        projects.append(
            {
                "id": item_id,
                "name": project.name,
                "description": project.description or None,
                "technologies": project.technologies,
                "outcomes": [],
            }
        )
        result.added.append(project.name)
        evidence.append((ProfileSection.PROJECTS, item_id, project.name))

    education = _copy(profile.education)
    known_schools = {_key(item.get("institution"), item.get("qualification")) for item in education}
    for entry in accepted.education:
        if _key(entry.institution, entry.qualification) in known_schools:
            result.skipped.append(entry.institution)
            continue
        item_id = str(uuid.uuid4())
        education.append(
            {
                "id": item_id,
                "institution": entry.institution,
                "qualification": entry.qualification or None,
                "field_of_study": entry.field_of_study or None,
                "grade": entry.grade or None,
                "start_date": entry.start_date or None,
                "end_date": entry.end_date or None,
            }
        )
        result.added.append(entry.institution)
        evidence.append((ProfileSection.EDUCATION, item_id, entry.institution))

    skills = _copy(profile.skills)
    known_skills = {_key(item.get("name")) for item in skills}
    for name in accepted.skills:
        if _key(name) in known_skills:
            continue
        known_skills.add(_key(name))
        item_id = str(uuid.uuid4())
        skills.append({"id": item_id, "name": name})
        result.added.append(name)
        evidence.append((ProfileSection.SKILLS, item_id, name))

    # JSONB columns are replaced, not mutated in place, so the change is seen and saved.
    profile.basics = basics
    profile.experience = experience
    profile.projects = projects
    profile.education = education
    profile.skills = skills

    now = datetime.now(UTC)
    for section, item_id, claim in evidence:
        session.add(
            Evidence(
                user_id=user.id,
                candidate_profile_id=profile.id,
                claim=claim[:2000],
                # The document supplied it and the user confirmed it: factual (PRD §15).
                status=EvidenceStatus.USER_CONFIRMED,
                source=EvidenceSource.UPLOADED_DOCUMENT,
                section=section,
                item_id=item_id,
                confirmed_at=now,
            )
        )

    await session.commit()
    await session.refresh(profile)
    return profile, result


def _copy(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _key(*parts: Any) -> str:
    return "|".join(str(part or "").strip().lower() for part in parts)
