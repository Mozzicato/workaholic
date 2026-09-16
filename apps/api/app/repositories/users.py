from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_auth_subject(self, auth_subject: str) -> User | None:
        result = await self._session.execute(select(User).where(User.auth_subject == auth_subject))
        return result.scalar_one_or_none()

    async def insert_if_absent(
        self, *, auth_subject: str, auth_provider: str, email: str | None, name: str | None
    ) -> None:
        # ON CONFLICT DO NOTHING makes concurrent first requests from the same new user safe.
        statement = (
            insert(User)
            .values(auth_subject=auth_subject, auth_provider=auth_provider, email=email, name=name)
            .on_conflict_do_nothing(index_elements=[User.auth_subject])
        )
        await self._session.execute(statement)
