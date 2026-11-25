from app.worker.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> str:
    """Round-trip probe: API → RabbitMQ → worker → Redis result backend."""
    return "pong"
