"""
Celery application for async task processing.
"""
import os
from celery import Celery

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "cxr_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

# Task routes
celery_app.conf.task_routes = {
    "app.tasks.analyze_study": {"queue": "analysis"},
    "app.tasks.convert_dicom": {"queue": "conversion"},
}

if __name__ == "__main__":
    celery_app.start()
