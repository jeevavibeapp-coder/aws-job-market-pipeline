import httpx
import structlog
from app.services.sources.base import BaseJobSource, RawJob
from app.core.config import settings

log = structlog.get_logger()


class LeverSource(BaseJobSource):
    source_name = "lever"
    BASE_URL = "https://api.lever.co/v0/postings"

    async def fetch_jobs(self, query: str, location: str = "", limit: int = 50) -> list[RawJob]:
        if not settings.LEVER_API_KEY:
            log.info("Lever API key not configured, skipping")
            return []
        return []

    async def fetch_company_postings(self, company_slug: str, limit: int = 50) -> list[RawJob]:
        url = f"{self.BASE_URL}/{company_slug}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params={"mode": "json", "limit": limit})
                resp.raise_for_status()
                items = resp.json()
        except Exception as e:
            log.error("Lever fetch failed", company=company_slug, error=str(e))
            return []

        jobs = []
        for item in items[:limit]:
            apply_url = item.get("applyUrl") or item.get("hostedUrl", "")
            jobs.append(RawJob(
                title=item.get("text", ""),
                company_name=company_slug,
                description=item.get("descriptionPlain") or item.get("description") or "",
                job_url=item.get("hostedUrl", ""),
                source="lever",
                location=item.get("categories", {}).get("location"),
                remote_type="remote" if "remote" in (item.get("categories", {}).get("location") or "").lower() else "onsite",
                direct_apply_url=apply_url,
                company_apply_url=apply_url,
                external_id=item.get("id"),
            ))
        return jobs
