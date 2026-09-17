"""Resume JSON to HTML (PRD §21).

The renderer owns formatting, and only formatting: it adds no words and drops none. It is
deterministic — the same document and template produce the same bytes, every time — which is
what makes a rendered resume reviewable and a regression visible.
"""

import functools
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.models.candidate import ResumeTemplate
from app.schemas.resume_document import ResumeDocument

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "resume"
_STYLE_DIR = _TEMPLATE_DIR / "styles"

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

# Education first for the academic template: for a student it is the strongest fact on the page.
_SECTION_ORDER: dict[ResumeTemplate, tuple[str, ...]] = {
    ResumeTemplate.STANDARD: ("experience", "projects", "education", "skills", "certifications"),
    ResumeTemplate.COMPACT: ("experience", "projects", "skills", "education", "certifications"),
    ResumeTemplate.ACADEMIC: ("education", "experience", "projects", "skills", "certifications"),
}


def render_html(document: ResumeDocument, template: ResumeTemplate) -> str:
    """The complete, self-contained HTML for this document."""
    jinja_template = _environment().get_template("document.html")
    html = jinja_template.render(
        document=document,
        css=_stylesheet(template),
        section_order=_SECTION_ORDER[template],
        date_range=format_range,
        month=format_month,
    )
    return html if html.endswith("\n") else f"{html}\n"


def format_month(value: str | None) -> str:
    """ "2025-06" reads as "June 2025"; a bare year stays as it is."""
    if not value:
        return ""
    if "-" not in value:
        return value
    year, month = value.split("-", 1)
    index = int(month)
    if not 1 <= index <= 12:  # pragma: no cover - the schema rejects this first
        return value
    return f"{_MONTH_NAMES[index - 1]} {year}"


def format_range(start: str | None, end: str | None, is_current: bool) -> str:
    """ "March 2024 – Present", or whichever end of it the record actually holds."""
    first = format_month(start)
    last = "Present" if is_current else format_month(end)
    if first and last:
        return f"{first} – {last}"
    return first or last


@functools.cache
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),  # resume content is user text, never markup
        undefined=StrictUndefined,  # a missing field must fail loudly, not render blank
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


@functools.cache
def _stylesheet(template: ResumeTemplate) -> str:
    return (_STYLE_DIR / f"{template.value}.css").read_text(encoding="utf-8")
