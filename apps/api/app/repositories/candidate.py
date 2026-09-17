"""Data access for candidate profiles, evidence and resumes.

Every lookup takes the owning user's id. There is deliberately no "get by id" without an
owner: a missing owner filter is the classic IDOR bug, and it cannot be written here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile, Evidence, EvidenceStatus, Resume


class CandidateProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(self, user_id: uuid.UUID) -> CandidateProfile | None:
        result = await self._session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def add(self, profile: CandidateProfile) -> None:
        self._session.add(profile)


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self, user_id: uuid.UUID, *, status: EvidenceStatus | None = None
    ) -> list[Evidence]:
        query = select(Evidence).where(Evidence.user_id == user_id)
        if status is not None:
            query = query.where(Evidence.status == status)
        result = await self._session.execute(query.order_by(Evidence.created_at.desc()))
        return list(result.scalars())

    async def get_owned(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> Evidence | None:
        result = await self._session.execute(
            select(Evidence).where(Evidence.id == evidence_id, Evidence.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def add(self, evidence: Evidence) -> None:
        self._session.add(evidence)

    async def delete(self, evidence: Evidence) -> None:
        await self._session.delete(evidence)


class ResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[Resume]:
        result = await self._session.execute(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.updated_at.desc())
        )
        return list(result.scalars())

    async def get_owned(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume | None:
        result = await self._session.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def add(self, resume: Resume) -> None:
        self._session.add(resume)

    async def delete(self, resume: Resume) -> None:
        await self._session.delete(resume)
