import httpx
import structlog
from app.services.sources.base import BaseJobSource, RawJob
from app.core.config import settings

log = structlog.get_logger()


class GreenhouseSource(BaseJobSource):
    source_name = "greenhouse"
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    async def fetch_jobs(self, query: str, location: str = "", limit: int = 50) -> list[RawJob]:
        if not settings.GREENHOUSE_API_KEY:
            log.info("Greenhouse API key not configured, skipping")
            return []
        # Greenhouse uses company-specific board slugs.
        # When API key is provided, iterate configured company boards.
        return []

    async def fetch_company_board(self, company_slug: str, limit: int = 50) -> list[RawJob]:
        url = f"{self.BASE_URL}/{company_slug}/jobs"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params={"content": "true"})
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.error("Greenhouse fetch failed", company=company_slug, error=str(e))
            return []

        jobs = []
        for item in (data.get("jobs") or [])[:limit]:
            jobs.append(RawJob(
                title=item.get("title", ""),
                company_name=company_slug,
                description=item.get("content") or item.get("description") or "",
                job_url=item.get("absolute_url", ""),
                source="greenhouse",
                location=item.get("location", {}).get("name"),
                direct_apply_url=item.get("absolute_url"),
                company_apply_url=item.get("absolute_url"),
                external_id=str(item.get("id", "")),
            ))
        return jobs
