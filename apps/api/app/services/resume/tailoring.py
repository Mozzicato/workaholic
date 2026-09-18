"""Tailoring a resume to a job (PRD §33).

Tailoring is emphasis, not content. The job decides what leads: which roles and projects come
first, which bullets within them come first, which skills are listed first. It cannot decide what
the resume says, because the material is the candidate's record and nothing else may enter it.

So this module never calls a model. It reorders a document that generation already produced and
already checked, and it reports what it moved. Everything it can do is therefore explainable in a
sentence, which is what PRD §33's change summary asks for.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from app.schemas.job import JobAnalysis, MatchState, RequirementMatch
from app.schemas.resume_document import (
    Bullet,
    ResumeDocument,
    ResumeExperience,
    ResumeProject,
    ResumeSkillGroup,
)
from app.services.job.matching import requirement_keywords

__all__ = ["TailoringResult", "tailor"]


@dataclass(slots=True)
class TailoringResult:
    """The tailored document, what changed, and what the job wanted that is missing."""

    document: ResumeDocument
    changed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)

    @property
    def any_change(self) -> bool:
        return bool(self.changed)


# What tailoring is structurally incapable of touching. Stated rather than implied, because the
# promise is the product: a tailored resume says the same things in a different order.
UNTOUCHED = [
    "Employers, job titles and dates",
    "Education and certifications",
    "The wording of every bullet",
    "Any number, tool or claim",
]


def tailor(
    document: ResumeDocument,
    analysis: JobAnalysis,
    matches: Sequence[RequirementMatch],
) -> TailoringResult:
    """Reorder the document so what the job asks about comes first."""
    keywords = [keyword.lower() for keyword in requirement_keywords(analysis)]
    result = TailoringResult(document=document)

    experience = _by_relevance(document.experience, keywords, _experience_text)
    projects = _by_relevance(document.projects, keywords, _project_text)
    skills = _skills_first(document.skills, keywords)

    experience = [_lead_in_role(role, keywords, result) for role in experience]
    projects = [_lead_in_project(project, keywords, result) for project in projects]

    if [role.item_id for role in experience] != [role.item_id for role in document.experience]:
        result.changed.append("Reordered your roles so the most relevant comes first")
    if [item.item_id for item in projects] != [item.item_id for item in document.projects]:
        result.changed.append("Reordered your projects so the most relevant comes first")
    if [group.skills for group in skills] != [group.skills for group in document.skills]:
        result.changed.append("Moved the skills this job asks for to the front")

    result.document = document.model_copy(
        update={"experience": experience, "projects": projects, "skills": skills}
    )
    result.unchanged = list(UNTOUCHED)
    result.missing_requirements = [
        match.requirement for match in matches if match.state is MatchState.NOT_FOUND
    ]
    return result


def _lead_in_role(
    role: ResumeExperience, keywords: Sequence[str], result: TailoringResult
) -> ResumeExperience:
    ordered = _relevant_bullets(role.bullets, keywords)
    if ordered is None:
        return role
    _note_reorder(result, role.employer or role.title or "")
    return role.model_copy(update={"bullets": ordered})


def _lead_in_project(
    project: ResumeProject, keywords: Sequence[str], result: TailoringResult
) -> ResumeProject:
    ordered = _relevant_bullets(project.bullets, keywords)
    if ordered is None:
        return project
    _note_reorder(result, project.name)
    return project.model_copy(update={"bullets": ordered})


def _relevant_bullets(bullets: Sequence[Bullet], keywords: Sequence[str]) -> list[Bullet] | None:
    """The bullets that answer the job first, or None when the order is already right."""
    if len(bullets) < 2:
        return None
    ordered = _by_relevance(bullets, keywords, _bullet_text)
    if [bullet.text for bullet in ordered] == [bullet.text for bullet in bullets]:
        return None
    return ordered


def _note_reorder(result: TailoringResult, label: str) -> None:
    note = f"Led with the most relevant line under {label}" if label else "Reordered bullets"
    if note not in result.changed:
        result.changed.append(note)


def _by_relevance[T](
    items: Sequence[T], keywords: Sequence[str], text_of: Callable[[T], str]
) -> list[T]:
    """Stable sort by how many of the job's words an item already contains."""
    return sorted(items, key=lambda item: -_score(text_of(item), keywords))


def _skills_first(
    groups: Sequence[ResumeSkillGroup], keywords: Sequence[str]
) -> list[ResumeSkillGroup]:
    """Within each group, the skills the job named come first. No skill is added or removed."""
    reordered: list[ResumeSkillGroup] = []
    for group in groups:
        wanted = [skill for skill in group.skills if skill.lower() in keywords]
        rest = [skill for skill in group.skills if skill.lower() not in keywords]
        reordered.append(group.model_copy(update={"skills": [*wanted, *rest]}))
    ranked = _by_relevance(reordered, keywords, lambda group: " ".join(group.skills))
    return ranked


def _score(text: str, keywords: Sequence[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword and keyword in lowered)


def _experience_text(role: ResumeExperience) -> str:
    return " ".join(
        [
            role.title or "",
            role.employer or "",
            *(bullet.text for bullet in role.bullets),
            *role.technologies,
        ]
    )


def _project_text(project: ResumeProject) -> str:
    return " ".join(
        [project.name, *(bullet.text for bullet in project.bullets), *project.technologies]
    )


def _bullet_text(bullet: Bullet) -> str:
    return bullet.text
