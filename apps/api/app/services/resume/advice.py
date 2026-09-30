"""What would make this record produce a better resume, said plainly.

Readiness (`app.services.resume.readiness`) answers one question: can a resume be written at all.
This answers the harder one: would the resume that comes out survive thirty seconds with a
recruiter, and if not, what exactly should this person do about it.

Every piece of advice here is deterministic and is about *their record*, never about the writing —
the writer already makes their sentences read well. What it cannot do is invent a project they
never built or a number they never measured, which is why the honest version of "make my resume
better" is a list of things to say or to go and do.

Nothing here refuses anything. Someone in a hurry can ignore all of it and still get a resume.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any

from app.services.resume.record import items, strings, text_of

__all__ = ["Advice", "Severity", "advise", "grade_reading"]


class Severity(IntEnum):
    """How much this costs them. Ordered, so the worst is dealt with first."""

    CRITICAL = 1  # a recruiter would stop reading here
    IMPORTANT = 2  # a real disadvantage against an equal candidate
    POLISH = 3  # worth doing, not urgent


class Action(StrEnum):
    """What resolves it, which decides what the page offers to do next."""

    ANSWER = "answer"  # the assistant can ask for it: they already have the answer
    EDIT = "edit"  # a field on the profile page
    REMOVE = "remove"  # something on the record is working against them
    BUILD = "build"  # there is nothing to say yet; they have to go and do it


@dataclass(frozen=True, slots=True)
class Advice:
    key: str
    severity: Severity
    action: Action
    title: str
    detail: str
    # What to do, in the imperative, concrete enough to act on without thinking.
    todo: str
    # Where it applies, when it is about one item.
    item_id: str | None = None


# Filler that says nothing about what somebody did.
_WEAK_OPENINGS = re.compile(
    r"^\s*(helped|assisted|worked on|responsible for|involved in|participated in|took part)",
    re.I,
)
_HAS_NUMBER = re.compile(r"\d")

_FIRST_CLASS_WORDS = re.compile(r"\b(first class|distinction|summa|magna)\b", re.I)
_UPPER_SECOND_WORDS = re.compile(r"\b(second class upper|upper second|2[:.]1|2-1)\b", re.I)
_LOW_CLASS_WORDS = re.compile(
    r"\b(second class lower|lower second|2[:.]2|2-2|third class|third|pass|ordinary)\b", re.I
)
_GRADE_NUMBERS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:/|out of)\s*(\d+(?:\.\d+)?)")
_PERCENTAGE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def grade_reading(grade: str) -> tuple[float | None, bool]:
    """How this grade reads to a screener: its share of the scale, and whether it is likely to hurt.

    Nigerian degrees are usually out of 5, British ones classed, American ones out of 4. Each is
    screened at its own conventional line — a 2:2, a 3.4 out of 5, a 2.9 out of 4 — below which a
    grade is worth leaving off rather than volunteering.
    """
    if _FIRST_CLASS_WORDS.search(grade) or _UPPER_SECOND_WORDS.search(grade):
        return None, False
    if _LOW_CLASS_WORDS.search(grade):
        return None, True

    match = _GRADE_NUMBERS.search(grade)
    if match:
        value, scale = float(match.group(1)), float(match.group(2))
        if scale > 0 and value <= scale:
            # Each scale is screened at its own conventional line rather than one ratio: 3.0 on
            # a four-point GPA, 3.5 out of five, 7.0 out of ten.
            cutoffs = {4.0: 3.0, 5.0: 3.5, 10.0: 7.0, 100.0: 60.0}
            cutoff = cutoffs.get(scale)
            if cutoff is not None:
                return value / scale, value < cutoff
            share = value / scale
            return share, share < 0.7
    percentage = _PERCENTAGE.search(grade)
    if percentage:
        share = float(percentage.group(1)) / 100
        return share, share < 0.6
    return None, False


def advise(profile: Any, *, target_role: str | None = None) -> list[Advice]:
    """Everything worth telling this person, worst first."""
    basics = getattr(profile, "basics", None)
    basics = basics if isinstance(basics, dict) else {}
    experience = items(profile.experience)
    projects = items(profile.projects)
    education = items(profile.education)
    skills = items(profile.skills)
    links = getattr(profile, "links", None)
    links = links if isinstance(links, dict) else {}

    found: list[Advice] = [
        *_about_work(experience, projects, target_role),
        *_about_education(education),
        *_about_skills(skills, experience, projects),
        *_about_contact(basics, links),
    ]
    return sorted(found, key=lambda advice: (advice.severity, advice.key))


def _about_work(
    experience: list[dict[str, Any]], projects: list[dict[str, Any]], target_role: str | None
) -> Iterable[Advice]:
    aimed_at = f" for {target_role}" if target_role else ""

    if not experience and not projects:
        yield Advice(
            key="nothing-done",
            severity=Severity.CRITICAL,
            action=Action.BUILD,
            title="There is nothing here to hire you for",
            detail=(
                "A resume with no job and no project gives a recruiter nothing to read. This is "
                "the one thing no amount of good writing can fix"
                f"{aimed_at}."
            ),
            todo=(
                "Build one thing and write it down here: a small tool that solves a problem you "
                "actually have, finished and on GitHub. One real project beats five tutorials."
            ),
        )
        return

    if not projects:
        yield Advice(
            key="no-projects",
            severity=Severity.IMPORTANT,
            action=Action.BUILD,
            title="You have no projects",
            detail=(
                "Two candidates with the same internship are separated by what they built on "
                "their own. It is the part of a junior resume people actually read."
            ),
            todo=(
                "Add one thing you built outside work — coursework, a side project, anything "
                "with your name on it. If you have none, build a small one and put it on GitHub."
            ),
        )

    if not experience and projects:
        yield Advice(
            key="no-experience",
            severity=Severity.POLISH,
            action=Action.EDIT,
            title="No work experience recorded",
            detail=(
                "Projects can carry an early resume, so this is not fatal. Anything paid or "
                "organised counts though: an internship, industrial training, a teaching "
                "assistant role, work for a family business."
            ),
            todo="Add any job, internship, SIWES placement or volunteer role you have had.",
        )

    for kind, entries in (("experience", experience), ("project", projects)):
        for index, item in enumerate(entries):
            item_id = str(item.get("id") or f"{kind}-{index}")
            label = _label(kind, item)
            lines = strings(item.get("bullets")) + strings(item.get("outcomes"))
            description = text_of(item.get("description"))
            if description:
                lines = [description, *lines]

            if not lines:
                yield Advice(
                    key=f"empty-{kind}-{index}",
                    severity=Severity.CRITICAL,
                    action=Action.ANSWER,
                    title=f"{label} has nothing under it",
                    detail="A heading with no lines under it reads like padding.",
                    todo=f"Say what you actually did at {label}, in your own words.",
                    item_id=item_id,
                )
                continue

            if not any(_HAS_NUMBER.search(line) for line in lines):
                yield Advice(
                    key=f"unmeasured-{kind}-{index}",
                    severity=Severity.IMPORTANT,
                    action=Action.ANSWER,
                    title=f"Nothing about {label} has a number in it",
                    detail=(
                        "Numbers are what make a line land: how many people used it, how often it "
                        "ran, how long it took before and after. You almost certainly remember one."
                    ),
                    todo=f"Answer a couple of questions about {label} and we will put it in.",
                    item_id=item_id,
                )

            weak = [line for line in lines if _WEAK_OPENINGS.match(line)]
            if weak and len(weak) == len(lines):
                yield Advice(
                    key=f"vague-{kind}-{index}",
                    severity=Severity.POLISH,
                    action=Action.ANSWER,
                    title=f"{label} reads as helping, not doing",
                    detail=(
                        'Every line starts with "helped" or "worked on". Whatever you actually '
                        "built or changed is the part worth saying."
                    ),
                    todo=f"Say what you did yourself at {label}, however small.",
                    item_id=item_id,
                )


def _about_education(education: list[dict[str, Any]]) -> Iterable[Advice]:
    for index, school in enumerate(education):
        item_id = str(school.get("id") or f"education-{index}")
        institution = text_of(school.get("institution")) or "your school"
        if not text_of(school.get("field_of_study")) and not text_of(school.get("qualification")):
            yield Advice(
                key=f"no-course-{index}",
                severity=Severity.IMPORTANT,
                action=Action.EDIT,
                title=f"{institution} has no course against it",
                detail=(
                    "For a student or graduate role this is the first thing read, and an "
                    "internship screen often filters on it."
                ),
                todo=f"Add what you study at {institution}, and the degree if you have one.",
                item_id=item_id,
            )

        grade = text_of(school.get("grade"))
        if grade:
            _, hurts = grade_reading(grade)
            if hurts:
                yield Advice(
                    key=f"low-grade-{index}",
                    severity=Severity.IMPORTANT,
                    action=Action.REMOVE,
                    title=f"Your grade ({grade}) is working against you",
                    detail=(
                        "Most graduate screens filter somewhere around a 2:1 or 3.5 out of 5. "
                        "A grade below that volunteers a reason to say no."
                    ),
                    todo=(
                        "Leave it off. Nobody is owed your grade, and a resume without one reads "
                        "as normal — your projects and experience do the work instead."
                    ),
                    item_id=item_id,
                )


def _about_skills(
    skills: list[dict[str, Any]],
    experience: list[dict[str, Any]],
    projects: list[dict[str, Any]],
) -> Iterable[Advice]:
    if len(skills) < 4:
        yield Advice(
            key="thin-skills",
            severity=Severity.IMPORTANT,
            action=Action.ANSWER,
            title="Your skills list is thin",
            detail=(
                "Skills are how most applicant-tracking systems find you at all, and how a "
                "recruiter decides in five seconds whether to keep reading."
            ),
            todo=(
                "List the languages, tools and systems you would be comfortable being asked "
                "about in an interview."
            ),
        )

    named = {name.lower() for item in skills if (name := text_of(item.get("name")))}
    used: set[str] = set()
    for item in (*experience, *projects):
        used.update(tool.lower() for tool in strings(item.get("technologies")))
    missing = sorted(tool for tool in used if tool not in named)
    if missing:
        yield Advice(
            key="tools-not-in-skills",
            severity=Severity.POLISH,
            action=Action.EDIT,
            title="Tools you have used are missing from your skills",
            detail=(
                f"You used {', '.join(missing[:6])} in your work, but a keyword search over your "
                "skills would not find it."
            ),
            todo="Add them to your skills — you have already done the work to earn them.",
        )


def _about_contact(basics: dict[str, Any], links: dict[str, Any]) -> Iterable[Advice]:
    has_link = any(text_of(links.get(name)) for name in ("github", "linkedin", "website")) or bool(
        items(links.get("other"))
    )
    if not has_link:
        yield Advice(
            key="no-links",
            severity=Severity.POLISH,
            action=Action.EDIT,
            title="No GitHub or LinkedIn on the page",
            detail=(
                "For a technical role the first thing a reader does with an interesting resume is "
                "look for the code."
            ),
            todo="Add your GitHub, and your LinkedIn if you keep it current.",
        )


def _label(kind: str, item: dict[str, Any]) -> str:
    if kind == "project":
        return text_of(item.get("name")) or "that project"
    title, employer = text_of(item.get("title")), text_of(item.get("employer"))
    if title and employer:
        return f"{title} at {employer}"
    return title or employer or "that role"
