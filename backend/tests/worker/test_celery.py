from collections.abc import Iterator

import pytest
from celery import Celery
from celery.contrib.testing.worker import start_worker
from kombu.exceptions import OperationalError

from app.worker.celery_app import QUEUES, celery_app
from app.worker.system import ping
from tests.conftest import skip_unless_ci

WORKER_NAME = "pytest@localhost"


@pytest.mark.parametrize(
    ("task_name", "queue"),
    [
        ("system.ping", "default"),
        ("emails.send_verification", "emails"),
        ("ai.embed_mentor_profile", "ai"),
    ],
)
def test_tasks_are_routed_by_name_prefix(task_name: str, queue: str) -> None:
    route = celery_app.amqp.router.route({}, task_name)

    assert route["queue"].name == queue


def test_reliability_settings() -> None:
    conf = celery_app.conf

    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.accept_content == ["json"]


def test_ping_runs_locally() -> None:
    assert ping.apply().get() == "pong"


@pytest.fixture
def worker() -> Iterator[Celery]:
    try:
        celery_app.connection_for_write().ensure_connection(max_retries=1, timeout=2)
    except OperationalError as exc:
        skip_unless_ci(f"rabbitmq unavailable: {exc}")
    # A real worker thread against the real broker and result backend.
    with start_worker(
        celery_app,
        pool="solo",
        queues=list(QUEUES),
        perform_ping_check=False,
        hostname=WORKER_NAME,
    ):
        yield celery_app
        # The event loop may sleep in poll() for up to 10 s; a broadcast wakes it immediately.
        celery_app.control.shutdown(destination=[WORKER_NAME])


@pytest.mark.integration
def test_ping_round_trip_through_broker(worker: Celery) -> None:
    assert ping.delay().get(timeout=10) == "pong"
