from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api import health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import RequestIdMiddleware, UnhandledExceptionMiddleware
from app.core.problem_details import register_exception_handlers
from app.db.session import create_engine, create_session_factory

logger = structlog.stdlib.get_logger(__name__)


def make_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        logger.info("startup", app=app.title)
        try:
            yield
        finally:
            await engine.dispose()
            logger.info("shutdown", app=app.title)

    return lifespan


# Run with `uvicorn app.main:create_app --factory`: importing this module has no side effects.
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=make_lifespan(settings))
    register_exception_handlers(app)
    app.include_router(health.router)
    # Before our middleware, so it is the innermost one.
    setup_metrics(app)
    # add_middleware wraps: the last one added is the outermost.
    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(RequestIdMiddleware)
    return app
