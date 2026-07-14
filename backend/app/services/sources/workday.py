import httpx
import structlog
from app.services.sources.base import BaseJobSource, RawJob
from app.core.config import settings

log = structlog.get_logger()


class WorkdaySource(BaseJobSource):
    """Workday tenants expose a public CxS search endpoint per company.

    URL shape: https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    Configure company tenants and pass them to ``fetch_company_jobs``.
    """

    source_name = "workday"

    async def fetch_jobs(self, query: str, location: str = "", limit: int = 50) -> list[RawJob]:
        # Generic entrypoint: Workday has no global search, so this returns
        # nothing until configured company tenants are wired in.
        return []

    async def fetch_company_jobs(
        self,
        tenant: str,
        data_center: str,
        site: str,
        limit: int = 50,
    ) -> list[RawJob]:
        base = f"https://{tenant}.{data_center}.myworkdayjobs.com"
        url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        payload = {"appliedFacets": {}, "limit": min(limit, 20), "offset": 0, "searchText": ""}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.error("Workday fetch failed", tenant=tenant, error=str(e))
            return []

        jobs: list[RawJob] = []
        for item in (data.get("jobPostings") or [])[:limit]:
            external_path = item.get("externalPath", "")
            apply_url = f"{base}/{site}{external_path}" if external_path else base
            jobs.append(RawJob(
                title=item.get("title", ""),
                company_name=tenant,
                description=item.get("bulletFields", [""])[0] if item.get("bulletFields") else "",
                job_url=apply_url,
                source="workday",
                location=item.get("locationsText"),
                direct_apply_url=apply_url,
                company_apply_url=apply_url,
                external_id=item.get("externalPath"),
            ))
        return jobs
