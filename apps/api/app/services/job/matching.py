"""Comparing a job's requirements against evidence in the record (PRD §32).

This is deterministic on purpose. A model asked "does this candidate meet the requirement?" will
find a way to say yes, and the answer that matters here is the honest one: a requirement is met
only where the record actually shows it.

Three states, and the difference between them is where the evidence sits:

* **MATCHED** — the candidate listed it as a skill, or named it as a tool on a role or project.
* **PARTIALLY_MATCHED** — it appears in something they wrote about what they did, but they never
  claimed it as a skill. Worth surfacing; not worth claiming for them.
* **NOT_FOUND** — the record does not mention it.

Nothing here writes anything. A missing skill stays missing until the user provides evidence for
it themselves, which is the rule in PRD §32.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Any

from app.schemas.job import JobAnalysis, MatchReport, MatchState, RequirementMatch
from app.services.resume.record import items, skill_names, strings, text_of

__all__ = ["match_requirements"]

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9+#.]*")

# Written differently by different people, meaning the same thing. Deliberately short: a wrong
# equivalence here would claim a skill the candidate does not have.
_ALIASES: dict[str, set[str]] = {
    "postgresql": {"postgres", "psql"},
    "javascript": {"js"},
    "typescript": {"ts"},
    "python": {"python3"},
    "kubernetes": {"k8s"},
    "amazon web services": {"aws"},
    "continuous integration": {"ci"},
    "github actions": {"actions"},
    "node.js": {"node", "nodejs"},
    "next.js": {"next", "nextjs"},
    "rest": {"restful"},
}


def match_requirements(analysis: JobAnalysis, profile: Any) -> list[RequirementMatch]:
    """One verdict per required and preferred skill, in the order the advert lists them."""
    claimed = _claimed_skills(profile)
    described = _described_work(profile)

    matches: list[RequirementMatch] = []
    seen: set[str] = set()
    for kind, requirements in (
        ("required", analysis.required_skills),
        ("preferred", analysis.preferred_skills),
    ):
        for requirement in requirements:
            key = requirement.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            matches.append(_verdict(requirement, kind, claimed, described))
    return matches


def build_report(job_id: Any, analysis: JobAnalysis, profile: Any) -> MatchReport:
    matches = match_requirements(analysis, profile)
    return MatchReport(
        job_id=job_id,
        matches=matches,
        matched=sum(1 for item in matches if item.state is MatchState.MATCHED),
        partially_matched=sum(1 for item in matches if item.state is MatchState.PARTIALLY_MATCHED),
        not_found=sum(1 for item in matches if item.state is MatchState.NOT_FOUND),
    )


def _verdict(
    requirement: str,
    kind: str,
    claimed: dict[str, str],
    described: list[tuple[str, str]],
) -> RequirementMatch:
    names = _names_for(requirement)

    for name in names:
        if name in claimed:
            return RequirementMatch(
                requirement=requirement,
                state=MatchState.MATCHED,
                kind=kind,
                evidence=[claimed[name]],
                explanation="You list this as a skill or a tool you used.",
            )

    mentions = [
        sentence for label, sentence in described if any(_mentions(sentence, n) for n in names)
    ][:3]
    if mentions:
        return RequirementMatch(
            requirement=requirement,
            state=MatchState.PARTIALLY_MATCHED,
            kind=kind,
            evidence=mentions,
            explanation=(
                "You mention this in what you did, but haven't listed it as a skill. Add it to "
                "your record if you can back it up."
            ),
        )

    return RequirementMatch(
        requirement=requirement,
        state=MatchState.NOT_FOUND,
        kind=kind,
        evidence=[],
        explanation="Your record doesn't mention this. Nothing will be added for you.",
    )


def _claimed_skills(profile: Any) -> dict[str, str]:
    """Skills and tools the candidate has explicitly claimed, mapped to how they wrote them."""
    claimed: dict[str, str] = {}

    def remember(value: str) -> None:
        for name in _names_for(value):
            claimed.setdefault(name, value)

    for name in skill_names(profile):
        remember(name)
    for section in ("experience", "projects"):
        for item in items(getattr(profile, section, None)):
            for technology in strings(item.get("technologies")):
                remember(technology)
    return claimed


def _described_work(profile: Any) -> list[tuple[str, str]]:
    """Sentences the candidate wrote about what they did."""
    described: list[tuple[str, str]] = []
    for section in ("experience", "projects"):
        for item in items(getattr(profile, section, None)):
            label = text_of(item.get("employer")) or text_of(item.get("name")) or section
            for field in ("bullets", "outcomes"):
                described.extend((label, sentence) for sentence in strings(item.get(field)))
            description = text_of(item.get("description"))
            if description:
                described.append((label, description))
    basics = getattr(profile, "basics", None)
    if isinstance(basics, dict):
        summary = text_of(basics.get("summary"))
        if summary:
            described.append(("summary", summary))
    return described


def _names_for(value: str) -> set[str]:
    """The requirement plus the ways people write the same thing."""
    base = value.strip().lower()
    names = {base}
    names.update(_ALIASES.get(base, set()))
    for canonical, aliases in _ALIASES.items():
        if base in aliases:
            names.add(canonical)
            names.update(aliases)
    return {name for name in names if name}


def _mentions(sentence: str, name: str) -> bool:
    """Whole-word containment: "Go" must not match "Django", "R" must not match everything."""
    words = _words(sentence)
    parts = _words(name)
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0] in words
    return name in " ".join(words)


def _words(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


def requirement_keywords(analysis: JobAnalysis) -> Sequence[str]:
    """Everything the advert treats as a keyword, for coverage checks."""
    return _unique(
        [
            *analysis.required_skills,
            *analysis.preferred_skills,
            *analysis.keywords,
            *analysis.domain_terms,
        ]
    )


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(value.strip())
    return unique
