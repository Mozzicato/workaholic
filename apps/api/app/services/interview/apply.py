"""Writing an answer's facts into the career record.

Everything here works on the profile's plain JSON sections. Items keep the ids they already have,
so evidence recorded against an item in an earlier turn still points at the same thing, and a
follow-up answer adds to a role rather than creating a second copy of it.
"""

import uuid
from typing import Any

from app.services.interview.extraction import GroundedFacts
from app.services.interview.gaps import Gap, Topic

__all__ = ["Applied", "apply_basics", "apply_facts"]


class Applied:
    """What changed, in words a person can read back."""

    def __init__(self) -> None:
        self.notes: list[str] = []
        self.item_id: str | None = None

    def note(self, text: str) -> None:
        self.notes.append(text)

    @property
    def changed(self) -> bool:
        return bool(self.notes)


_BASICS_LABELS = (
    ("full_name", "name"),
    ("email", "email"),
    ("phone", "phone"),
    ("location", "location"),
)


def apply_basics(basics: dict[str, Any], facts: GroundedFacts) -> list[str]:
    """Fill in name and contact details the record does not have yet.

    Only empty fields are filled. A name or address the person typed themselves is theirs, and a
    passing mention in an answer — "my old email was..." — must never replace it.
    """
    notes: list[str] = []
    for key, label in _BASICS_LABELS:
        value: str = getattr(facts, key)
        if not value or _text(basics.get(key)):
            continue
        basics[key] = _title_if_flat(value) if key in ("full_name", "location") else value
        notes.append(f"{label}: {basics[key]}")
    return notes


def apply_facts(
    sections: dict[str, list[dict[str, Any]]], facts: GroundedFacts, gap: Gap
) -> Applied:
    """Merge `facts` into the profile sections, guided by what the question was about.

    `sections` is modified in place and holds plain dictionaries — the same shape the profile
    stores. The gap decides where an answer belongs: a reply about what someone did at a job goes
    onto that job, not into a new one.
    """
    applied = Applied()
    experience = sections.setdefault("experience", [])
    projects = sections.setdefault("projects", [])

    if gap.topic in (Topic.EXPERIENCE_DETAIL, Topic.EXPERIENCE_OUTCOME):
        role = _find(experience, gap.item_id)
        if role is not None:
            said = (
                facts.outcomes or facts.bullets
                if gap.topic is Topic.EXPERIENCE_OUTCOME
                else facts.bullets or facts.outcomes
            )
            _extend(role, "bullets", said, applied, "what you did")
            _extend(role, "technologies", _tools(facts.technologies), applied, "tools")
            applied.item_id = _identity(role)
            _fill_dates(role, facts, applied)
            return applied

    if gap.topic in (Topic.PROJECT_DETAIL, Topic.PROJECT_OUTCOME):
        project = _find(projects, gap.item_id)
        if project is not None:
            if facts.description and not project.get("description"):
                project["description"] = facts.description
                applied.note("what the project is")
            _extend(
                project, "outcomes", facts.outcomes or facts.bullets, applied, "what came of it"
            )
            _extend(project, "technologies", _tools(facts.technologies), applied, "tools")
            applied.item_id = _identity(project)
            return applied

    if gap.topic is Topic.GRADE:
        school = _find(sections.setdefault("education", []), gap.item_id)
        if school is not None and facts.grade and not school.get("grade"):
            school["grade"] = facts.grade
            applied.item_id = _identity(school)
            applied.note(f"grade: {facts.grade}")
            return applied

    if gap.topic is Topic.TECHNOLOGIES:
        item = _find(experience, gap.item_id) or _find(projects, gap.item_id)
        if item is not None and facts.technologies:
            _extend(item, "technologies", _tools(facts.technologies), applied, "tools")
            applied.item_id = _identity(item)
            return applied

    # A new role: either the question asked for one, or the answer plainly describes one.
    if facts.employer or facts.title:
        role = {
            "id": str(uuid.uuid4()),
            "employer": _title_if_flat(facts.employer) or None,
            "title": _title_if_flat(facts.title) or None,
            "is_current": facts.is_current,
            "start_date": facts.start_date or None,
            "end_date": facts.end_date or None,
            "bullets": _clean(facts.bullets),
            "technologies": _tools(facts.technologies),
        }
        experience.append(role)
        applied.item_id = role["id"]
        applied.note(_role_note(facts))
        return applied

    if facts.project_name:
        project = {
            "id": str(uuid.uuid4()),
            "name": _title_if_flat(facts.project_name),
            "description": facts.description or None,
            "outcomes": _clean(facts.outcomes or facts.bullets),
            "technologies": _tools(facts.technologies),
        }
        projects.append(project)
        applied.item_id = project["id"]
        applied.note(_title_if_flat(facts.project_name))
        return applied

    if gap.topic is Topic.SKILLS and facts.skills:
        skills = sections.setdefault("skills", [])
        existing = {_text(item.get("name")).lower() for item in skills}
        added = [name for name in facts.skills if name.lower() not in existing]
        skills.extend({"id": str(uuid.uuid4()), "name": name} for name in added)
        if added:
            applied.note(", ".join(added))
        return applied

    # A school is the one thing an education entry cannot be without: a course with no school
    # would be refused by the profile the next time it was read.
    if facts.institution:
        education = sections.setdefault("education", [])
        entry = {
            "id": str(uuid.uuid4()),
            "institution": _title_if_flat(facts.institution),
            "qualification": _title_if_flat(facts.qualification) or None,
            "field_of_study": _title_if_flat(facts.field_of_study) or None,
            "grade": facts.grade or None,
            "start_date": facts.start_date or None,
            "end_date": facts.end_date or None,
        }
        education.append(entry)
        applied.item_id = entry["id"]
        applied.note(
            " - ".join(part for part in (facts.qualification, facts.institution) if part)
            or facts.institution
        )
        return applied

    if facts.certification_name:
        certifications = sections.setdefault("certifications", [])
        entry = {
            "id": str(uuid.uuid4()),
            "name": facts.certification_name,
            "issued_date": facts.start_date or None,
        }
        certifications.append(entry)
        applied.item_id = entry["id"]
        applied.note(facts.certification_name)
        return applied

    # Nothing structured, but the answer said something: keep their sentence against the subject.
    if facts.bullets or facts.outcomes:
        item = _find(experience, gap.item_id) or _find(projects, gap.item_id)
        if item is not None:
            key = "outcomes" if "outcomes" in item else "bullets"
            _extend(item, key, facts.bullets or facts.outcomes, applied, "what you did")
            applied.item_id = _identity(item)
    return applied


