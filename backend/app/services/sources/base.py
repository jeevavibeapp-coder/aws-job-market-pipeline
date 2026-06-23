from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawJob:
    title: str
    company_name: str
    description: str
    job_url: str
    source: str
    location: str | None = None
    remote_type: str = "onsite"
    experience_min: float | None = None
    experience_max: float | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    direct_apply_url: str | None = None
    company_apply_url: str | None = None
    company_website: str | None = None
    posted_at: datetime | None = None
    external_id: str | None = None
    skills: list[str] = field(default_factory=list)
    applicant_count: int | None = None


class BaseJobSource(ABC):
    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self, query: str, location: str = "", limit: int = 50) -> list[RawJob]:
        pass

    async def health_check(self) -> bool:
        try:
            jobs = await self.fetch_jobs("software engineer", limit=1)
            return len(jobs) >= 0
        except Exception:
            return False
