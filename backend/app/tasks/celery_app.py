from celery import Celery
from app.config import settings

celery_app = Celery(
    "immigraassist",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ingest_task",
        "app.tasks.remap_task",
        "app.tasks.feedback_task",
        "app.tasks.scraper_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    task_default_retry_delay=300,
    result_expires=86400,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    beat_schedule={
        "process-feedback-daily": {
            "task": "app.tasks.feedback_task.process_feedback_task",
            "schedule": 86400.0,
        },
        "scrape-news-daily": {
            "task": "app.tasks.scraper_task.run_scrapers_task",
            "schedule": 86400.0,
            "kwargs": {
                "scrape_policy": False,
                "scrape_news": True,
                "scrape_bia": False,
            },
        },
        "scrape-full-weekly": {
            "task": "app.tasks.scraper_task.run_scrapers_task",
            "schedule": 604800.0,
            "kwargs": {
                "scrape_policy": True,
                "scrape_news": True,
                "scrape_bia": True,
                "retry_failed": True,
            },
        },
        "scrape-missing-policy-daily": {
            "task": "app.tasks.scraper_task.run_missing_policy_task",
            "schedule": 86400.0,
        },
    },
)
