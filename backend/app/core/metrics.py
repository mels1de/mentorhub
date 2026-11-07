from fastapi import FastAPI
from prometheus_client import CollectorRegistry, GCCollector, PlatformCollector, ProcessCollector
from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app: FastAPI) -> None:
    # One registry per app: with the global REGISTRY the instrumentator silently skips
    # metrics already registered, so only the first app in a process would be measured.
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    GCCollector(registry=registry)

    # Probes and scrapes would drown the request rate and latency of real traffic.
    Instrumentator(
        excluded_handlers=["^/health/", "^/metrics$"],
        registry=registry,
    ).instrument(app).expose(app, include_in_schema=False)
