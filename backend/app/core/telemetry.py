"""
OpenTelemetry instrumentation for the Second Brain RAG pipeline.

Provides distributed tracing across:
- HTTP requests (FastAPI auto-instrumentation)
- RAG pipeline stages (retrieval, reranking, generation)
- Database operations (Neo4j, ChromaDB)
- LLM API calls

Exports traces to console/file by default (zero cost). Can be configured
to export to Jaeger, Zipkin, or any OTLP-compatible backend via env vars.
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.logging import get_logger

logger = get_logger(__name__)

_initialized = False


def init_telemetry(app=None):
    """
    Initialize OpenTelemetry tracing.

    Configuration via environment variables:
    - OTEL_ENABLED: "true" to enable (default: "true")
    - OTEL_SERVICE_NAME: service name (default: "second-brain-rag")
    - OTEL_EXPORTER: "console", "otlp", or "none" (default: "console")
    - OTEL_OTLP_ENDPOINT: OTLP collector endpoint (if exporter=otlp)
    """
    global _initialized
    if _initialized:
        return

    enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    if not enabled:
        logger.info("OpenTelemetry disabled via OTEL_ENABLED=false")
        _initialized = True
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "second-brain-rag")
    exporter_type = os.getenv("OTEL_EXPORTER", "console").lower()

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter_type == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter_type == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            endpoint = os.getenv("OTEL_OTLP_ENDPOINT", "http://localhost:4317")
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {endpoint}")
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp not installed. Falling back to console."
            )
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter_type == "none":
        pass  # No exporter — traces are discarded (useful for tests)
    else:
        logger.warning(f"Unknown OTEL_EXPORTER={exporter_type}, using console")
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI if app is provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumented with OpenTelemetry")

    _initialized = True
    logger.info(f"OpenTelemetry initialized (service={service_name}, exporter={exporter_type})")


def get_tracer(name: str = "rag") -> trace.Tracer:
    """Get a named tracer for manual span creation."""
    return trace.get_tracer(name)
