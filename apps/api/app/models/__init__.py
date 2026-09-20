# Import every model here so Alembic autogenerate sees the complete schema.
from app.models.base import Base
from app.models.candidate import (
    CandidateProfile,
    DocumentType,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
    Resume,
    ResumeStatus,
    ResumeTemplate,
    ResumeVersion,
)
from app.models.interview import (
    InterviewMessage,
    InterviewRole,
    InterviewSession,
    InterviewStatus,
)
from app.models.job import JobDescription
from app.models.support import Feedback, SupportStatus, TemplateRequest
from app.models.user import User

__all__ = [
    "Base",
    "CandidateProfile",
    "DocumentType",
    "Evidence",
    "EvidenceSource",
    "EvidenceStatus",
    "Feedback",
    "InterviewMessage",
    "InterviewRole",
    "InterviewSession",
    "InterviewStatus",
    "JobDescription",
    "ProfileSection",
    "Resume",
    "ResumeStatus",
    "ResumeTemplate",
    "ResumeVersion",
    "SupportStatus",
    "TemplateRequest",
    "User",
]
