"""The resume templates: how each one looks, and nothing about what it says.

Every template renders the same document through the same HTML. What a template may change is
presentation only — typeface, colour, spacing, the order of sections, whether an entry's heading
sits on one line or two, and whether minor sections move to a side column. It can never add or
drop a fact, which is why one set of tests covers all of them.

Typefaces are embedded in the page itself. The PDF printer is not allowed to fetch anything, and
a container has only basic system fonts, so a template that names a font it does not carry
would print in whatever happens to be installed. Every face here is under the SIL Open Font
License or Apache 2.0; the licences sit beside the files.
"""

import base64
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.models.candidate import ResumeTemplate

__all__ = ["FontFace", "TemplateSpec", "font_css", "spec_for"]

_FONT_DIR = Path(__file__).resolve().parents[2] / "templates" / "fonts"

Header = Literal["centered", "left", "band"]
"""centered: name and contact centred. left: aligned left. band: name on a coloured band."""

EntryLayout = Literal["role-first", "org-first", "inline"]
"""
role-first: the role on the first line with dates; the organisation beneath it.
org-first:  the organisation first with its place; the role beneath it with dates (Harvard).
inline:     one line, "Role, Organisation - Place", with dates on the right.
"""


Style = Literal["normal", "italic"]


@dataclass(frozen=True, slots=True)
class FontFace:
    family: str
    file_stem: str  # e.g. "charis-sil"
    weight: int
    style: Style = "normal"


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    key: ResumeTemplate
    stylesheet: str
    fonts: tuple[FontFace, ...]
    section_order: tuple[str, ...]
    header: Header = "centered"
    entry: EntryLayout = "role-first"
    # Sections placed in a side column. Empty means a single column.
    sidebar: tuple[str, ...] = ()
    contact_icons: bool = False
    # "Jun 2025" rather than "June 2025": one-line entries need the room.
    short_months: bool = True


def _faces(family: str, stem: str, *variants: tuple[int, Style]) -> tuple[FontFace, ...]:
    return tuple(
        FontFace(family=family, file_stem=stem, weight=weight, style=style)
        for weight, style in variants
    )


_REGULAR_BOLD_ITALIC: tuple[tuple[int, Style], ...] = (
    (400, "normal"),
    (700, "normal"),
    (400, "italic"),
    (700, "italic"),
)
_SANS: tuple[tuple[int, Style], ...] = ((400, "normal"), (700, "normal"), (400, "italic"))

_SOURCE_SERIF = _faces("Source Serif 4", "source-serif-4", *_REGULAR_BOLD_ITALIC)
_CHARIS = _faces("Charis SIL", "charis-sil", *_REGULAR_BOLD_ITALIC)
_TINOS = _faces("Tinos", "tinos", *_REGULAR_BOLD_ITALIC)
_CARLITO = _faces("Carlito", "carlito", *_SANS)
_LATO = _faces("Lato", "lato", *_SANS)
_SOURCE_SANS = _faces(
    "Source Sans 3",
    "source-sans-3",
    (400, "normal"),
    (600, "normal"),
    (700, "normal"),
    (400, "italic"),
)
_INTER = _faces("Inter", "inter", (400, "normal"), (600, "normal"), (700, "normal"))

# Students lead with what they are studying; people with a career lead with the career.
_EDUCATION_FIRST = ("education", "skills", "experience", "projects", "certifications")
_EXPERIENCE_FIRST = ("experience", "projects", "education", "skills", "certifications")

_SPECS: dict[ResumeTemplate, TemplateSpec] = {
    spec.key: spec
    for spec in (
        TemplateSpec(
            key=ResumeTemplate.CLASSIC,
            stylesheet="classic.css",
            fonts=_CHARIS,
            section_order=_EDUCATION_FIRST,
            entry="inline",
        ),
        TemplateSpec(
            key=ResumeTemplate.HARVARD,
            stylesheet="harvard.css",
            fonts=_TINOS,
            section_order=("education", "experience", "projects", "skills", "certifications"),
            entry="org-first",
        ),
        TemplateSpec(
            key=ResumeTemplate.ENGINEERING,
            stylesheet="engineering.css",
            fonts=_CARLITO,
            section_order=("skills", "experience", "projects", "education", "certifications"),
            entry="inline",
        ),
        TemplateSpec(
            key=ResumeTemplate.MODERN,
            stylesheet="modern.css",
            fonts=_LATO,
            section_order=_EXPERIENCE_FIRST,
            contact_icons=True,
        ),
        TemplateSpec(
            key=ResumeTemplate.BOLD,
            stylesheet="bold.css",
            fonts=_SOURCE_SANS,
            section_order=_EDUCATION_FIRST,
            entry="org-first",
        ),
        TemplateSpec(
            key=ResumeTemplate.SIDEBAR,
            stylesheet="sidebar.css",
            fonts=_LATO,
            section_order=_EXPERIENCE_FIRST,
            header="left",
            sidebar=("education", "skills", "certifications"),
            contact_icons=True,
        ),
        TemplateSpec(
            key=ResumeTemplate.EXECUTIVE,
            stylesheet="executive.css",
            fonts=_SOURCE_SANS + _SOURCE_SERIF[1:2],
            section_order=_EXPERIENCE_FIRST,
            header="band",
        ),
        TemplateSpec(
            key=ResumeTemplate.MINIMAL,
            stylesheet="minimal.css",
            fonts=_INTER,
            section_order=_EXPERIENCE_FIRST,
            header="left",
        ),
        TemplateSpec(
            key=ResumeTemplate.STANDARD,
            short_months=False,
            stylesheet="standard.css",
            fonts=_SOURCE_SERIF,
            header="left",
            section_order=_EXPERIENCE_FIRST,
        ),
        TemplateSpec(
            key=ResumeTemplate.COMPACT,
            short_months=False,
            stylesheet="compact.css",
            fonts=_INTER,
            section_order=("experience", "projects", "skills", "education", "certifications"),
            header="left",
        ),
        TemplateSpec(
            key=ResumeTemplate.ACADEMIC,
            short_months=False,
            stylesheet="academic.css",
            fonts=_SOURCE_SERIF,
            header="left",
            section_order=("education", "experience", "projects", "skills", "certifications"),
        ),
    )
}


def spec_for(template: ResumeTemplate) -> TemplateSpec:
    return _SPECS[template]


@functools.cache
def font_css(template: ResumeTemplate) -> str:
    """@font-face rules with the font files inlined, so the page needs nothing from outside."""
    rules = []
    for face in _SPECS[template].fonts:
        path = _FONT_DIR / f"{face.file_stem}-{face.weight}-{face.style}.woff2"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            "@font-face {\n"
            f'  font-family: "{face.family}";\n'
            f"  font-weight: {face.weight};\n"
            f"  font-style: {face.style};\n"
            f'  src: url("data:font/woff2;base64,{encoded}") format("woff2");\n'
            "}"
        )
    return "\n".join(rules)
