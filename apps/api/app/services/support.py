"""Feedback, template requests, and the numbers an administrator sees.

The dashboard counts rows. It never reads a resume, a profile section, an interview answer or a
job advert: what the product is for is none of the operator's business, and an aggregate cannot
leak it.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import (
    CandidateProfile,
    DocumentType,
    Evidence,
    EvidenceSource,
    Resume,
    ResumeVersion,
)
from app.models.interview import InterviewSession, InterviewStatus
from app.models.job import JobDescription
from app.models.support import Feedback, SupportStatus, TemplateRequest
from app.models.user import User
from app.schemas.support import AdminStats, AdminUserRead, Count
from app.services.resume.readiness import assess_readiness

MAX_TEMPLATE_BYTES = 8 * 1024 * 1024
"""The same ceiling as an uploaded CV: enough for any template, small enough for a row."""


class SupportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── what users send ─────────────────────────────────────────────────────

    async def record_feedback(
        self, user: User, *, message: str, page: str | None, email: str | None
    ) -> Feedback:
        entry = Feedback(
            user_id=user.id,
            email=(email or user.email or "").strip() or None,
            message=message,
            page=page,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def record_template_request(
        self,
        user: User,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        note: str | None,
    ) -> TemplateRequest:
        entry = TemplateRequest(
            user_id=user.id,
            email=user.email,
            note=note,
            filename=filename[:255],
            content_type=content_type,
            size_bytes=len(content),
            content=content,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    # ── what an administrator reads ─────────────────────────────────────────

    async def feedback(self, *, status: SupportStatus | None = None) -> Sequence[Feedback]:
        query = select(Feedback).order_by(Feedback.created_at.desc()).limit(200)
        if status is not None:
            query = query.where(Feedback.status == status)
        return (await self._session.scalars(query)).all()

    async def template_requests(self) -> Sequence[TemplateRequest]:
        # Without the file: a listing should not carry megabytes of attachments.
        query = (
            select(TemplateRequest)
            .order_by(TemplateRequest.created_at.desc())
            .limit(200)
            .execution_options(populate_existing=True)
        )
        return (await self._session.scalars(query)).all()

    async def template_request(self, request_id: uuid.UUID) -> TemplateRequest | None:
        return await self._session.get(TemplateRequest, request_id)

    async def feedback_item(self, feedback_id: uuid.UUID) -> Feedback | None:
        return await self._session.get(Feedback, feedback_id)

    async def set_status(self, entry: Feedback | TemplateRequest, status: SupportStatus) -> None:
        entry.status = status
        entry.handled_at = datetime.now(UTC) if status is SupportStatus.DONE else None
        await self._session.commit()

    async def delete_feedback(self, entry: Feedback) -> None:
        await self._session.delete(entry)
        await self._session.commit()

    async def delete_template_request(self, entry: TemplateRequest) -> None:
        await self._session.delete(entry)
        await self._session.commit()

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Erase an account and everything it owns. Feedback is kept, with its owner cleared."""
        user = await self._session.get(User, user_id)
        if user is None:
            return False
        await self._session.execute(delete(User).where(User.id == user_id))
        await self._session.commit()
        return True

    async def users(self) -> list[AdminUserRead]:
        users = (
            await self._session.scalars(select(User).order_by(User.created_at.desc()).limit(200))
        ).all()
        resumes = await self._count_by_user(
            select(Resume.user_id, func.count()).group_by(Resume.user_id)
        )
        drafts = await self._count_by_user(
            select(ResumeVersion.user_id, func.count()).group_by(ResumeVersion.user_id)
        )
        interviews = await self._count_by_user(
            select(InterviewSession.user_id, func.count()).group_by(InterviewSession.user_id)
        )
        ready = await self._ready_profiles()
        return [
            AdminUserRead(
                id=user.id,
                email=user.email,
                name=user.name,
                auth_provider=user.auth_provider,
                created_at=user.created_at,
                resumes=resumes.get(user.id, 0),
                drafts=drafts.get(user.id, 0),
                interviews=interviews.get(user.id, 0),
                record_ready=user.id in ready,
            )
            for user in users
        ]

    async def stats(self) -> AdminStats:
        now = datetime.now(UTC)
        week, month = now - timedelta(days=7), now - timedelta(days=30)

        templates = (
            await self._session.execute(
                select(Resume.template, func.count())
                .where(Resume.document_type != DocumentType.COVER_LETTER)
                .group_by(Resume.template)
                .order_by(func.count().desc())
            )
        ).all()
        signups = (
            await self._session.execute(
                select(func.date(User.created_at), func.count())
                .where(User.created_at >= month)
                .group_by(func.date(User.created_at))
                .order_by(func.date(User.created_at))
            )
        ).all()

        return AdminStats(
            generated_at=now,
            users_total=await self._count(select(func.count()).select_from(User)),
            users_last_7_days=await self._count(
                select(func.count()).select_from(User).where(User.created_at >= week)
            ),
            users_last_30_days=await self._count(
                select(func.count()).select_from(User).where(User.created_at >= month)
            ),
            records_ready_for_a_resume=len(await self._ready_profiles()),
            resumes_total=await self._count(
                select(func.count())
                .select_from(Resume)
                .where(Resume.document_type != DocumentType.COVER_LETTER)
            ),
            letters_total=await self._count(
                select(func.count())
                .select_from(Resume)
                .where(Resume.document_type == DocumentType.COVER_LETTER)
            ),
            drafts_total=await self._count(select(func.count()).select_from(ResumeVersion)),
            drafts_last_7_days=await self._count(
                select(func.count())
                .select_from(ResumeVersion)
                .where(ResumeVersion.created_at >= week)
            ),
            interviews_started=await self._count(
                select(func.count()).select_from(InterviewSession)
            ),
            interviews_completed=await self._count(
                select(func.count())
                .select_from(InterviewSession)
                .where(InterviewSession.status == InterviewStatus.COMPLETED)
            ),
            documents_imported=await self._count(
                select(func.count(func.distinct(Evidence.source_reference)))
                .select_from(Evidence)
                .where(Evidence.source == EvidenceSource.UPLOADED_DOCUMENT)
            ),
            jobs_saved=await self._count(select(func.count()).select_from(JobDescription)),
            wrote_a_draft_last_7_days=await self._count(
                select(func.count(func.distinct(ResumeVersion.user_id))).where(
                    ResumeVersion.created_at >= week
                )
            ),
            used_the_assistant_last_7_days=await self._count(
                select(func.count(func.distinct(InterviewSession.user_id))).where(
                    InterviewSession.created_at >= week
                )
            ),
            feedback_new=await self._count(
                select(func.count())
                .select_from(Feedback)
                .where(Feedback.status == SupportStatus.NEW)
            ),
            template_requests_new=await self._count(
                select(func.count())
                .select_from(TemplateRequest)
                .where(TemplateRequest.status == SupportStatus.NEW)
            ),
            templates_in_use=[Count(label=str(name), count=total) for name, total in templates],
            signups_by_day=[Count(label=str(day), count=total) for day, total in signups],
        )

    async def _count(self, query: Select[Any]) -> int:
        return int((await self._session.scalar(query)) or 0)

    async def _count_by_user(self, query: Select[Any]) -> dict[uuid.UUID, int]:
        rows = (await self._session.execute(query)).all()
        return {row[0]: row[1] for row in rows}

    async def _ready_profiles(self) -> set[uuid.UUID]:
        """Whose record could produce a resume today — the number that says the product works.

        Readiness is decided by the same code the product refuses on, so this cannot drift from
        what people actually experience.
        """
        profiles = (await self._session.scalars(select(CandidateProfile).limit(2000))).all()
        return {profile.user_id for profile in profiles if assess_readiness(profile).ready}
