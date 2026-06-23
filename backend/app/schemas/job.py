from pydantic import BaseModel
import uuid
from datetime import datetime


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None
    career_page_url: str | None
    logo_url: str | None

    model_config = {"from_attributes": True}


class JobScoreOut(BaseModel):
    skill_match: float
    experience_match: float
    location_match: float
    technology_match: float
    seniority_match: float
    overall_score: float
    experience_status: str
    match_reasons: list[str]
    insight: str | None

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    company: CompanyOut
    location: str | None
    remote_type: str
    experience_min: float | None
    experience_max: float | None
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    source: str
    direct_apply_url: str | None
    company_apply_url: str | None
    job_url: str
    posted_at: datetime | None
    applicant_count: int | None
    competition_score: int | None
    skills_required: list[str]
    seniority_level: str | None
    score: JobScoreOut | None = None

    model_config = {"from_attributes": True}


class JobDetail(JobListItem):
    description: str
    requirements: str | None
    scraped_at: datetime


class JobFilters(BaseModel):
    source: list[str] | None = None
    remote_type: list[str] | None = None
    location: list[str] | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    posted_within_hours: int | None = 24
    min_score: float | None = None
    competition_max: int | None = None
    skills: list[str] | None = None
    limit: int = 50
    offset: int = 0
