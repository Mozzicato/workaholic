"""What to do about the things a job asks for and the record does not have.

Matching says a requirement is missing. That is true and useless on its own: the candidate
already knows they have never used Kubernetes. What helps is the next sentence — something
adjacent they *have* done and should say out loud, or a small thing they could build this month
that would make the claim real.

Nothing here writes a skill onto a resume. A skill goes on the resume when the person has used
it, and the way to get there is to go and use it, which is what this tells them to do.
"""

import re
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Coaching", "ProjectIdea", "SkillGap", "coach"]


@dataclass(frozen=True, slots=True)
class SkillGap:
    """One thing the job asks for that the record does not support."""

    skill: str
    # Something they have already done that is close enough to be worth saying explicitly.
    adjacent: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectIdea:
    """Something small enough to finish, that earns one or more of the missing skills honestly."""

    title: str
    covers: tuple[str, ...]
    summary: str
    steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Coaching:
    gaps: list[SkillGap] = field(default_factory=list)
    ideas: list[ProjectIdea] = field(default_factory=list)
    # Said every time, because the temptation this feature creates is exactly the wrong one.
    caveat: str = (
        "These are not on your resume and will not be added. A skill goes on it when you have "
        "used it — build one of these, put it on GitHub, tell us, and then it goes on."
    )


# Things close enough that having one is worth mentioning when the other is asked for. Only pairs
# where the experience genuinely transfers; nothing here claims the missing skill itself.
_ADJACENT: dict[str, tuple[str, ...]] = {
    "kubernetes": ("docker", "containers", "docker compose"),
    "docker": ("linux", "deployment", "ci/cd"),
    "kafka": ("rabbitmq", "queues", "redis", "celery"),
    "aws": ("azure", "gcp", "cloud", "heroku", "render"),
    "azure": ("aws", "gcp", "cloud"),
    "gcp": ("aws", "azure", "cloud"),
    "typescript": ("javascript",),
    "javascript": ("typescript",),
    "react": ("next.js", "vue", "angular", "javascript"),
    "next.js": ("react",),
    "postgresql": ("mysql", "sql", "sqlite"),
    "mysql": ("postgresql", "sql", "sqlite"),
    "mongodb": ("nosql", "firebase"),
    "terraform": ("infrastructure as code", "cloudformation", "bicep"),
    "ci/cd": ("github actions", "gitlab ci", "jenkins"),
    "github actions": ("ci/cd",),
    "go": ("c", "java", "rust"),
    "rust": ("c", "c++", "go"),
    "graphql": ("rest", "rest apis"),
    "rest": ("graphql", "apis"),
    "django": ("flask", "fastapi", "python"),
    "fastapi": ("flask", "django", "python"),
    "spring": ("java",),
    "pytest": ("testing", "unit tests", "jest"),
    "jest": ("testing", "unit tests", "pytest"),
    "figma": ("design", "wireframes"),
    "power bi": ("excel", "tableau", "sql"),
    "tableau": ("power bi", "excel", "sql"),
}

