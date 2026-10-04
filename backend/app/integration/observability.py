import os
import time

from fastapi import Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import settings
from app.log import get_logger

log = get_logger("app.observability")

REQUEST_COUNT = Counter(
    "eroom_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

REQUEST_LATENCY = Histogram(
    "eroom_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

_traced = False


def route_name(request: Request) -> str:
    route = request.scope.get("route")

    if route is not None and getattr(route, "path", None):
        return str(route.path)

    return request.url.path


async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    route = route_name(request)

    REQUEST_COUNT.labels(
        method=request.method,
        route=route,
        status=str(response.status_code),
    ).inc()

    REQUEST_LATENCY.labels(method=request.method, route=route).observe(elapsed)

    return response


def metrics_registry():
    multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR", "")

    if not multiproc_dir:
        return None

    from prometheus_client import CollectorRegistry
    from prometheus_client.multiprocess import MultiProcessCollector

    registry = CollectorRegistry()
    MultiProcessCollector(registry)

    return registry


def setup_metrics(app) -> None:
    app.middleware("http")(metrics_middleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        registry = metrics_registry()
        data = generate_latest(registry) if registry is not None else generate_latest()

        return PlainTextResponse(data, media_type=CONTENT_TYPE_LATEST)


def setup_tracing(service_name: str = "") -> bool:
    global _traced

    if _traced:
        return True

    if not settings.otel_enabled:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        name = service_name or settings.otel_service_name or "eroom"

        provider = TracerProvider(resource=Resource.create({"service.name": name}))

        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
            )
        )

        trace.set_tracer_provider(provider)

        from app.database import engine as db_engine

        SQLAlchemyInstrumentor().instrument(engine=db_engine)
        RedisInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        CeleryInstrumentor().instrument()
        LoggingInstrumentor(set_logging_format=False)

        _traced = True

        log.info("Tracing enabled | service=%s exporter=%s", name, settings.otel_exporter_otlp_endpoint)

        return True
    except Exception as error:
        log.warning("Tracing setup failed, continuing without traces | err=%s", str(error)[:150])

        return False


def setup_fastapi_tracing(app) -> None:
    if not settings.otel_enabled:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as error:
        log.warning("FastAPI tracing setup failed | err=%s", str(error)[:150])
