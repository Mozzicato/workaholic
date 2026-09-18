"""Reading the career record.

Both documents Workaholic writes — a resume and a cover letter — are built from the same
record, so the code that reads it lives here rather than inside either one. Nothing here
calls a model or touches the database; it turns stored JSON into the sentences and names a
generated document is allowed to use.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.models.candidate import CandidateProfile, Evidence

__all__ = [
    "MAX_BULLETS",
    "SourceBullet",
    "collect_sources",
    "item_id_of",
    "items",
    "items_awaiting_confirmation",
    "profile_names",
    "skill_names",
    "strings",
    "text_of",
]

MAX_BULLETS = 60
"""A ceiling on how much wording one request may rewrite, so cost per call stays predictable."""


@dataclass(frozen=True, slots=True)
class SourceBullet:
    """A sentence from the record, and where it belongs in the document."""

    id: str
    kind: str  # "experience" | "project"
    item_id: str
    item_index: int
    bullet_index: int
    text: str
    context: str
    allowed_names: tuple[str, ...]


def collect_sources(profile: CandidateProfile, blocked_items: frozenset[str]) -> list[SourceBullet]:
    """Every sentence the user wrote, with the names its rewrite may legitimately use."""
    sources: list[SourceBullet] = []
    known_names = profile_names(profile)

    for index, item in enumerate(items(profile.experience)):
        item_id = item_id_of(item, index)
        if item_id in blocked_items:
            continue
        employer = text_of(item.get("employer")) or ""
        title = text_of(item.get("title")) or ""
        context = " at ".join(part for part in (title, employer) if part) or "a role"
        allowed = (*known_names, *strings(item.get("technologies")), employer, title)
        for position, bullet in enumerate(strings(item.get("bullets"))):
            sources.append(
                SourceBullet(
                    id=f"e{index}.b{position}",
                    kind="experience",
                    item_id=item_id,
                    item_index=index,
                    bullet_index=position,
                    text=bullet,
                    context=context,
                    allowed_names=tuple(name for name in allowed if name),
                )
            )

    for index, item in enumerate(items(profile.projects)):
        item_id = item_id_of(item, index)
        if item_id in blocked_items:
            continue
        name = text_of(item.get("name")) or "a project"
        allowed = (*known_names, *strings(item.get("technologies")), name)
        outcomes = strings(item.get("outcomes"))
        description = text_of(item.get("description"))
        texts = ([description] if description else []) + outcomes
        for position, bullet in enumerate(texts):
            sources.append(
                SourceBullet(
                    id=f"p{index}.b{position}",
                    kind="project",
                    item_id=item_id,
                    item_index=index,
                    bullet_index=position,
                    text=bullet,
                    context=name,
                    allowed_names=tuple(entry for entry in allowed if entry),
                )
            )

    return sources[:MAX_BULLETS]


def items_awaiting_confirmation(evidence: Sequence[Evidence]) -> frozenset[str]:
    """Profile items whose evidence a model proposed and the user has not confirmed (PRD §15)."""
    return frozenset(
        record.item_id for record in evidence if record.item_id and not record.status.is_factual
    )


def skill_names(profile: CandidateProfile) -> list[str]:
    return [name for item in items(profile.skills) if (name := text_of(item.get("name")))]


def profile_names(profile: CandidateProfile) -> tuple[str, ...]:
    """Names the record holds: employers, titles, schools, tools, skills, the user's own name."""
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    names: list[str] = [text_of(basics.get("full_name")) or ""]
    for item in items(profile.experience):
        names.extend([text_of(item.get("employer")) or "", text_of(item.get("title")) or ""])
        names.extend(strings(item.get("technologies")))
    for item in items(profile.projects):
        names.append(text_of(item.get("name")) or "")
        names.extend(strings(item.get("technologies")))
    for item in items(profile.education):
        names.extend(
            [
                text_of(item.get("institution")) or "",
                text_of(item.get("qualification")) or "",
                text_of(item.get("field_of_study")) or "",
            ]
        )
    for item in items(profile.certifications):
        names.extend([text_of(item.get("name")) or "", text_of(item.get("issuer")) or ""])
    names.extend(skill_names(profile))
    # Names are matched word by word, so multi-word names contribute each of their words.
    words = {word for name in names if name for word in name.split()}
    return tuple(sorted(words))


def items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for entry in value if (text := text_of(entry))]


def text_of(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def item_id_of(item: dict[str, Any], index: int) -> str:
    """Profile items carry a generated id; fall back to position for records written before that."""
    raw = item.get("id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:36]
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"item-{index}"))