def _tools(values: list[str]) -> list[str]:
    return _clean([_tool_name(value) for value in values])


def _role_note(facts: GroundedFacts) -> str:
    parts = (_title_if_flat(facts.title), _title_if_flat(facts.employer))
    return " at ".join(part for part in parts if part) or _title_if_flat(facts.employer)


def _find(items: list[dict[str, Any]], item_id: str | None) -> dict[str, Any] | None:
    if not item_id:
        return None
    if item_id.startswith("index-"):
        index = int(item_id.removeprefix("index-"))
        return items[index] if 0 <= index < len(items) else None
    return next((item for item in items if item.get("id") == item_id), None)


def _extend(
    item: dict[str, Any], key: str, values: list[str], applied: Applied, label: str
) -> None:
    current = item.get(key)
    existing: list[str] = (
        [text for text in current if isinstance(text, str)] if isinstance(current, list) else []
    )
    seen = {text.strip().lower() for text in existing}
    added = [text for text in _clean(values) if text.lower() not in seen]
    if not added:
        return
    item[key] = [*existing, *added]
    applied.note(f"{label}: {'; '.join(added)}")


def _fill_dates(item: dict[str, Any], facts: GroundedFacts, applied: Applied) -> None:
    if facts.start_date and not item.get("start_date"):
        item["start_date"] = facts.start_date
        applied.note(f"started {facts.start_date}")
    if facts.end_date and not item.get("end_date"):
        item["end_date"] = facts.end_date
        applied.note(f"ended {facts.end_date}")


def _clean(values: list[str]) -> list[str]:
    """Trim, drop duplicates, and keep the fuller of two sentences that say the same thing.

    A model asked for "what you did" and "what changed" often returns one as a fragment of the
    other. Storing both would put the same fact on a resume twice.
    """
    cleaned: list[str] = []
    for value in sorted(
        (value.strip() for value in values if value.strip()), key=len, reverse=True
    ):
        lowered = value.lower().rstrip(".;")
        if any(lowered in kept.lower() for kept in cleaned):
            continue
        cleaned.append(value)
    return [value for value in values if value.strip() in cleaned]


_TRAILING_CLAUSE = (" for ", " to ", " with ", " when ", " while ", " during ", " on the ")


def _tool_name(value: str) -> str:
    """ "docker for running things locally" is a sentence about Docker. Keep the tool."""
    trimmed = value.strip()
    for marker in _TRAILING_CLAUSE:
        index = trimmed.lower().find(marker)
        if index > 0:
            trimmed = trimmed[:index]
    return trimmed.strip(" ,.;")[:60]


def _title_if_flat(value: str) -> str:
    """Capitalise a name the person typed in lower case. Casing is presentation, not fact."""
    return value.title() if value and value == value.lower() else value


def _identity(item: dict[str, Any]) -> str | None:
    raw = item.get("id")
    return raw if isinstance(raw, str) else None


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
