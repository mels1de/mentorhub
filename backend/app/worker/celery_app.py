from datetime import timedelta

from celery import Celery
from celery.signals import setup_logging
from kombu import Exchange, Queue

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

# Split by latency class: a slow LLM job must never delay a password-reset email.
QUEUES = ("default", "emails", "ai")

# Modules whose tasks the worker registers; feature modules add their `tasks` here.
TASK_MODULES = ["app.worker.system", "app.modules.auth.tasks"]


def create_celery(settings: Settings) -> Celery:
    app = Celery(
        "mentorhub",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend_url,
        include=TASK_MODULES,
    )
    app.conf.update(
        task_queues=[Queue(name, Exchange(name), routing_key=name) for name in QUEUES],
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        # Task names are "<queue>.<action>" for routed work, e.g. "emails.send_verification".
        task_routes={"emails.*": {"queue": "emails"}, "ai.*": {"queue": "ai"}},
        # At-least-once: ack after the task finished, redeliver if the worker dies mid-task.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # With late acks, prefetching would park tasks behind a long-running one.
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_expires=timedelta(days=1),
        task_soft_time_limit=60,
        task_time_limit=90,
        broker_connection_retry_on_startup=True,
        enable_utc=True,
        timezone="UTC",
        # Events feed Flower (observability profile).
        worker_send_task_events=True,
        task_send_sent_event=True,
        beat_schedule={},
    )
    return app


celery_app = create_celery(get_settings())


@setup_logging.connect
def _use_structlog(**_: object) -> None:
    # A receiver on this signal stops Celery from installing its own logging handlers.
    configure_logging(get_settings())
