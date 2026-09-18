"""Storing and analysing job descriptions.

An advert is kept exactly as pasted so the user can always see what they applied to, and it is
analysed into structure for matching and tailoring. Analysis failing is not fatal: the advert is
still saved, and can be analysed again later.
"""

import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.job import JobDescription
from app.models.user import User
from app.prompts.job import ANALYSE_PROMPT_VERSION, build_analyse_messages
from app.prompts.job.analyse import AnalyseContext
from app.schemas.job import JobAnalysis, JobCreate, JobUpdate
from app.services.ai.base import LLMProvider
from app.services.ai.errors import AIError

logger = structlog.get_logger(__name__)


class JobService:
    def __init__(self, session: AsyncSession, llm: LLMProvider | None = None) -> None:
        self._session = session
        self._llm = llm

    async def list_for_user(self, user: User) -> Sequence[JobDescription]:
        result = await self._session.execute(
            select(JobDescription)
            .where(JobDescription.user_id == user.id)
            .order_by(JobDescription.updated_at.desc())
        )
        return list(result.scalars())

    async def get(self, user: User, job_id: uuid.UUID) -> JobDescription:
        result = await self._session.execute(
            select(JobDescription).where(
                JobDescription.id == job_id, JobDescription.user_id == user.id
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise NotFoundError("We couldn't find that job description.")
        return job

    async def create(self, user: User, payload: JobCreate) -> JobDescription:
        job = JobDescription(
            user_id=user.id,
            title=payload.title,
            company=payload.company,
            source_url=payload.source_url,
            raw_text=payload.raw_text,
            analysis={},
        )
        self._session.add(job)
        await self._session.flush()
        await self._analyse(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def update(self, user: User, job_id: uuid.UUID, payload: JobUpdate) -> JobDescription:
        job = await self.get(user, job_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def reanalyse(self, user: User, job_id: uuid.UUID) -> JobDescription:
        job = await self.get(user, job_id)
        await self._analyse(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def delete(self, user: User, job_id: uuid.UUID) -> None:
        job = await self.get(user, job_id)
        await self._session.delete(job)
        await self._session.commit()

    async def _analyse(self, job: JobDescription) -> None:
        """Read the advert into structure. A failure leaves the advert saved and unanalysed."""
        if self._llm is None:
            return
        context = AnalyseContext(title=job.title, company=job.company, raw_text=job.raw_text)
        try:
            result = await self._llm.structured_output(
                build_analyse_messages(context), JobAnalysis, operation="job.analyse"
            )
        except AIError:
            logger.warning("job.analyse.unavailable", job_id=str(job.id))
            return
        job.analysis = result.value.model_dump(mode="json")
        job.analysis_model = result.model
        job.prompt_version = ANALYSE_PROMPT_VERSION
