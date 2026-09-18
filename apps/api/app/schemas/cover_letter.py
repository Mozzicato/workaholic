"""Cover letter JSON: the validated document a cover letter version stores.

A cover letter is prose, which makes it the easiest place in this product to lie. The same rule
applies as everywhere else: the model may arrange and phrase, and every claim it makes has to be
traceable to something the candidate wrote about themselves.

The employer's advert is deliberately **not** a source of claims. It tells the letter which of
the candidate's own experience to lead with; it may never license a claim of its own, or a letter
would end up echoing the job requirements back as though the candidate had met them.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1"] = "1"

Sentence = Annotated[str, Field(min_length=1, max_length=1200)]


class LetterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class LetterSender(LetterModel):
    """The candidate, copied from their record."""

    full_name: str = Field(max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)


class LetterRecipient(LetterModel):
    """Who it is addressed to. Supplied by the candidate, so it is theirs to get right."""

    company: str = Field(min_length=1, max_length=200)
    person: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)


class LetterParagraph(LetterModel):
    """One paragraph, and the profile items its claims come from."""

    text: Sentence
    source_item_ids: list[str] = Field(default_factory=list, max_length=20)


class CoverLetterDocument(LetterModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    sender: LetterSender
    recipient: LetterRecipient
    # Written at generation, stored here, so rendering the same version twice is identical.
    written_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    salutation: str = Field(min_length=1, max_length=120)
    paragraphs: list[LetterParagraph] = Field(min_length=1, max_length=6)
    closing: str = Field(min_length=1, max_length=60)
