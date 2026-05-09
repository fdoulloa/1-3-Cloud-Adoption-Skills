"""Centralized configuration for the AIOps Agent.

Loads all settings from environment variables with sensible defaults.
Reuses the css-testing config.py pattern of .env-based configuration.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass


@dataclass
class OpsAgentConfig:
    # Huawei Cloud credentials
    hwc_ak: str = ""
    hwc_sk: str = ""
    hwc_region: str = "la-north-2"
    hwc_project_id: str = ""

    # CSS cluster
    css_cluster_id: str = ""
    css_endpoint: str = ""
    css_username: str = "admin"
    css_password: str = ""

    # MaaS LLM
    maas_api_base: str = "https://maas-api.la-north-2.myhuaweicloud.com/v1"
    maas_api_key: str = ""
    maas_model: str = "glm-5.1"

    # AOM/CES
    aom_app_id: str = ""

    # Prometheus
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"
    grafana_api_key: str = ""

    # LTS
    lts_log_group_id: str = ""
    lts_log_topic_id: str = ""

    # CTS
    cts_tracker_name: str = "system"

    # SMN
    smn_topic_urn: str = ""
    smn_approval_email: str = ""

    # OBS
    obs_bucket_name: str = ""
    obs_region: str = "la-north-2"

    # Approval
    approval_ttl_seconds: int = 900

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = ""
    traceloop_trace_content: bool = False

    # Agent behavior
    agent_version: str = "1.0.0"
    verification_delay_seconds: int = 30
    max_rediagnosis_loops: int = 2
    demo_mode: bool = False

    # Derived paths
    skill_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    runbook_dir: Path = field(default=None)
    policy_dir: Path = field(default=None)
    index_template_dir: Path = field(default=None)

    def __post_init__(self):
        self.runbook_dir = self.skill_root / "runbooks"
        self.policy_dir = self.skill_root / "policies"
        self.index_template_dir = self.skill_root / "index_templates"

    @classmethod
    def from_env(cls) -> "OpsAgentConfig":
        """Load configuration from environment variables."""
        return cls(
            hwc_ak=os.getenv("HWC_ACCESS_KEY_ID", ""),
            hwc_sk=os.getenv("HWC_SECRET_ACCESS_KEY", ""),
            hwc_region=os.getenv("HWC_REGION", "la-north-2"),
            hwc_project_id=os.getenv("HWC_PROJECT_ID", ""),
            css_cluster_id=os.getenv("CSS_CLUSTER_ID", ""),
            css_endpoint=os.getenv("CSS_ENDPOINT", ""),
            css_username=os.getenv("CSS_USERNAME", "admin"),
            css_password=os.getenv("CSS_PASSWORD", ""),
            maas_api_base=os.getenv("HUAWEI_MAAS_API_BASE",
                                    "https://maas-api.la-north-2.myhuaweicloud.com/v1"),
            maas_api_key=os.getenv("HUAWEI_MAAS_API_KEY", ""),
            maas_model=os.getenv("HUAWEI_MAAS_MODEL", "glm-5.1"),
            aom_app_id=os.getenv("AOM_APP_ID", ""),
            prometheus_url=os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
            grafana_url=os.getenv("GRAFANA_URL", "http://localhost:3000"),
            grafana_api_key=os.getenv("GRAFANA_API_KEY", ""),
            lts_log_group_id=os.getenv("LTS_LOG_GROUP_ID", ""),
            lts_log_topic_id=os.getenv("LTS_LOG_TOPIC_ID", ""),
            cts_tracker_name=os.getenv("CTS_TRACKER_NAME", "system"),
            smn_topic_urn=os.getenv("SMN_TOPIC_URN", ""),
            smn_approval_email=os.getenv("SMN_APPROVAL_EMAIL", ""),
            obs_bucket_name=os.getenv("OBS_BUCKET_NAME", ""),
            obs_region=os.getenv("OBS_REGION", "la-north-2"),
            approval_ttl_seconds=int(os.getenv("APPROVAL_TTL_SECONDS", "900")),
            otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
            traceloop_trace_content=os.getenv("TRACELOOP_TRACE_CONTENT", "false").lower() == "true",
            agent_version=os.getenv("AGENT_VERSION", "1.0.0"),
            verification_delay_seconds=int(os.getenv("VERIFICATION_DELAY_SECONDS", "30")),
            max_rediagnosis_loops=int(os.getenv("MAX_REDIAGNOSIS_LOOPS", "2")),
            demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
        )

    def validate(self) -> list[str]:
        """Validate required configuration. Returns list of errors."""
        errors = []
        if not self.hwc_ak:
            errors.append("HWC_ACCESS_KEY_ID is required")
        if not self.hwc_sk:
            errors.append("HWC_SECRET_ACCESS_KEY is required")
        if not self.hwc_project_id:
            errors.append("HWC_PROJECT_ID is required")
        if not self.css_endpoint:
            errors.append("CSS_ENDPOINT is required for log correlation")
        if not self.maas_api_key:
            errors.append("HUAWEI_MAAS_API_KEY is required for LLM inference")
        return errors
