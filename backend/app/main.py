from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api import health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import RequestIdMiddleware, UnhandledExceptionMiddleware
from app.core.problem_details import register_exception_handlers

logger = structlog.stdlib.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", app=app.title)
    yield
    logger.info("shutdown", app=app.title)


# Run with `uvicorn app.main:create_app --factory`: importing this module has no side effects.
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    # Before our middleware, so it is the innermost one.
    setup_metrics(app)
    # add_middleware wraps: the last one added is the outermost.
    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(RequestIdMiddleware)
    return app
