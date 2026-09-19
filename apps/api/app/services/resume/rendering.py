"""Resume JSON to HTML (PRD §21).

The renderer owns formatting, and only formatting: it adds no words and drops none. It is
deterministic — the same document and template produce the same bytes, every time — which is
what makes a rendered resume reviewable and a regression visible.
"""

import functools
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from app.models.candidate import ResumeTemplate
from app.schemas.cover_letter import CoverLetterDocument
from app.schemas.resume_document import ResumeDocument
from app.services.resume.templates import font_css, spec_for

_TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
_TEMPLATE_DIR = _TEMPLATES / "resume"
_STYLE_DIR = _TEMPLATE_DIR / "styles"
_LETTER_DIR = _TEMPLATES / "letter"

_EN_DASH = "–"  # noqa: RUF001 - a date range takes an en dash, not a hyphen

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_SECTION_TITLES = {"experience": "Experience", "education": "Education", "projects": "Projects"}


@dataclass(frozen=True, slots=True)
class _Entry:
    """One role, school or project, in the shape every entry layout reads from."""

    kind: str  # experience | education | project
    org: str | None  # employer, school, or project name
    role: str | None  # job title, or qualification and course
    place: str | None
    dates: str
    note: str | None = None  # a grade
    link: str | None = None
    bullets: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Contact:
    kind: str  # email | phone | location | link
    text: str
    href: str | None = None


def render_html(document: ResumeDocument, template: ResumeTemplate) -> str:
    """The complete, self-contained HTML for this document."""
    spec = spec_for(template)
    jinja_template = _environment().get_template("document.html")
    html = jinja_template.render(
        document=document,
        # Our own stylesheets and fonts, so they go in as markup. Everything else on the page is
        # user text and stays escaped — quotes in CSS would otherwise break every rule.
        css=Markup(_stylesheet(template)),  # noqa: S704 - repository files, never user input
        template=template.value,
        layout=spec.entry,
        header=spec.header,
        icons=spec.contact_icons,
        sidebar=spec.sidebar,
        section_order=spec.section_order,
        titles=_SECTION_TITLES,
        entries=_entries(document, short=spec.short_months),
        contacts=_contacts(document),
        month=functools.partial(format_month, short=spec.short_months),
    )
    return html if html.endswith("\n") else f"{html}\n"


def render_letter_html(document: CoverLetterDocument) -> str:
    """The complete, self-contained HTML for a cover letter.

    A letter has one layout. The resume templates differ in density and order, which a letter
    has none of, so there is nothing here for the template choice to change.
    """
    jinja_template = _environment(_LETTER_DIR).get_template("document.html")
    html = jinja_template.render(
        document=document,
        css=Markup((_LETTER_DIR / "styles" / "standard.css").read_text(encoding="utf-8")),  # noqa: S704 - a repository file
        long_date=format_long_date,
    )
    return html if html.endswith("\n") else f"{html}\n"


def format_long_date(value: str) -> str:
    """ "2026-09-18" reads as "18 September 2026"."""
    try:
        year, month, day = (int(part) for part in value.split("-"))
        return f"{day} {_MONTH_NAMES[month - 1]} {year}"
    except (ValueError, IndexError):  # pragma: no cover - the schema rejects this first
        return value


def format_month(value: str | None, *, short: bool = False) -> str:
    """ "2025-06" reads as "June 2025", or "Jun 2025" when short; a bare year stays as it is."""
    if not value:
        return ""
    if "-" not in value:
        return value
    year, month = value.split("-", 1)
    index = int(month)
    if not 1 <= index <= 12:  # pragma: no cover - the schema rejects this first
        return value
    name = _MONTH_NAMES[index - 1]
    return f"{name[:3] if short else name} {year}"


def format_range(
    start: str | None, end: str | None, is_current: bool, *, short: bool = False
) -> str:
    """The date range as a resume prints it, or whichever end of it the record holds."""
    first = format_month(start, short=short)
    last = "Present" if is_current else format_month(end, short=short)
    if first and last:
        return f"{first} {_EN_DASH} {last}"
    return first or last


def _entries(document: ResumeDocument, *, short: bool) -> dict[str, list[_Entry]]:
    return {
        "experience": [
            _Entry(
                kind="experience",
                org=role.employer,
                role=role.title,
                place=role.location,
                dates=format_range(role.start_date, role.end_date, role.is_current, short=short),
                bullets=[bullet.text for bullet in role.bullets],
                tools=list(role.technologies),
            )
            for role in document.experience
        ],
        "education": [
            _Entry(
                kind="education",
                org=school.institution,
                role=", ".join(
                    part for part in (school.qualification, school.field_of_study) if part
                )
                or None,
                place=school.location,
                dates=format_range(school.start_date, school.end_date, False, short=short),
                note=f"Grade: {school.grade}" if school.grade else None,
                bullets=list(school.details),
            )
            for school in document.education
        ],
        "projects": [
            _Entry(
                kind="project",
                org=project.name,
                role=None,
                place=None,
                dates=format_range(project.start_date, project.end_date, False, short=short),
                link=project.url,
                bullets=[bullet.text for bullet in project.bullets],
                tools=list(project.technologies),
            )
            for project in document.projects
        ],
    }


def _contacts(document: ResumeDocument) -> list[_Contact]:
    """Contact details as a reader sees them: a link prints its address, not a label.

    "github.com/ada" on paper can be typed in; "GitHub" cannot.
    """
    basics = document.basics
    contacts: list[_Contact] = []
    if basics.email:
        contacts.append(_Contact("email", basics.email, f"mailto:{basics.email}"))
    if basics.phone:
        dialable = "".join(ch for ch in basics.phone if ch.isdigit() or ch == "+")
        contacts.append(_Contact("phone", basics.phone, f"tel:{dialable}" if dialable else None))
    if basics.location:
        contacts.append(_Contact("location", basics.location))
    contacts.extend(_Contact("link", _display_url(link.url), link.url) for link in basics.links)
    return contacts


def _display_url(url: str) -> str:
    shown = url.split("://", 1)[-1]
    shown = shown.removeprefix("www.")
    return shown.rstrip("/")


@functools.cache
def _environment(directory: Path = _TEMPLATE_DIR) -> Environment:
    return Environment(
        loader=FileSystemLoader(directory),
        autoescape=select_autoescape(["html"]),  # resume content is user text, never markup
        undefined=StrictUndefined,  # a missing field must fail loudly, not render blank
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


@functools.cache
def _stylesheet(template: ResumeTemplate) -> str:
    """Embedded fonts, the shared structure, then the template's own look — in that order."""
    spec = spec_for(template)
    base = (_STYLE_DIR / "base.css").read_text(encoding="utf-8")
    own = (_STYLE_DIR / spec.stylesheet).read_text(encoding="utf-8")
    return f"{font_css(template)}\n\n{base}\n\n{own}"