# One finishable project per skill. Deliberately small: a thing somebody can actually complete
# beside their coursework, and honestly say they built.
_IDEAS: tuple[tuple[tuple[str, ...], ProjectIdea], ...] = (
    (
        ("docker", "kubernetes", "containers"),
        ProjectIdea(
            title="Containerise something you have already built",
            covers=("Docker", "Kubernetes"),
            summary=(
                "Take a project you have finished and make it run anywhere with one command, then "
                "run it on a small cluster."
            ),
            steps=(
                "Write a Dockerfile for it and get it running locally in a container.",
                "Add a docker-compose file so its database starts with it.",
                "Deploy it to a free Kubernetes cluster (k3s on a cheap VM, or minikube locally) "
                "with a deployment and a service.",
                "Write a short README saying how to run it. That README is what an interviewer "
                "will read.",
            ),
        ),
    ),
    (
        ("ci/cd", "github actions", "jenkins", "gitlab ci"),
        ProjectIdea(
            title="Put a pipeline on a project you already have",
            covers=("CI/CD", "GitHub Actions"),
            summary="Make your own repository run its tests and deploy itself on every push.",
            steps=(
                "Add a GitHub Actions workflow that installs, lints and runs tests on every push.",
                "Make a failing test and watch it stop the pipeline, so you know it works.",
                "Add a second job that deploys on a green build to any free host.",
            ),
        ),
    ),
    (
        ("aws", "azure", "gcp", "cloud"),
        ProjectIdea(
            title="Put one thing of yours on a cloud you have never used",
            covers=("AWS", "Azure", "GCP"),
            summary=(
                "Hosting something real teaches more than a course, and it is the part interviews "
                "ask about."
            ),
            steps=(
                "Deploy an existing project to the cloud the job names, on its free tier.",
                "Put its files in object storage and its secrets in the platform's secret store.",
                "Write down what it costs a month. Being able to answer that separates people.",
            ),
        ),
    ),
    (
        ("kafka", "rabbitmq", "queues", "event", "streaming"),
        ProjectIdea(
            title="Build something that processes a queue",
            covers=("Kafka", "Queues"),
            summary="A producer, a queue and a worker — the shape of most systems that scale.",
            steps=(
                "Write a small producer that puts jobs on a queue (Kafka or RabbitMQ, both free "
                "locally in Docker).",
                "Write a worker that consumes them and writes the result to a database.",
                "Make the worker crash halfway through and show the job is not lost.",
            ),
        ),
    ),
    (
        ("sql", "postgresql", "mysql", "database", "data"),
        ProjectIdea(
            title="Build something with real data in a real database",
            covers=("SQL", "PostgreSQL"),
            summary="Collect data you care about and answer questions with SQL, not spreadsheets.",
            steps=(
                "Pick a source you can scrape or download — prices, results, timetables.",
                "Load it into PostgreSQL with a schema you designed.",
                "Write the five queries that answer the questions you actually had, and put them "
                "in the README with their answers.",
            ),
        ),
    ),
    (
        ("react", "next.js", "frontend", "typescript", "javascript"),
        ProjectIdea(
            title="Build a small app that someone other than you uses",
            covers=("React", "TypeScript"),
            summary=(
                "One screen that solves one problem for people around you beats another tutorial "
                "clone."
            ),
            steps=(
                "Find one thing your classmates do badly by hand and build the screen for it.",
                "Write it in TypeScript, keep it to one page, deploy it on Vercel.",
                "Get ten people to use it, and write down how many did.",
            ),
        ),
    ),
    (
        ("testing", "pytest", "jest", "unit tests", "automated tests"),
        ProjectIdea(
            title="Add real tests to something you wrote before you knew how",
            covers=("Testing",),
            summary="Most juniors say they can test. Few can point at a repository that proves it.",
            steps=(
                "Take an old project and add tests for the part you are most afraid to change.",
                "Add one test that would have caught a bug you actually had.",
                "Put the test count and what they cover in the README.",
            ),
        ),
    ),
    (
        ("api", "rest", "graphql", "backend", "fastapi", "django", "flask", "node"),
        ProjectIdea(
            title="Build an API that something else consumes",
            covers=("REST APIs",),
            summary="An API with a second thing calling it is the smallest honest backend project.",
            steps=(
                "Build a small API with three or four endpoints and a database behind it.",
                "Write a script or a page that uses it, so it is not just endpoints in isolation.",
                "Document how to run it, and what each endpoint returns when things go wrong.",
            ),
        ),
    ),
)

_GENERIC = ProjectIdea(
    title="Build the smallest real thing that uses it",
    covers=(),
    summary=(
        "Anything finished, on GitHub, with a README somebody else could follow, beats a course "
        "certificate for this."
    ),
    steps=(
        "Pick a problem you actually have, small enough to finish in a fortnight.",
        "Build it using the thing the job asks for, and nothing else new.",
        "Write the README as if for the interviewer who will read it.",
    ),
)

_WORD = re.compile(r"[a-z0-9][a-z0-9+#./-]*")


def coach(missing: list[str], *, record_terms: list[str], limit: int = 3) -> Coaching:
    """What to say, and what to build, about the things this job wants and the record lacks.

    `record_terms` is everything the person has already done — skills, tools, the words in their
    own lines — so that "you have never used Kubernetes, but you have used Docker" can be said
    only when it is true.
    """
    known = {term.strip().lower() for term in record_terms if term and term.strip()}
    gaps: list[SkillGap] = []
    for requirement in missing:
        wanted = requirement.strip().lower()
        adjacent = tuple(
            near for near in _ADJACENT.get(wanted, ()) if near in known or _mentioned(near, known)
        )
        gaps.append(SkillGap(skill=requirement.strip(), adjacent=adjacent))

    ideas: list[ProjectIdea] = []
    covered: set[str] = set()
    for gap in gaps:
        wanted = gap.skill.lower()
        if wanted in covered:
            continue
        idea = _idea_for(wanted)
        if idea is None:
            continue
        if any(existing.title == idea.title for existing in ideas):
            covered.add(wanted)
            continue
        ideas.append(idea)
        covered.add(wanted)
        if len(ideas) >= limit:
            break

    if gaps and not ideas:
        ideas.append(_GENERIC)
    return Coaching(gaps=gaps, ideas=ideas[:limit])


def _idea_for(skill: str) -> ProjectIdea | None:
    for triggers, idea in _IDEAS:
        if any(trigger in skill for trigger in triggers):
            return idea
    return None


def _mentioned(term: str, known: set[str]) -> bool:
    """A term counts as known when it appears as a word in something they wrote."""
    words = set(_WORD.findall(term))
    return bool(words) and any(words <= set(_WORD.findall(entry)) for entry in known)


def record_terms(profile: Any) -> list[str]:
    """Everything this person has actually done, as plain lowercase text to match against."""
    from app.services.resume.record import items, strings, text_of

    terms: list[str] = []
    for item in items(profile.skills):
        if name := text_of(item.get("name")):
            terms.append(name)
    for section in ("experience", "projects"):
        for item in items(getattr(profile, section, None)):
            terms.extend(strings(item.get("technologies")))
            terms.extend(strings(item.get("bullets")))
            terms.extend(strings(item.get("outcomes")))
            if description := text_of(item.get("description")):
                terms.append(description)
    return terms
