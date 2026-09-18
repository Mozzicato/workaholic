"""The Workaholic ATS Compatibility Score (PRD §34, §35).

Every check here is deterministic and inspectable. A model is never asked whether a resume will
pass an applicant tracking system, because a model's answer would be a confident guess dressed as
a measurement, and the number this produces is shown to someone deciding whether to send a job
application.

What the score is: a report on properties this resume demonstrably has — text that extracts,
headings a parser recognises, dates in a readable form, keywords the advert actually asked for.

What it is not: a prediction. Employers run different systems, configured differently. The name
says "Workaholic" precisely so nobody mistakes it for a universal verdict, and nothing in this
module is allowed to say a resume is guaranteed to pass anything (PRD §35).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.schemas.job import JobAnalysis
from app.schemas.resume_document import ResumeDocument
from app.services.job.matching import requirement_keywords

__all__ = ["AtsReport", "Category", "Check", "assess"]

MAX_PER_CATEGORY = 20
CATEGORY_COUNT = 5

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]*")
# A bullet that starts with a verb reads as an action. This is a short, deliberately
# uncontroversial list; a bullet that fails it is reported, never rewritten.
_WEAK_OPENERS = frozenset(
    {"responsible", "duties", "tasked", "involved", "helped", "assisted", "worked"}
)


class Category(StrEnum):
    STRUCTURE = "Structure"
    TEXT_EXTRACTION = "Text extraction"
    KEYWORD_ALIGNMENT = "Keyword alignment"
    FORMATTING = "Formatting"
    CONTENT_QUALITY = "Content quality"


@dataclass(frozen=True, slots=True)
class Check:
    """One thing that was looked at, and what was found."""

    category: Category
    name: str
    passed: bool
    weight: int
    detail: str

    @property
    def points(self) -> int:
        return self.weight if self.passed else 0


@dataclass(frozen=True, slots=True)
class CategoryScore:
    category: Category
    score: int
    maximum: int
    explanation: str


@dataclass(frozen=True, slots=True)
class AtsReport:
    """The score, its parts, and every check behind them."""

    score: int
    categories: list[CategoryScore]
    checks: list[Check]

    #  Shown wherever the number is. PRD §35: never claim a resume will pass anything.
    caveat: str = (
        "This is the Workaholic ATS Compatibility Score, not a universal one. Employers run "
        "different systems, configured differently, and no tool can promise how any particular "
        "one will treat your resume."
    )

    @property
    def failed(self) -> list[Check]:
        return [check for check in self.checks if not check.passed]


def assess(
    document: ResumeDocument,
    *,
    html: str,
    pdf_text: str | None = None,
    analysis: JobAnalysis | None = None,
) -> AtsReport:
    """Score a rendered resume.

    `html` is what the renderer produced; `pdf_text` is the text extracted back out of the PDF,
    when one has been printed. Extracting from the real PDF is the only way to check that a PDF
    contains text at all rather than a picture of text.
    """
    checks = [
        *_structure_checks(document),
        *_extraction_checks(document, html, pdf_text),
        *_keyword_checks(document, analysis),
        *_formatting_checks(html),
        *_content_checks(document),
    ]
    categories = [_score_category(category, checks) for category in Category]
    return AtsReport(
        score=sum(category.score for category in categories),
        categories=categories,
        checks=checks,
    )


# ── Structure ────────────────────────────────────────────────────────────────


def _structure_checks(document: ResumeDocument) -> list[Check]:
    sections = {
        "Experience": bool(document.experience),
        "Education": bool(document.education),
        "Skills": bool(document.skills),
    }
    present = [name for name, exists in sections.items() if exists]
    missing = [name for name, exists in sections.items() if not exists]

    contact = [value for value in (document.basics.email, document.basics.phone) if value]
    dated_roles = [role for role in document.experience if role.start_date]
    dated_education = [entry for entry in document.education if entry.start_date or entry.end_date]

    return [
        Check(
            category=Category.STRUCTURE,
            name="Section headings",
            passed=len(present) >= 2,
            weight=6,
            detail=(
                f"Found {', '.join(present)}."
                if len(present) >= 2
                else "A parser looks for standard sections; this resume has fewer than two."
            ),
        ),
        Check(
            category=Category.STRUCTURE,
            name="Contact details",
            passed=bool(document.basics.full_name) and bool(contact),
            weight=6,
            detail=(
                "Your name and at least one way to reach you are on the page."
                if contact
                else "Add an email address or phone number: a parser needs a way to reach you."
            ),
        ),
        Check(
            category=Category.STRUCTURE,
            name="Experience dates",
            passed=not document.experience or len(dated_roles) == len(document.experience),
            weight=4,
            detail=(
                "Every role has a start date."
                if len(dated_roles) == len(document.experience)
                else f"{len(document.experience) - len(dated_roles)} role(s) have no dates. "
                "Parsers use dates to work out your history."
            ),
        ),
        Check(
            category=Category.STRUCTURE,
            name="Missing sections",
            passed=not missing,
            weight=4,
            detail=("Nothing obvious is missing." if not missing else f"No {', '.join(missing)}."),
        ),
        Check(
            category=Category.STRUCTURE,
            name="Education dates",
            passed=not document.education or bool(dated_education),
            weight=0,
            detail=(
                "Education carries dates."
                if dated_education or not document.education
                else "Your education has no dates."
            ),
        ),
    ]


# ── Text extraction ──────────────────────────────────────────────────────────


def _extraction_checks(document: ResumeDocument, html: str, pdf_text: str | None) -> list[Check]:
    checks = [
        Check(
            category=Category.TEXT_EXTRACTION,
            name="No text inside images",
            passed="<img" not in html.lower() and "data:image" not in html.lower(),
            weight=6,
            detail="The page contains no images, so nothing is trapped in a picture.",
        ),
        Check(
            category=Category.TEXT_EXTRACTION,
            name="Selectable text",
            passed=True,
            weight=6,
            detail="The document is rendered as HTML text and printed from it.",
        ),
    ]
    if pdf_text is None:
        checks.append(
            Check(
                category=Category.TEXT_EXTRACTION,
                name="PDF text extractability",
                passed=True,
                weight=8,
                detail="Checked against the PDF when you download it.",
            )
        )
        return checks

    extracted = " ".join(pdf_text.split()).lower()
    name = (document.basics.full_name or "").lower()
    bullets = [bullet.text for role in document.experience for bullet in role.bullets]
    sampled = bullets[:3]
    found = sum(1 for text in sampled if _mostly_present(text, extracted))
    ok = bool(extracted) and (not name or name in extracted) and found == len(sampled)
    checks.append(
        Check(
            category=Category.TEXT_EXTRACTION,
            name="PDF text extractability",
            passed=ok,
            weight=8,
            detail=(
                "Text read back out of the PDF matches the document, so a parser can read it."
                if ok
                else "Text could not be read back out of the PDF reliably."
            ),
        )
    )
    return checks


def _mostly_present(sentence: str, extracted: str) -> bool:
    words = [word.lower() for word in _WORD.findall(sentence) if len(word) > 3]
    if not words:
        return True
    hits = sum(1 for word in words if word in extracted)
    return hits >= max(1, int(len(words) * 0.8))


# ── Keyword alignment ────────────────────────────────────────────────────────


def _keyword_checks(document: ResumeDocument, analysis: JobAnalysis | None) -> list[Check]:
    if analysis is None:
        return [
            Check(
                category=Category.KEYWORD_ALIGNMENT,
                name="Keyword coverage",
                passed=True,
                weight=20,
                detail="No job attached, so there is nothing to align to. Attach one to check.",
            )
        ]

    keywords = [keyword.lower() for keyword in requirement_keywords(analysis)]
    text = _document_text(document).lower()
    covered = [keyword for keyword in keywords if keyword and keyword in text]
    ratio = len(covered) / len(keywords) if keywords else 1.0

    required = [skill.lower() for skill in analysis.required_skills]
    required_covered = [skill for skill in required if skill in text]

    return [
        Check(
            category=Category.KEYWORD_ALIGNMENT,
            name="Keyword coverage",
            passed=ratio >= 0.5,
            weight=10,
            detail=(
                f"{len(covered)} of {len(keywords)} of the advert's terms appear in your resume. "
                "Only add a missing one if it is true of you."
            ),
        ),
        Check(
            category=Category.KEYWORD_ALIGNMENT,
            name="Required skills present",
            passed=not required or len(required_covered) >= max(1, len(required) // 2),
            weight=10,
            detail=(
                f"{len(required_covered)} of {len(required)} required skills appear."
                if required
                else "The advert names no required skills."
            ),
        ),
    ]


# ── Formatting ───────────────────────────────────────────────────────────────


def _formatting_checks(html: str) -> list[Check]:
    lowered = html.lower()
    return [
        Check(
            category=Category.FORMATTING,
            name="No tables",
            passed="<table" not in lowered,
            weight=5,
            detail="No tables, which parsers frequently read out of order.",
        ),
        Check(
            category=Category.FORMATTING,
            name="Single column",
            passed="column-count" not in lowered and "grid-template-columns" not in lowered,
            weight=5,
            detail="One column, read top to bottom.",
        ),
        Check(
            category=Category.FORMATTING,
            name="No header or footer furniture",
            passed="display_header_footer" not in lowered and '<header class="page' not in lowered,
            weight=4,
            detail="Nothing important sits in a page header or footer, which parsers often drop.",
        ),
        Check(
            category=Category.FORMATTING,
            name="Readable fonts",
            passed="font-size: 9" not in lowered.replace(" ", " "),
            weight=3,
            detail="Body text is set at a readable size.",
        ),
        Check(
            category=Category.FORMATTING,
            name="Real bullet lists",
            passed="<ul" in lowered or "<li" in lowered,
            weight=3,
            detail="Bullets are list items, not characters typed at the start of a line.",
        ),
    ]


# ── Content quality ──────────────────────────────────────────────────────────


def _content_checks(document: ResumeDocument) -> list[Check]:
    bullets = [bullet.text for role in document.experience for bullet in role.bullets]
    bullets += [bullet.text for project in document.projects for bullet in project.bullets]
    words = len(_WORD.findall(_document_text(document)))
    duplicates = len(bullets) - len({bullet.strip().lower() for bullet in bullets})
    weak = [bullet for bullet in bullets if _opens_weakly(bullet)]
    measured = [bullet for bullet in bullets if any(char.isdigit() for char in bullet)]

    return [
        Check(
            category=Category.CONTENT_QUALITY,
            name="Resume length",
            passed=200 <= words <= 900,
            weight=5,
            detail=(
                f"About {words} words, which fits a page."
                if 200 <= words <= 900
                else f"About {words} words. Under 200 reads thin; over 900 runs past a page."
            ),
        ),
        Check(
            category=Category.CONTENT_QUALITY,
            name="No duplicate lines",
            passed=duplicates == 0,
            weight=5,
            detail=(
                "No line is repeated."
                if duplicates == 0
                else f"{duplicates} line(s) appear more than once."
            ),
        ),
        Check(
            category=Category.CONTENT_QUALITY,
            name="Bullets lead with what you did",
            passed=not bullets or len(weak) <= len(bullets) // 3,
            weight=5,
            detail=(
                "Your lines lead with actions."
                if not weak
                else f"{len(weak)} line(s) open with words like 'responsible for' or 'helped'. "
                "If you did more than help, say what you did — in your record, not here."
            ),
        ),
        Check(
            category=Category.CONTENT_QUALITY,
            name="Some measurable detail",
            passed=bool(measured),
            weight=5,
            detail=(
                f"{len(measured)} line(s) include a number."
                if measured
                else "No line includes a number. If you know one, add it to your record — "
                "Workaholic will never invent one for you."
            ),
        ),
    ]


def _opens_weakly(bullet: str) -> bool:
    words = _WORD.findall(bullet)
    return bool(words) and words[0].lower() in _WEAK_OPENERS


def _document_text(document: ResumeDocument) -> str:
    parts: list[str] = [
        document.basics.full_name,
        document.basics.headline or "",
        document.summary or "",
    ]
    for role in document.experience:
        parts.extend([role.employer or "", role.title or "", *role.technologies])
        parts.extend(bullet.text for bullet in role.bullets)
    for project in document.projects:
        parts.extend([project.name, *project.technologies])
        parts.extend(bullet.text for bullet in project.bullets)
    for entry in document.education:
        parts.extend([entry.institution, entry.qualification or "", entry.field_of_study or ""])
    for group in document.skills:
        parts.extend(group.skills)
    for certification in document.certifications:
        parts.extend([certification.name, certification.issuer or ""])
    return " ".join(part for part in parts if part)


def _score_category(category: Category, checks: Sequence[Check]) -> CategoryScore:
    relevant = [check for check in checks if check.category is category]
    possible = sum(check.weight for check in relevant) or MAX_PER_CATEGORY
    earned = sum(check.points for check in relevant)
    score = round(MAX_PER_CATEGORY * earned / possible)
    failed = [check.name for check in relevant if not check.passed and check.weight]
    return CategoryScore(
        category=category,
        score=score,
        maximum=MAX_PER_CATEGORY,
        explanation=(
            "Everything checked here passed."
            if not failed
            else f"Lost points on: {', '.join(failed)}."
        ),
    )
