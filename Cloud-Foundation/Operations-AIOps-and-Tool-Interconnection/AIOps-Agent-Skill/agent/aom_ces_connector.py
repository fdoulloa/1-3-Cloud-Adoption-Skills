"""AOM + CES monitoring connector for the AIOps Agent.

Provides unified metric collection, alarm querying, and health assessment
from Huawei Cloud AOM (Application Operations Management) and
CES (Cloud Eye Service).
"""

import time
from typing import Optional

from cachetools import TTLCache

from ops_agent_config import OpsAgentConfig


class AOMCESConnector:
    """Unified monitoring connector for Huawei Cloud AOM and CES.

    Provides metric collection, alarm querying, and health assessment
    with TTL caching to avoid API rate limits.
    """

    DEFAULT_THRESHOLDS = {
        "cpu_utilization": {"warning": 80.0, "critical": 90.0},
        "mem_utilization": {"warning": 85.0, "critical": 95.0},
        "disk_utilization": {"warning": 80.0, "critical": 90.0},
        "disk_read_await": {"warning": 20.0, "critical": 50.0},
    }

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._metric_cache = TTLCache(maxsize=100, ttl=60)
        self._alarm_cache = TTLCache(maxsize=50, ttl=300)
        self._aom_client = None
        self._ces_client = None

    def _get_aom_client(self):
        if self._aom_client is None:
            from huaweicloudsdkaom.v1 import AomClient
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkcore.http.http_config import HttpConfig

            credentials = BasicCredentials(
                ak=self.config.hwc_ak,
                sk=self.config.hwc_sk,
                project_id=self.config.hwc_project_id,
            )
            http_config = HttpConfig.get_default_config()
            http_config.timeout = (30, 60)
            self._aom_client = (
                AomClient.new_builder()
                .with_http_config(http_config)
                .with_credentials(credentials)
                .with_region(AomClient.region.value_of(self.config.hwc_region))
                .build()
            )
        return self._aom_client

    def _get_ces_client(self):
        if self._ces_client is None:
            from huaweicloudsdkces.v1 import CesClient
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkcore.http.http_config import HttpConfig

            credentials = BasicCredentials(
                ak=self.config.hwc_ak,
                sk=self.config.hwc_sk,
                project_id=self.config.hwc_project_id,
            )
            http_config = HttpConfig.get_default_config()
            http_config.timeout = (30, 60)
            self._ces_client = (
                CesClient.new_builder()
                .with_http_config(http_config)
                .with_credentials(credentials)
                .with_region(CesClient.region.value_of(self.config.hwc_region))
                .build()
            )
        return self._ces_client

    def get_current_metrics(self, resource_type: str, resource_id: str,
                            metric_names: Optional[list[str]] = None,
                            namespace: Optional[str] = None) -> dict:
        """Get current metrics for a resource from CES.

        Returns dict of metric_name -> latest_value.
        Caches results for 60s.
        """
        cache_key = f"{resource_type}:{resource_id}:{','.join(metric_names or [])}"
        cached = self._metric_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.config.demo_mode:
            result = self._demo_metrics(resource_type, resource_id, metric_names)
        else:
            result = self._fetch_ces_metrics(resource_type, resource_id, metric_names, namespace)

        self._metric_cache[cache_key] = result
        return result

    def _fetch_ces_metrics(self, resource_type: str, resource_id: str,
                           metric_names: Optional[list[str]], namespace: Optional[str]) -> dict:
        ces = self._get_ces_client()
        from huaweicloudsdkces.v1 import (
            ShowMetricDataRequest,
            ShowMetricDataRequestBody,
        )

        now = int(time.time() * 1000)
        from_time = now - 5 * 60 * 1000  # last 5 minutes

        results = {}
        for metric_name in (metric_names or []):
            try:
                body = ShowMetricDataRequestBody(
                    namespace=namespace or f"SYS.{resource_type.upper()}",
                    metric_name=metric_name,
                    dim_name=f"{resource_type}_id",
                    dim_id=resource_id,
                    period=1,
                    filter="average",
                    _from=from_time,
                    to=now,
                )
                req = ShowMetricDataRequest(body=body)
                resp = ces.show_metric_data(req)
                datapoints = resp.datapoints or []
                if datapoints:
                    results[metric_name] = datapoints[-1].average
            except Exception:
                results[metric_name] = None
        return results

    def _demo_metrics(self, resource_type: str, resource_id: str,
                      metric_names: Optional[list[str]]) -> dict:
        defaults = {
            "cpu_utilization": 65.0,
            "mem_utilization": 72.0,
            "disk_utilization": 55.0,
        }
        if metric_names:
            return {m: defaults.get(m, 50.0) for m in metric_names}
        return defaults

    def get_alarm_state(self, resource_type: Optional[str] = None,
                        resource_id: Optional[str] = None,
                        severity: Optional[list[str]] = None) -> list[dict]:
        """Get current alarm state from AOM.

        Returns list of active alarms with severity, name, and detail.
        """
        cache_key = f"alarms:{resource_type}:{resource_id}:{severity}"
        cached = self._alarm_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.config.demo_mode:
            result = []
        else:
            result = self._fetch_aom_alarms(severity)

        self._alarm_cache[cache_key] = result
        return result

    def _fetch_aom_alarms(self, severity: Optional[list[str]]) -> list[dict]:
        aom = self._get_aom_client()
        from huaweicloudsdkaom.v1 import ListAlarmsRequest

        req = ListAlarmsRequest()
        if severity:
            req.severity = ",".join(severity)
        resp = aom.list_alarms(req)
        alarms = []
        for alarm in (resp.alarms or []):
            alarms.append({
                "alarm_id": alarm.id,
                "alarm_name": alarm.name,
                "severity": alarm.severity,
                "description": alarm.description,
                "alarm_state": alarm.alarm_state,
            })
        return alarms

    def assess_health(self, resource_type: str, resource_id: str,
                      thresholds: Optional[dict] = None,
                      metric_names: Optional[list[str]] = None) -> dict:
        """Assess resource health against thresholds.

        Returns:
            {"status": "healthy"|"degraded"|"critical",
             "violations": [...], "metrics": {...}}
        """
        effective_thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        metrics = self.get_current_metrics(resource_type, resource_id, metric_names)

        violations = []
        worst_status = "healthy"

        for metric_name, value in metrics.items():
            if value is None:
                continue
            threshold = effective_thresholds.get(metric_name)
            if not threshold:
                continue

            if value >= threshold.get("critical", 100):
                violations.append({
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold["critical"],
                    "level": "critical",
                })
                worst_status = "critical"
            elif value >= threshold.get("warning", 80):
                violations.append({
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold["warning"],
                    "level": "warning",
                })
                if worst_status != "critical":
                    worst_status = "degraded"

        return {
            "status": worst_status,
            "violations": violations,
            "metrics": metrics,
        }

    def get_metric_history(self, resource_type: str, resource_id: str,
                           metric_name: str, period_minutes: int = 30,
                           namespace: Optional[str] = None) -> list[dict]:
        """Get metric time series for anomaly detection context."""
        if self.config.demo_mode:
            return [{"timestamp": i * 60, "value": 50.0 + i * 0.5}
                    for i in range(period_minutes)]

        ces = self._get_ces_client()
        from huaweicloudsdkces.v1 import (
            ShowMetricDataRequest,
            ShowMetricDataRequestBody,
        )

        now = int(time.time() * 1000)
        from_time = now - period_minutes * 60 * 1000

        body = ShowMetricDataRequestBody(
            namespace=namespace or f"SYS.{resource_type.upper()}",
            metric_name=metric_name,
            dim_name=f"{resource_type}_id",
            dim_id=resource_id,
            period=1,
            filter="average",
            _from=from_time,
            to=now,
        )
        req = ShowMetricDataRequest(body=body)
        resp = ces.show_metric_data(req)

        return [{"timestamp": dp.timestamp, "value": dp.average}
                for dp in (resp.datapoints or [])]
