"""The resume wording prompt.

The model is given the user's own sentences and asked to rewrite them, one for one. It is not
asked to write a resume: employers, titles, dates and skills are copied from the record by
`app.services.resume.generation`, and never pass through the model at all.

Version history:
  v1  First version. One-for-one bullet rewrite plus a summary, both checked against the record.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.ai.base import ChatMessage

GENERATE_PROMPT_VERSION = "resume.generate.v1"

GENERATE_SYSTEM_PROMPT = """\
You are an editor for a resume builder. You improve how a candidate's own words read. \
You never add information they did not give you.

You may: fix grammar and spelling, cut filler, tighten sentence structure, lead with the action, \
and use precise verbs.

You must not: invent or change numbers, percentages, durations, team sizes, user counts or \
revenue; name employers, clients, products, tools or technologies that are not already in the \
text you were given; claim production use, business impact, scale, awards or seniority that the \
text does not state; change what the person actually did; or add adjectives that imply results \
that are not stated.

If a sentence is vague, keep it vague and correct. A weaker true line is always better than a \
stronger invented one. Never write a placeholder such as "X%" or "N users".

Return every bullet you were given, exactly once, keyed by its id, in the same order. Keep each \
rewrite under 300 characters. Do not merge, split, drop or reorder bullets.

The summary is two or three sentences describing the candidate, drawn only from the material \
below. If the material does not support a summary, return an empty string for it.\
"""


@dataclass(frozen=True, slots=True)
class BulletInput:
    """One sentence the user wrote, with the context it belongs to."""

    id: str
    text: str
    context: str  # e.g. "Backend Engineer at Paystack" — for tone, not for copying


@dataclass(frozen=True, slots=True)
class GenerationContext:
    """Everything the model is allowed to see. Nothing else about the user is sent."""

    target_role: str | None
    headline: str | None
    summary: str | None
    bullets: Sequence[BulletInput]
    skills: Sequence[str]


def build_generate_messages(context: GenerationContext) -> list[ChatMessage]:
    payload = {
        "target_role": context.target_role,
        "headline": context.headline,
        "existing_summary": context.summary,
        "skills": list(context.skills),
        "bullets": [
            {"id": bullet.id, "context": bullet.context, "text": bullet.text}
            for bullet in context.bullets
        ],
    }
    instruction = (
        "Rewrite each bullet below in the candidate's voice, keeping every fact exactly as given."
        if context.target_role is None
        else (
            f"The candidate is applying for: {context.target_role}. Rewrite each bullet below so "
            "the relevant parts read clearly first, keeping every fact exactly as given. Do not "
            "add anything about that role that the candidate did not say."
        )
    )
    return [
        ChatMessage(role="system", content=GENERATE_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"{instruction}\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        ),
    ]


def build_retry_message(problems: Sequence[str]) -> ChatMessage:
    """Names what was added that the record does not support, and asks for a corrected pass."""
    listed = "\n".join(f"- {problem}" for problem in problems)
    return ChatMessage(
        role="user",
        content=(
            "That output added information the candidate never gave:\n"
            f"{listed}\n\n"
            "Rewrite again using only what is in the material above. Remove anything you added. "
            "Return every bullet id exactly once."
        ),
    )
