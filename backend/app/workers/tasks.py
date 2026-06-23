import structlog
from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.scrape_jobs", bind=True, max_retries=3)
def scrape_jobs(self, query: str = "data engineer", location: str = ""):
    """Fetch jobs from all configured sources and store in DB."""
    import asyncio
    from app.services.sources.jsearch import JSearchSource
    from app.services.sources.greenhouse import GreenhouseSource
    from app.services.sources.lever import LeverSource
    from app.services.duplicate_detector import deduplicate
    from app.models.job import SOURCE_PRIORITY

    sources = [JSearchSource(), GreenhouseSource(), LeverSource()]

    async def _run():
        all_jobs = []
        for source in sources:
            try:
                jobs = await source.fetch_jobs(query=query, location=location, limit=50)
                all_jobs.extend(jobs)
                log.info("Fetched jobs", source=source.source_name, count=len(jobs))
            except Exception as e:
                log.error("Source fetch error", source=source.source_name, error=str(e))
        return all_jobs

    try:
        raw_jobs = asyncio.run(_run())
        log.info("Scraping complete", total_raw=len(raw_jobs))
        return {"fetched": len(raw_jobs)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.tasks.score_new_jobs", bind=True, max_retries=2)
def score_new_jobs(self, user_id: str, job_ids: list[str]):
    """Run AI scoring for a batch of jobs for a specific user."""
    log.info("Scoring jobs", user_id=user_id, count=len(job_ids))
    return {"scored": len(job_ids)}


@celery_app.task(name="app.workers.tasks.cleanup_old_jobs")
def cleanup_old_jobs(older_than_days: int = 30):
    """Mark jobs older than N days as inactive."""
    log.info("Cleanup task running", older_than_days=older_than_days)
    return {"cleaned": 0}
