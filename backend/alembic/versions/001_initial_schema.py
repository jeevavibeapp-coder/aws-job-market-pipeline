"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500)),
        sa.Column("career_page_url", sa.String(500)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("industry", sa.String(100)),
        sa.Column("size", sa.String(50)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_companies_name", "companies", ["name"])

    remote_type_enum = postgresql.ENUM("remote", "hybrid", "onsite", name="remotetype")
    source_enum = postgresql.ENUM("company_site", "greenhouse", "lever", "workday", "indeed", "linkedin", "jsearch", name="jobsource")
    seniority_enum = postgresql.ENUM("intern", "junior", "mid", "senior", "lead", "principal", "director", name="senioritylevel")
    remote_type_enum.create(op.get_bind())
    source_enum.create(op.get_bind())
    seniority_enum.create(op.get_bind())

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(500)),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requirements", sa.Text),
        sa.Column("location", sa.String(255)),
        sa.Column("remote_type", sa.Enum("remote", "hybrid", "onsite", name="remotetype", create_type=False)),
        sa.Column("experience_min", sa.Float),
        sa.Column("experience_max", sa.Float),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("currency", sa.String(10)),
        sa.Column("source", sa.Enum("company_site", "greenhouse", "lever", "workday", "indeed", "linkedin", "jsearch", name="jobsource", create_type=False), nullable=False),
        sa.Column("direct_apply_url", sa.String(1000)),
        sa.Column("company_apply_url", sa.String(1000)),
        sa.Column("job_url", sa.String(1000), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("applicant_count", sa.Integer),
        sa.Column("competition_score", sa.Integer),
        sa.Column("skills_required", postgresql.JSONB, default=[]),
        sa.Column("seniority_level", sa.Enum("intern", "junior", "mid", "senior", "lead", "principal", "director", name="senioritylevel", create_type=False)),
        sa.Column("is_duplicate", sa.Boolean, default=False),
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
    )
    op.create_index("ix_jobs_external_id", "jobs", ["external_id"])
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index("ix_jobs_source", "jobs", ["source"])

    op.create_table(
        "job_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_match", sa.Float, default=0),
        sa.Column("experience_match", sa.Float, default=0),
        sa.Column("location_match", sa.Float, default=0),
        sa.Column("technology_match", sa.Float, default=0),
        sa.Column("seniority_match", sa.Float, default=0),
        sa.Column("overall_score", sa.Float, default=0),
        sa.Column("experience_status", sa.String(20)),
        sa.Column("match_reasons", postgresql.JSONB, default=[]),
        sa.Column("insight", sa.Text),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    status_enum = postgresql.ENUM("saved", "applied", "interview_scheduled", "offer_received", "rejected", "withdrawn", name="applicationstatus")
    status_enum.create(op.get_bind())

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("status", sa.Enum("saved", "applied", "interview_scheduled", "offer_received", "rejected", "withdrawn", name="applicationstatus", create_type=False)),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])

    op.create_table(
        "bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"])

    op.create_table(
        "resume_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("raw_text", sa.Text),
        sa.Column("parsed_skills", postgresql.JSONB, default=[]),
        sa.Column("experience_years", sa.Float),
        sa.Column("education", postgresql.JSONB, default=[]),
        sa.Column("certifications", postgresql.JSONB, default=[]),
        sa.Column("projects", postgresql.JSONB, default=[]),
        sa.Column("target_roles", postgresql.JSONB, default=[]),
        sa.Column("preferred_locations", postgresql.JSONB, default=[]),
        sa.Column("remote_preference", sa.String(20)),
        sa.Column("min_salary", sa.Integer),
        sa.Column("resume_file_url", sa.String(1000)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "search_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query", sa.Text),
        sa.Column("filters", postgresql.JSONB),
        sa.Column("results_count", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("is_read", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("search_history")
    op.drop_table("resume_profiles")
    op.drop_table("bookmarks")
    op.drop_table("applications")
    op.drop_table("job_scores")
    op.drop_table("jobs")
    op.drop_table("companies")
    op.drop_table("users")
    for name in ["applicationstatus", "senioritylevel", "jobsource", "remotetype"]:
        postgresql.ENUM(name=name).drop(op.get_bind())
