"""Data access for interviews. Every lookup is scoped to the owning user, as elsewhere."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewMessage, InterviewSession


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sessions(self, user_id: uuid.UUID) -> list[InterviewSession]:
        result = await self._session.execute(
            select(InterviewSession)
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.updated_at.desc())
        )
        return list(result.scalars())

    async def get_owned_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> InterviewSession | None:
        result = await self._session.execute(
            select(InterviewSession).where(
                InterviewSession.id == session_id, InterviewSession.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_messages(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[InterviewMessage]:
        result = await self._session.execute(
            select(InterviewMessage)
            .where(
                InterviewMessage.session_id == session_id,
                InterviewMessage.user_id == user_id,
            )
            .order_by(InterviewMessage.sequence)
        )
        return list(result.scalars())

    async def next_sequence(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.max(InterviewMessage.sequence)).where(
                InterviewMessage.session_id == session_id
            )
        )
        return (result.scalar() or 0) + 1

    def add_session(self, session: InterviewSession) -> None:
        self._session.add(session)

    def add_message(self, message: InterviewMessage) -> None:
        self._session.add(message)
