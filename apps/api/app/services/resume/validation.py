"""Unsupported-claim detection (PRD §36).

The model is asked to rewrite the user's sentences. This module checks that it did only that.
Everything here is deterministic and pure: no model is asked whether the output is faithful,
because a model that invents a metric will happily approve it afterwards.

Three things are checked against the source text:

* **Numbers.** Every number in a rewrite must appear in the sentence it came from. Spelled-out
  numbers count as their digits, so "two interns" may become "2 interns".
* **Names.** Proper nouns, acronyms and tool names must already be in the material. A rewrite
  may not introduce "AWS" or "Paystack" on its own.
* **Claims.** A small vocabulary of impact and seniority words — production, revenue, users,
  led, owned — must be present in the source before a rewrite may use it. This is what stops
  "helped with deployments" becoming "owned production deployments".

A failure is reported, not repaired: `app.services.resume.generation` retries once with the
problems named, and blocks generation if they persist.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = ["UnsupportedClaim", "check_text", "find_instruction", "vocabulary_of"]

# Tokens: words (with internal apostrophes, hyphens, dots and pluses, so "CI/CD", "C++",
# "Node.js" and "well-tested" survive) and numbers.
_WORD = re.compile("[A-Za-z][A-Za-z0-9'’.+#-]*")  # noqa: RUF001 - the curly apostrophe is deliberate
# Digits inside a word ("S3", "EC2") are part of a name, not a number: the name check owns them.
_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*")
_SENTENCE_START = re.compile(r"(?:^|[.!?]\s+|\n\s*|[:;]\s+|[-•]\s*)$")

_NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
    "hundred": "100",
    "thousand": "1000",
    "million": "1000000",
    "billion": "1000000000",
}

# Words that assert impact, scale or seniority. Allowed only where the source already says so.
_CLAIM_WORDS = frozenset(
    {
        "architected",
        "authored",
        "award",
        "awarded",
        "certified",
        "client",
        "clients",
        "customer",
        "customers",
        "directed",
        "downtime",
        "enterprise",
        "founded",
        "headed",
        "latency",
        "lead",
        "leading",
        "led",
        "managed",
        "managing",
        "mentored",
        "mentoring",
        "nationwide",
        "owned",
        "owning",
        "ownership",
        "patent",
        "patented",
        "pioneered",
        "production",
        "profit",
        "profitability",
        "revenue",
        "scalable",
        "scale",
        "scaled",
        "spearheaded",
        "sla",
        "supervised",
        "throughput",
        "uptime",
        "user",
        "users",
        "worldwide",
    }
)

# Stems that make a claim word acceptable when the source uses a nearby form of it: the source
# saying "leadership" licenses "led", and "scaling" licenses "scaled".
_CLAIM_STEMS = {
    "architected": "architect",
    "authored": "author",
    "awarded": "award",
    "certified": "certif",
    "client": "client",
    "clients": "client",
    "customer": "customer",
    "customers": "customer",
    "directed": "direct",
    "founded": "found",
    "headed": "head",
    "lead": "lead",
    "leading": "lead",
    "led": "lead",
    "managed": "manag",
    "managing": "manag",
    "mentored": "mentor",
    "mentoring": "mentor",
    "owned": "own",
    "owning": "own",
    "ownership": "own",
    "patented": "patent",
    "pioneered": "pioneer",
    "profitability": "profit",
    "scalable": "scal",
    "scale": "scal",
    "scaled": "scal",
    "spearheaded": "spearhead",
    "supervised": "supervis",
    "user": "user",
    "users": "user",
}


# Text that addresses the writer instead of describing what happened (PRD section 38). These
# patterns are deliberately specific: "ignore" or "say" alone appear in honest sentences, so a
# match needs the shape of an instruction. A line like this cannot be checked, because the words
# it smuggles in would license themselves as its own source.
_INSTRUCTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\b", re.I),
    re.compile(r"\byou\s+are\s+now\b", re.I),
    re.compile(r"\bact\s+as\s+(a|an|if)\b", re.I),
    re.compile(r"\bsystem\s*(prompt|note|message)\s*:", re.I),
    re.compile(r"\bmake\s+(it|this|me|that)\s+sound\b", re.I),
    re.compile(r"\bfeel\s+free\s+to\s+(add|say|mention|include|claim)\b", re.I),
    re.compile(r"\b(pretend|claim)\s+(that\s+)?i\b", re.I),
    re.compile(r"\bsay\s+(that\s+)?i\s+(led|owned|managed|built|founded|increased)\b", re.I),
    re.compile(r"\b(add|include)\s+(that\s+)?i\s+(led|owned|managed|founded)\b", re.I),
    re.compile(r"\bexaggerat", re.I),
)


def find_instruction(text: str) -> str | None:
    """The instruction-shaped phrase in this text, if there is one."""
    for pattern in _INSTRUCTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


@dataclass(frozen=True, slots=True)
class UnsupportedClaim:
    """One thing the rewrite says that the record does not support."""

    location: str  # bullet id, or "summary"
    kind: str  # "number" | "name" | "claim"
    token: str
    message: str

    def for_prompt(self) -> str:
        return f"{self.location}: {self.message}"


def vocabulary_of(texts: Iterable[str]) -> set[str]:
    """The lowercased words a rewrite is allowed to draw on."""
    words: set[str] = set()
    for text in texts:
        if text:
            words.update(match.group(0).lower().strip(".") for match in _WORD.finditer(text))
    return words


def numbers_of(texts: Iterable[str]) -> set[str]:
    """Every number in the source, digits and spelled-out forms alike, normalised."""
    numbers: set[str] = set()
    for text in texts:
        if not text:
            continue
        numbers.update(_normalise_number(match.group(0)) for match in _NUMBER.finditer(text))
        for match in _WORD.finditer(text):
            digits = _NUMBER_WORDS.get(match.group(0).lower())
            if digits:
                numbers.add(digits)
    return numbers


def check_text(
    *,
    location: str,
    rewritten: str,
    sources: Sequence[str],
    allowed_names: Iterable[str] = (),
) -> list[UnsupportedClaim]:
    """Report everything in `rewritten` that `sources` does not support.

    `sources` is the material this text was written from. `allowed_names` adds names the record
    holds elsewhere — an employer, a listed skill — which the rewrite may legitimately mention.
    """
    source_words = vocabulary_of(sources)
    source_numbers = numbers_of(sources)
    permitted_names = {name.lower().strip(".") for name in allowed_names if name}
    permitted_names.update(source_words)

    problems: list[UnsupportedClaim] = []

    for match in _NUMBER.finditer(rewritten):
        value = _normalise_number(match.group(0))
        if value not in source_numbers:
            problems.append(
                UnsupportedClaim(
                    location=location,
                    kind="number",
                    token=match.group(0),
                    message=f'the number "{match.group(0)}" is not in what you wrote',
                )
            )

    for match in _WORD.finditer(rewritten):
        token = match.group(0)
        lowered = token.lower().strip(".")
        if lowered in permitted_names:
            continue

        if _looks_like_a_name(token, rewritten, match.start()):
            problems.append(
                UnsupportedClaim(
                    location=location,
                    kind="name",
                    token=token,
                    message=f'"{token}" does not appear in what you wrote',
                )
            )
            continue

        if lowered in _CLAIM_WORDS and not _stem_present(lowered, source_words):
            problems.append(
                UnsupportedClaim(
                    location=location,
                    kind="claim",
                    token=token,
                    message=f'"{token}" claims more than what you wrote says',
                )
            )

    return _deduplicate(problems)


def _looks_like_a_name(token: str, text: str, start: int) -> bool:
    """Proper nouns, acronyms and tool names — the shapes a model uses when it invents one."""
    if any(character.isdigit() for character in token):
        return True  # "S3", "EC2", "Python3"
    if token.isupper() and len(token) > 1:
        return True  # "AWS", "SQL"
    if token[0].isupper() and len(token) > 1 and not token.isupper():
        # Capitalised mid-sentence. At the start of a sentence, capitalisation says nothing.
        return not _SENTENCE_START.search(text[:start])
    return False


def _stem_present(word: str, source_words: set[str]) -> bool:
    stem = _CLAIM_STEMS.get(word)
    if stem is None:
        return False
    return any(source_word.startswith(stem) for source_word in source_words)


def _normalise_number(raw: str) -> str:
    """ "1,200" and "1200" are the same number; "99.9" keeps its point."""
    cleaned = raw.replace(",", "")
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    return cleaned.lstrip("0") or "0"


def _deduplicate(problems: Sequence[UnsupportedClaim]) -> list[UnsupportedClaim]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[UnsupportedClaim] = []
    for problem in problems:
        key = (problem.location, problem.kind, problem.token.lower())
        if key not in seen:
            seen.add(key)
            unique.append(problem)
    return unique
