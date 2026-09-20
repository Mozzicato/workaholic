"""Request and response shapes for feedback, template requests and the admin dashboard."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.support import SupportStatus


class SupportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FeedbackCreate(SupportModel):
    message: str = Field(min_length=1, max_length=4000)
    # Where they were when they wrote it. A path only: never a full URL with query parameters.
    page: str | None = Field(default=None, max_length=200)
    # Optional: how to reply, if they want one. Defaults to the account's address.
    email: str | None = Field(default=None, max_length=320)


class FeedbackRead(SupportModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    email: str | None
    message: str
    page: str | None
    status: SupportStatus
    created_at: datetime
    handled_at: datetime | None


class TemplateRequestRead(SupportModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    email: str | None
    note: str | None
    filename: str
    content_type: str
    size_bytes: int
    status: SupportStatus
    created_at: datetime
    handled_at: datetime | None


class SupportUpdate(SupportModel):
    status: SupportStatus


class Count(SupportModel):
    """One labelled number, for a list or a bar."""

    label: str
    count: int


class AdminStats(SupportModel):
    """Counts only. Nothing here is anyone's resume, and nothing identifies a person."""

    generated_at: datetime
    users_total: int
    users_last_7_days: int
    users_last_30_days: int
    records_ready_for_a_resume: int
    resumes_total: int
    letters_total: int
    drafts_total: int
    drafts_last_7_days: int
    interviews_started: int
    interviews_completed: int
    documents_imported: int
    jobs_saved: int
    wrote_a_draft_last_7_days: int
    used_the_assistant_last_7_days: int
    feedback_new: int
    template_requests_new: int
    templates_in_use: list[Count]
    signups_by_day: list[Count]


class AdminUserRead(SupportModel):
    """An account as an administrator sees it: how to reach them, and how far they have got."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    email: str | None
    name: str | None
    auth_provider: str
    created_at: datetime
    resumes: int
    drafts: int
    interviews: int
    record_ready: bool
