from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "job_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.scrape_jobs": {"queue": "scraping"},
        "app.workers.tasks.score_new_jobs": {"queue": "scoring"},
        "app.workers.tasks.cleanup_old_jobs": {"queue": "default"},
    },
    beat_schedule={
        "scrape-jobs-every-hour": {
            "task": "app.workers.tasks.scrape_jobs",
            "schedule": crontab(minute=0),
        },
        "cleanup-daily": {
            "task": "app.workers.tasks.cleanup_old_jobs",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
