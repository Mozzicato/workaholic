"""The interview (PRD §23, §24).

One turn works like this:

    answer ──> checked for instructions ──> extracted ──> grounded ──> written to the record
                                                                            │
                          next gap (decided by code) ──> question ──────────┘

The model does two narrow jobs: turning an answer into fields, and phrasing a question about a
gap that code chose. Everything it returns is checked against what the person actually said
before it reaches the record, and a question that asserts anything is thrown away in favour of a
plain one. If the model is unavailable the interview still runs on those plain questions, because
the questions are not the hard part — the record is.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode, NotFoundError
from app.models.candidate import (
    CandidateProfile,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
)
from app.models.interview import (
    InterviewMessage,
    InterviewRole,
    InterviewSession,
    InterviewStatus,
)
from app.models.user import User
from app.prompts.interview import build_ask_messages, build_extract_messages
from app.prompts.interview.ask import AskContext
from app.prompts.interview.extract import ExtractContext, summarise_turns
from app.repositories.interview import InterviewRepository
from app.services.ai.base import LLMProvider
from app.services.ai.errors import AIError
from app.services.candidate import CandidateProfileService
from app.services.interview.apply import Applied, apply_basics, apply_facts
from app.services.interview.extraction import ExtractedFacts, ground
from app.services.interview.gaps import Gap, Topic, next_gap
from app.services.resume.readiness import assess_readiness
from app.services.resume.validation import check_text, find_instruction

logger = structlog.get_logger(__name__)

MAX_QUESTIONS = 25
"""A ceiling on one session, so a runaway conversation cannot run up a bill."""

MAX_ANSWER_LENGTH = 4000

_SECTION_KEYS = (
    "experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "achievements",
    "languages",
)

# Asked when the model is unavailable, or when its question strayed into asserting things.
_PLAIN_QUESTIONS: dict[Topic, str] = {
    Topic.NAME: "Let's start with you. What's your full name, as it should appear on your resume?",
    Topic.CONTACT: (
        "What email address or phone number should employers use to reach you? "
        "Tell me the city you're in too, if you'd like it on the page."
    ),
    Topic.EDUCATION: "Where are you studying, or where did you study — and what course?",
    Topic.GRADE: (
        "What grade or CGPA do you have from {subject}? "
        "If you'd rather leave it off your resume, just say skip."
    ),
    Topic.EXPERIENCE: (
        "Have you had a job, internship or placement? If so, tell me about the most recent "
        "one — where it was and what your role was. If not, just say no and we'll talk about "
        "what you've built instead."
    ),
    Topic.EXPERIENCE_DETAIL: "Thinking about {subject}: what did you actually do day to day?",
    Topic.EXPERIENCE_OUTCOME: "Thinking about {subject}: what changed because of your work?",
    Topic.TECHNOLOGIES: "Thinking about {subject}: which tools, languages or systems did you use?",
    Topic.PROJECTS: "What have you built outside of a job — coursework, a side project, anything?",
    Topic.PROJECT_DETAIL: "What does {subject} do, and why did you build it?",
    Topic.PROJECT_OUTCOME: "Did anyone use {subject}, and what came of it?",
    Topic.SKILLS: "Which skills would you be comfortable being asked about in an interview?",
    Topic.IMPACT_SCALE: (
        "About {subject}: can you put a number on any of it? How many people, how many times, "
        "how much data, how long it took — whatever you actually remember."
    ),
    Topic.IMPACT_CHANGE: (
        "About {subject}: what was it like before you did that, and what was it like after?"
    ),
    Topic.IMPACT_REACH: "About {subject}: who ended up using it, and what happened to it after?",
    Topic.CERTIFICATIONS: "Do you have any certifications or licences?",
}

_EXPECTING: dict[Topic, str] = {
    Topic.NAME: "their full name",
    Topic.CONTACT: "an email address or phone number, and optionally the city they live in",
    Topic.GRADE: "their grade or CGPA, exactly as stated",
    Topic.EXPERIENCE: "a job, internship or placement, with the employer and role",
    Topic.EXPERIENCE_DETAIL: "what they did in this role",
    Topic.EXPERIENCE_OUTCOME: "what changed because of their work",
    Topic.TECHNOLOGIES: "the tools, languages or systems they used",
    Topic.PROJECTS: "something they built outside a job",
    Topic.PROJECT_DETAIL: "what the project is and does",
    Topic.PROJECT_OUTCOME: "who used it and what came of it",
    Topic.SKILLS: "skills they can back up",
    Topic.IMPACT_SCALE: (
        "a number they actually remember — people, times, size or duration. If they do not "
        "remember one, that is fine and nothing should be recorded"
    ),
    Topic.IMPACT_CHANGE: "what it was like before, and what it was like afterwards",
    Topic.IMPACT_REACH: "who used it, how many of them, and what came of it",
    Topic.EDUCATION: "the school they attend or attended, the course, and the qualification",
    Topic.CERTIFICATIONS: (
        "the name of a certification or licence in certification_name, and when it was issued "
        "in start_date; if they say they have none, nothing is usable"
    ),
}

# Asked from a template every time. There is nothing for a model to phrase in "what's your name";
# the fixed grade question says plainly that the answer is optional; and the fixed work question
# tells someone who has never had a job that "no" is a fine answer, before they feel they must
# invent one. It is also one model call fewer on the turns where a person is still warming up.
_PLAIN_ONLY = frozenset(
    {Topic.NAME, Topic.CONTACT, Topic.EDUCATION, Topic.GRADE, Topic.EXPERIENCE, Topic.PROJECTS}
)

_GREETING = (
    "Hi! I'll walk you through your resume one question at a time — just answer the way you'd "
    "say it out loud. You can type, or press the microphone and talk. If you already have a CV, "
    "upload it and I'll only ask about what it's missing."
)

_AFTER_UPLOAD = "Thanks — I've added what you confirmed from your document."

_CLOSING = (
    "That's everything a resume needs. Your record is on the profile page — have a look, "
    "correct anything I misheard, and you can write a resume from it whenever you like."
)

_CLOSING_INCOMPLETE = (
    "That's all I'll ask for now. Before a resume can be written, your record still needs: "
    "{missing}. You can add them on your profile page, or start a new conversation with me."
)

_COULD_NOT_HEAR = (
    "Sorry — something went wrong on my side and I did not get that written down. "
    "Could you say it again?"
)

_NOT_A_FACT = (
    "I can only record what you actually did, in your own words. Tell me what happened and I'll "
    "write it down plainly."
)


class InterviewClosedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ErrorCode.CONFLICT, "This interview has already finished. Start a new one.", 409
        )


@dataclass(frozen=True, slots=True)
class _Extraction:
    """What the model made of an answer, and whether it managed to answer at all."""

    facts: ExtractedFacts | None
    failed: bool


@dataclass(frozen=True, slots=True)
class TurnResult:
    """What one answer produced."""

    session: InterviewSession
    recorded: list[str]
    dropped: list[str]
    reply: InterviewMessage
    completed: bool


class InterviewService:
    def __init__(self, session: AsyncSession, llm: LLMProvider | None = None) -> None:
        self._session = session
        self._llm = llm
        self._repository = InterviewRepository(session)
        self._profiles = CandidateProfileService(session)

    # ── sessions ────────────────────────────────────────────────────────────────

    async def start(
        self, user: User, *, resume_id: uuid.UUID | None = None, target_role: str | None = None
    ) -> InterviewSession:
        profile = await self._profiles.get_or_create(user)
        session = InterviewSession(
            user_id=user.id,
            candidate_profile_id=profile.id,
            resume_id=resume_id,
            target_role=target_role,
        )
        self._repository.add_session(session)
        await self._session.flush()

        gap = next_gap(profile)
        question = await self._compose_question(session, profile, gap, turns=[])
        if gap is None:
            session.status = InterviewStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
        await self._add_message(session, InterviewRole.AGENT, f"{_GREETING}\n\n{question}", gap)
        session.questions_asked = 1
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def get(self, user: User, session_id: uuid.UUID) -> InterviewSession:
        session = await self._repository.get_owned_session(session_id, user.id)
        if session is None:
            raise NotFoundError("We couldn't find that interview.")
        return session

    async def list_for_user(self, user: User) -> list[InterviewSession]:
        return await self._repository.list_sessions(user.id)

    async def transcript(self, user: User, session_id: uuid.UUID) -> list[InterviewMessage]:
        session = await self.get(user, session_id)
        return await self._repository.list_messages(session.id, user.id)

    async def abandon(self, user: User, session_id: uuid.UUID) -> InterviewSession:
        session = await self.get(user, session_id)
        if session.status is InterviewStatus.ACTIVE:
            session.status = InterviewStatus.ABANDONED
            await self._session.commit()
            await self._session.refresh(session)
        return session

    # ── one turn ────────────────────────────────────────────────────────────────

    async def answer(self, user: User, session_id: uuid.UUID, text: str) -> TurnResult:
        session = await self.get(user, session_id)
        if session.status is not InterviewStatus.ACTIVE:
            raise InterviewClosedError()

        answer = text.strip()[:MAX_ANSWER_LENGTH]
        messages = await self._repository.list_messages(session.id, user.id)
        last_question = next((m for m in reversed(messages) if m.role is InterviewRole.AGENT), None)
        user_message = await self._add_message(
            session,
            InterviewRole.USER,
            answer,
            topic=last_question.topic if last_question else None,
        )

        profile = await self._profiles.get_or_create(user)

        # An answer that instructs the writer cannot be recorded: the words it smuggles in would
        # become their own evidence. Say so, and ask again rather than storing it.
        if find_instruction(answer):
            reply = await self._add_message(session, InterviewRole.AGENT, _NOT_A_FACT, None)
            await self._session.commit()
            await self._session.refresh(session)
            return TurnResult(session, [], [], reply, completed=False)

        gap = _gap_for(profile, last_question)
        recorded: list[str] = []
        dropped: list[str] = []

        if gap is not None and answer:
            extraction = await self._extract(last_question, answer, gap)
            if extraction.failed:
                # Losing what somebody just said, quietly, is worse than asking them to repeat it:
                # they would carry on believing it was written down.
                reply = await self._add_message(session, InterviewRole.AGENT, _COULD_NOT_HEAR, gap)
                await self._session.commit()
                await self._session.refresh(session)
                return TurnResult(session, [], [], reply, completed=False)
            facts = extraction.facts
            if facts is not None:
                grounded = ground(facts, answer)
                grounded.dropped = _only_new(grounded.dropped, profile)
                dropped = grounded.dropped
                if grounded.usable and not grounded.is_empty:
                    basics = dict(profile.basics) if isinstance(profile.basics, dict) else {}
                    about_them = apply_basics(basics, grounded)
                    if about_them:
                        profile.basics = basics
                        recorded.extend(about_them)
                        self._record_evidence(
                            user=user,
                            profile=profile,
                            section=ProfileSection.BASICS,
                            applied_item_id=None,
                            claims=about_them,
                            message_id=user_message.id,
                        )
                    sections = {key: _copy_section(profile, key) for key in _SECTION_KEYS}
                    applied = apply_facts(sections, grounded, gap)
                    if applied.changed:
                        for key, value in sections.items():
                            setattr(profile, key, value)
                        recorded.extend(applied.notes)
                        self._record_evidence(
                            user=user,
                            profile=profile,
                            section=_section_for(applied, gap),
                            applied_item_id=applied.item_id,
                            claims=recorded,
                            message_id=user_message.id,
                        )

        await self._session.flush()
        await self._session.refresh(profile)

        asked = [message.topic for message in messages if message.topic]
        reply, finished = await self._ask_next(
            session, profile, asked, turns=_turns([*messages, user_message])
        )
        await self._session.commit()
        await self._session.refresh(session)
        return TurnResult(session, recorded, dropped, reply, completed=finished)

    async def continue_after_upload(self, user: User, session_id: uuid.UUID) -> TurnResult:
        """Pick up after a document was imported mid-conversation.

        The upload may have answered the question on screen, and several after it. Nothing is
        recorded here — the import already did that, with the person's confirmation — so this
        only chooses the next question from the record as it now stands.
        """
        session = await self.get(user, session_id)
        if session.status is not InterviewStatus.ACTIVE:
            raise InterviewClosedError()

        messages = await self._repository.list_messages(session.id, user.id)
        pending = messages[-1] if messages and messages[-1].role is InterviewRole.AGENT else None
        # The question still on screen was never answered, so it may be asked again.
        asked = [message.topic for message in messages if message.topic and message is not pending]
        profile = await self._profiles.get_or_create(user)
        reply, finished = await self._ask_next(
            session, profile, asked, turns=_turns(messages), preface=_AFTER_UPLOAD
        )
        await self._session.commit()
        await self._session.refresh(session)
        return TurnResult(session, [], [], reply, completed=finished)

    async def _ask_next(
        self,
        session: InterviewSession,
        profile: CandidateProfile,
        asked: Sequence[str | None],
        *,
        turns: Sequence[tuple[str, str]],
        preface: str | None = None,
    ) -> tuple[InterviewMessage, bool]:
        """The next question, or the closing message when there is nothing left to ask."""
        following = next_gap(profile, [topic for topic in asked if topic])
        finished = following is None or session.questions_asked >= MAX_QUESTIONS

        if finished:
            session.status = InterviewStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
            text = _closing(profile)
            gap = None
        else:
            text = await self._compose_question(session, profile, following, turns=turns)
            gap = following
            session.questions_asked += 1
        if preface:
            text = f"{preface}\n\n{text}"
        return await self._add_message(session, InterviewRole.AGENT, text, gap), finished

    # ── model calls ─────────────────────────────────────────────────────────────

    async def _extract(
        self, question: InterviewMessage | None, answer: str, gap: Gap
    ) -> _Extraction:
        if self._llm is None:
            return _Extraction(facts=None, failed=False)
        context = ExtractContext(
            question=question.content if question else "",
            answer=answer,
            known_subject=gap.subject,
            expecting=_EXPECTING.get(gap.topic, "facts about their work"),
        )
        try:
            result = await self._llm.structured_output(
                build_extract_messages(context), ExtractedFacts, operation="interview.extract"
            )
        except AIError:
            logger.warning("interview.extract.unavailable")
            return _Extraction(facts=None, failed=True)
        return _Extraction(facts=result.value, failed=False)

    async def _compose_question(
        self,
        session: InterviewSession,
        profile: CandidateProfile,
        gap: Gap | None,
        turns: Sequence[tuple[str, str]],
    ) -> str:
        if gap is None:
            return _closing(profile)
        plain = _PLAIN_QUESTIONS[gap.topic].format(subject=gap.subject)
        if self._llm is None or gap.topic in _PLAIN_ONLY:
            return plain

        context = AskContext(
            subject=gap.subject,
            missing=gap.missing,
            target_role=session.target_role,
            recent_turns=summarise_turns(turns),
        )
        try:
            result = await self._llm.generate(
                build_ask_messages(context), operation="interview.ask", max_output_tokens=200
            )
        except AIError:
            logger.warning("interview.ask.unavailable")
            return plain

        question = result.text.strip()
        if not _usable_question(question, profile, turns):
            logger.info("interview.ask.rejected")
            return plain
        return question

    # ── evidence ────────────────────────────────────────────────────────────────

    def _record_evidence(
        self,
        *,
        user: User,
        profile: CandidateProfile,
        section: ProfileSection | None,
        applied_item_id: str | None,
        claims: Sequence[str],
        message_id: uuid.UUID,
    ) -> None:
        """Every fact taken from an interview is the user's own statement (PRD §15).

        `source_reference` is the message it came from, so a claim on a resume can be traced to
        the sentence the person said.
        """
        for claim in claims:
            self._session.add(
                Evidence(
                    user_id=user.id,
                    candidate_profile_id=profile.id,
                    claim=claim[:2000],
                    status=EvidenceStatus.USER_PROVIDED,
                    source=EvidenceSource.USER_INTERVIEW,
                    source_reference=str(message_id),
                    section=section,
                    item_id=applied_item_id,
                    confirmed_at=datetime.now(UTC),
                )
            )

    async def _add_message(
        self,
        session: InterviewSession,
        role: InterviewRole,
        content: str,
        gap: Gap | None = None,
        topic: str | None = None,
    ) -> InterviewMessage:
        sequence = await self._repository.next_sequence(session.id)
        message = InterviewMessage(
            user_id=session.user_id,
            session_id=session.id,
            sequence=sequence,
            role=role,
            content=content,
            topic=gap.key if gap else topic,
        )
        self._repository.add_message(message)
        await self._session.flush()
        return message


_SECTIONS = {section.value: section for section in ProfileSection}

_SECTION_FOR_TOPIC: dict[Topic, ProfileSection] = {
    Topic.NAME: ProfileSection.BASICS,
    Topic.CONTACT: ProfileSection.BASICS,
    Topic.GRADE: ProfileSection.EDUCATION,
    Topic.EXPERIENCE: ProfileSection.EXPERIENCE,
    Topic.EXPERIENCE_DETAIL: ProfileSection.EXPERIENCE,
    Topic.EXPERIENCE_OUTCOME: ProfileSection.EXPERIENCE,
    Topic.PROJECTS: ProfileSection.PROJECTS,
    Topic.PROJECT_DETAIL: ProfileSection.PROJECTS,
    Topic.PROJECT_OUTCOME: ProfileSection.PROJECTS,
    Topic.SKILLS: ProfileSection.SKILLS,
    Topic.EDUCATION: ProfileSection.EDUCATION,
    Topic.CERTIFICATIONS: ProfileSection.CERTIFICATIONS,
}


def _section_for(applied: Applied, gap: Gap) -> ProfileSection | None:
    """Where the answer landed. An impact answer can go to a role or a project, so ask the write."""
    if applied.section is not None:
        return _SECTIONS.get(applied.section)
    return _SECTION_FOR_TOPIC.get(gap.topic)


def _closing(profile: CandidateProfile) -> str:
    readiness = assess_readiness(profile)
    if readiness.ready:
        return _CLOSING
    missing = ", ".join(item.label.lower() for item in readiness.missing)
    return _CLOSING_INCOMPLETE.format(missing=missing)


def _gap_for(profile: CandidateProfile, question: InterviewMessage | None) -> Gap | None:
    """The gap the last question was about, or the best one now if that is already filled."""
    if question is None or not question.topic:
        return next_gap(profile)
    for gap in _all_gaps(profile):
        if gap.key == question.topic:
            return gap
    # The gap it asked about is filled, but the answer still belongs to that subject.
    name, _, item_id = question.topic.partition(":")
    try:
        topic = Topic[name.upper()]
    except KeyError:
        return next_gap(profile)
    return Gap(
        topic=topic,
        item_id=None if item_id == "-" else item_id,
        subject="",
        missing="",
    )


def _all_gaps(profile: CandidateProfile) -> list[Gap]:
    from app.services.interview.gaps import open_gaps

    return open_gaps(profile)


def _usable_question(
    question: str, profile: CandidateProfile, turns: Sequence[tuple[str, str]]
) -> bool:
    """A question may not slip in facts of its own: no invented tools, employers or numbers.

    Only names and numbers count against a question. Asking "did anyone use it?" is the whole
    point of the interview, so the impact words that would disqualify a resume line are fine in
    a question — it is asking about them, not asserting them.
    """
    if not question or len(question) > 400:
        return False
    if find_instruction(question):
        return False
    sources = [text for _, text in turns]
    sources.extend(_profile_text(profile))
    invented = [
        problem
        for problem in check_text(location="question", rewritten=question, sources=sources)
        if problem.kind in ("name", "number")
    ]
    return not invented


def _only_new(dropped: Sequence[str], profile: CandidateProfile) -> list[str]:
    """Drop the noise: a value the record already holds was repeated, not invented."""
    known = {text.lower() for text in _profile_text(profile)}
    return [value for value in dropped if value.lower() not in known]


def _profile_text(profile: CandidateProfile) -> list[str]:
    texts: list[str] = []
    for key in ("experience", "projects"):
        for item in getattr(profile, key, []) or []:
            if not isinstance(item, dict):
                continue
            texts.extend(str(value) for value in item.values() if isinstance(value, str))
            for value in item.values():
                if isinstance(value, list):
                    texts.extend(entry for entry in value if isinstance(entry, str))
    for item in getattr(profile, "skills", []) or []:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            texts.append(item["name"])
    for item in getattr(profile, "education", []) or []:
        if isinstance(item, dict):
            texts.extend(value for value in item.values() if isinstance(value, str))
    basics = getattr(profile, "basics", None)
    if isinstance(basics, dict):
        texts.extend(value for value in basics.values() if isinstance(value, str))
    return texts


def _turns(messages: Sequence[InterviewMessage]) -> list[tuple[str, str]]:
    return [(message.role.value, message.content) for message in messages]


def _copy_section(profile: CandidateProfile, key: str) -> list[dict[str, Any]]:
    """A deep-enough copy: JSONB columns must be replaced, not mutated, to be saved."""
    value = getattr(profile, key, None)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
