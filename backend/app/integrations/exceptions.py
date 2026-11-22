from app.core.exceptions import AppError


class IntegrationError(AppError):
    """An external service answered with something we cannot use. Retrying won't help."""

    status_code = 502
    code = "upstream_error"
    title = "Bad Gateway"


class IntegrationUnavailableError(IntegrationError):
    """Timeout, connection error, 5xx or 429. Transient: Celery tasks retry with backoff."""

    status_code = 503
    code = "upstream_unavailable"
    title = "Service Unavailable"
