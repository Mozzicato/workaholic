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
from app.models.user import User

__all__ = [
    "Base",
    "CandidateProfile",
    "DocumentType",
    "Evidence",
    "EvidenceSource",
    "EvidenceStatus",
    "InterviewMessage",
    "InterviewRole",
    "InterviewSession",
    "InterviewStatus",
    "ProfileSection",
    "Resume",
    "ResumeStatus",
    "ResumeTemplate",
    "ResumeVersion",
    "User",
]
