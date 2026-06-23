import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Integer, Boolean, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.core.database import Base


class RemoteType(str, enum.Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class JobSource(str, enum.Enum):
    company_site = "company_site"
    greenhouse = "greenhouse"
    lever = "lever"
    workday = "workday"
    indeed = "indeed"
    linkedin = "linkedin"
    jsearch = "jsearch"


SOURCE_PRIORITY = {
    JobSource.company_site: 1,
    JobSource.greenhouse: 2,
    JobSource.lever: 3,
    JobSource.workday: 4,
    JobSource.indeed: 5,
    JobSource.linkedin: 6,
    JobSource.jsearch: 7,
}


class SeniorityLevel(str, enum.Enum):
    intern = "intern"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    principal = "principal"
    director = "director"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(500), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    remote_type: Mapped[RemoteType] = mapped_column(
        SAEnum(RemoteType), default=RemoteType.onsite
    )
    experience_min: Mapped[float | None] = mapped_column(Float)
    experience_max: Mapped[float | None] = mapped_column(Float)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(10))
    source: Mapped[JobSource] = mapped_column(SAEnum(JobSource), nullable=False)
    direct_apply_url: Mapped[str | None] = mapped_column(String(1000))
    company_apply_url: Mapped[str | None] = mapped_column(String(1000))
    job_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    applicant_count: Mapped[int | None] = mapped_column(Integer)
    competition_score: Mapped[int | None] = mapped_column(Integer)
    skills_required: Mapped[list] = mapped_column(JSONB, default=list)
    seniority_level: Mapped[SeniorityLevel | None] = mapped_column(SAEnum(SeniorityLevel))
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"))

    company: Mapped["Company"] = relationship(back_populates="jobs")
    scores: Mapped[list["JobScore"]] = relationship(back_populates="job")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="job")


class JobScore(Base):
    __tablename__ = "job_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    skill_match: Mapped[float] = mapped_column(Float, default=0)
    experience_match: Mapped[float] = mapped_column(Float, default=0)
    location_match: Mapped[float] = mapped_column(Float, default=0)
    technology_match: Mapped[float] = mapped_column(Float, default=0)
    seniority_match: Mapped[float] = mapped_column(Float, default=0)
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    experience_status: Mapped[str] = mapped_column(String(20), default="accept")
    match_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    insight: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    job: Mapped["Job"] = relationship(back_populates="scores")
