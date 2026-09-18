"""Writing a generated document into an immutable version.

A resume and a cover letter are stored the same way: the validated JSON, the schema it was
validated against, and the prompt and model that produced it. Keeping that in one function means
a new kind of document cannot quietly forget to record where it came from.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Resume, ResumeStatus, ResumeTemplate, ResumeVersion
from app.models.user import User
from app.repositories.candidate import ResumeVersionRepository

__all__ = ["save_version"]


async def save_version(
    session: AsyncSession,
    *,
    user: User,
    resume: Resume,
    content: dict[str, Any],
    schema_version: str,
    prompt_version: str,
    model: str,
    template: ResumeTemplate,
) -> ResumeVersion:
    versions = ResumeVersionRepository(session)
    number = await versions.next_version_number(resume.id)
    version = ResumeVersion(
        user_id=user.id,
        resume_id=resume.id,
        version_number=number,
        label=f"Version {number}",
        content=content,
        template=template,
        schema_version=schema_version,
        prompt_version=prompt_version,
        model=model,
    )
    versions.add(version)
    await session.flush()
    resume.current_version_id = version.id
    resume.status = ResumeStatus.READY
    await session.commit()
    await session.refresh(version)
    return version
