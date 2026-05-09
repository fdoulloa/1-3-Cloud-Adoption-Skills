"""OpenTelemetry/OpenLLMetry initialization for the AIOps Agent.

Reuses openllmetry-huawei-maas-agent pattern with safe defaults.
"""

import os
from typing import Optional

from ops_agent_config import OpsAgentConfig


def init_otel_tracing(config: OpsAgentConfig,
                      exporter: str = "console") -> None:
    """Initialize OpenLLMetry/OpenTelemetry for AIOps agent tracing.

    Reuses openllmetry-huawei-maas-agent pattern:
    - TRACELOOP_TRACE_CONTENT=false by default (prevent secrets leaking)
    - Instruments: OPENAI (for MaaS) + LLAMA_INDEX (for knowledge)
    - Optional OTLP exporter for remote tracing backends
    """
    os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

    if config.otel_exporter_otlp_endpoint:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = config.otel_exporter_otlp_endpoint

    try:
        from traceloop.sdk import Traceloop
        from traceloop.sdk.instruments import Instruments

        exporter_config = None
        if exporter == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter_config = ConsoleSpanExporter()

        Traceloop.init(
            app_name="huawei-aiops-agent",
            exporter=exporter_config,
            disable_batch=True,
            telemetry_enabled=False,
            instruments={Instruments.OPENAI, Instruments.LLAMA_INDEX},
            resource_attributes={
                "service.name": "huawei-aiops-agent",
                "agent.name": "ops-remediation-agent",
                "llm.provider": "huawei-cloud-maas",
                "llm.model": config.maas_model,
                "agent.version": config.agent_version,
            },
        )
    except ImportError:
        pass  # OpenTelemetry is optional


def get_tracer(name: str = "aiops-agent"):
    """Get an OpenTelemetry tracer for manual span creation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return None


def create_span(tracer, name: str, attributes: Optional[dict] = None):
    """Create a span with optional attributes."""
    if tracer is None:
        return None
    span = tracer.start_span(name)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
    return span
