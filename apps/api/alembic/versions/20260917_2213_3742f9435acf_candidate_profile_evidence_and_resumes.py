"""candidate profile evidence and resumes

Revision ID: 3742f9435acf
Revises: 5875423733bf
Create Date: 2026-09-17 22:13:43.020856

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3742f9435acf"
down_revision: str | Sequence[str] | None = "5875423733bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("basics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("education", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("experience", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("achievements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("certifications", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_candidate_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_candidate_profiles_user_id")),
    )
    op.create_table(
        "evidence",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "USER_PROVIDED",
                "USER_CONFIRMED",
                "MODEL_INFERRED",
                "UNVERIFIED",
                name="evidence_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "user_input",
                "user_interview",
                "uploaded_document",
                "model_suggestion",
                name="evidence_source",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "section",
            sa.Enum(
                "basics",
                "education",
                "experience",
                "projects",
                "skills",
                "achievements",
                "certifications",
                "languages",
                "links",
                name="profile_section",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("item_id", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_evidence_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_evidence_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
    )
    op.create_index(
        "ix_evidence_profile_item", "evidence", ["candidate_profile_id", "item_id"], unique=False
    )
    op.create_index("ix_evidence_user_id_status", "evidence", ["user_id", "status"], unique=False)
    op.create_table(
        "resumes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("target_role", sa.String(length=120), nullable=True),
        sa.Column(
            "document_type",
            sa.Enum("resume", "cv", name="document_type", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "generating", "ready", "failed", name="resume_status", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_resumes_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_resumes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resumes")),
        sa.UniqueConstraint("user_id", "title", name="uq_resumes_user_id_title"),
    )
    op.create_index(
        "ix_resumes_user_id_updated_at", "resumes", ["user_id", "updated_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_resumes_user_id_updated_at", table_name="resumes")
    op.drop_table("resumes")
    op.drop_index("ix_evidence_user_id_status", table_name="evidence")
    op.drop_index("ix_evidence_profile_item", table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("candidate_profiles")
