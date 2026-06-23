import httpx
import structlog
from datetime import datetime
from app.services.sources.base import BaseJobSource, RawJob
from app.core.config import settings

log = structlog.get_logger()


class JSearchSource(BaseJobSource):
    source_name = "jsearch"

    async def fetch_jobs(self, query: str, location: str = "", limit: int = 50) -> list[RawJob]:
        if not settings.JSEARCH_API_KEY:
            log.warning("JSearch API key not configured")
            return []

        full_query = f"{query} {location}".strip() if location else query
        params = {"query": full_query, "num_pages": max(1, limit // 10), "date_posted": "today"}
        headers = {
            "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{settings.JSEARCH_BASE_URL}/search",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.error("JSearch fetch failed", error=str(e))
            return []

        jobs = []
        for item in (data.get("data") or [])[:limit]:
            posted_at = None
            if item.get("job_posted_at_timestamp"):
                try:
                    posted_at = datetime.fromtimestamp(item["job_posted_at_timestamp"])
                except Exception:
                    pass

            jobs.append(RawJob(
                title=item.get("job_title", ""),
                company_name=item.get("employer_name", ""),
                description=item.get("job_description", ""),
                job_url=item.get("job_apply_link") or item.get("job_url") or "",
                source="jsearch",
                location=item.get("job_city") or item.get("job_country"),
                remote_type="remote" if item.get("job_is_remote") else "onsite",
                experience_min=self._parse_experience(item.get("job_required_experience", {})),
                direct_apply_url=item.get("job_apply_link"),
                company_apply_url=item.get("employer_website"),
                company_website=item.get("employer_website"),
                posted_at=posted_at,
                external_id=item.get("job_id"),
                skills=item.get("job_required_skills") or [],
            ))
        return jobs

    def _parse_experience(self, exp_data: dict) -> float | None:
        if not exp_data:
            return None
        months = exp_data.get("required_experience_in_months")
        if months:
            return round(months / 12, 1)
        return None
