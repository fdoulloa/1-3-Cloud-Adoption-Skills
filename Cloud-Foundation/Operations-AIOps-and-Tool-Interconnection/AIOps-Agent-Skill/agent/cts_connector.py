"""CTS (Cloud Trace Service) audit trail connector for the AIOps Agent.

Retrieves audit events to identify recent configuration changes
that may have caused anomalies.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from ops_agent_config import OpsAgentConfig


class CTSConnector:
    """Cloud Trace Service connector for audit trail retrieval."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            from huaweicloudsdkcts.v3 import CtsClient
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkcore.http.http_config import HttpConfig

            credentials = BasicCredentials(
                ak=self.config.hwc_ak,
                sk=self.config.hwc_sk,
                project_id=self.config.hwc_project_id,
            )
            http_config = HttpConfig.get_default_config()
            http_config.timeout = (30, 60)
            self._client = (
                CtsClient.new_builder()
                .with_http_config(http_config)
                .with_credentials(credentials)
                .with_region(CtsClient.region.value_of(self.config.hwc_region))
                .build()
            )
        return self._client

    def get_recent_events(self, resource_id: Optional[str] = None,
                          resource_type: Optional[str] = None,
                          minutes: int = 60) -> list[dict]:
        """Get recent CTS events for a resource.

        Used in the observe node to find recent changes.
        """
        if self.config.demo_mode:
            return []

        cts = self._get_client()
        from huaweicloudsdkcts.v3 import ListTracesRequest

        now = datetime.now(tz=timezone.utc)
        from_time = now - timedelta(minutes=minutes)

        req = ListTracesRequest()
        req.tracker_name = self.config.cts_tracker_name
        if resource_id:
            req.resource_id = resource_id
        if resource_type:
            req.resource_type = resource_type
        req.from_time = int(from_time.timestamp() * 1000)
        req.to_time = int(now.timestamp() * 1000)

        resp = cts.list_traces(req)
        return [self._format_trace(t) for t in (resp.traces or [])]

    def find_config_changes(self, resource_id: str,
                            from_time: str, to_time: str) -> list[dict]:
        """Find configuration change events for a resource in a time window.

        Filters for trace_names containing 'update', 'create', 'delete'.
        """
        if self.config.demo_mode:
            return []

        cts = self._get_client()
        from huaweicloudsdkcts.v3 import ListTracesRequest

        req = ListTracesRequest()
        req.tracker_name = self.config.cts_tracker_name
        req.resource_id = resource_id
        req.from_time = int(datetime.fromisoformat(from_time).timestamp() * 1000)
        req.to_time = int(datetime.fromisoformat(to_time).timestamp() * 1000)

        resp = cts.list_traces(req)
        change_keywords = ("update", "create", "delete", "modify", "resize", "restart")

        changes = []
        for trace in (resp.traces or []):
            trace_name = getattr(trace, "trace_name", "") or ""
            if any(kw in trace_name.lower() for kw in change_keywords):
                changes.append(self._format_trace(trace))
        return changes

    def correlate_with_alert(self, alert: dict,
                             window_minutes: int = 30) -> list[dict]:
        """Find CTS events that occurred near the alert time for the same resource.

        Used to identify if a recent change caused the anomaly.
        """
        resource_id = alert.get("resource_id", "")
        alert_time = alert.get("timestamp", "")

        if not resource_id or not alert_time:
            return []

        alert_dt = datetime.fromisoformat(alert_time.replace("Z", "+00:00"))
        from_time = (alert_dt - timedelta(minutes=window_minutes)).isoformat()
        to_time = alert_dt.isoformat()

        return self.find_config_changes(resource_id, from_time, to_time)

    def _format_trace(self, trace) -> dict:
        return {
            "trace_id": getattr(trace, "id", ""),
            "trace_name": getattr(trace, "trace_name", ""),
            "trace_type": getattr(trace, "trace_type", ""),
            "trace_status": getattr(trace, "trace_status", ""),
            "resource_id": getattr(trace, "resource_id", ""),
            "resource_type": getattr(trace, "resource_type", ""),
            "resource_name": getattr(trace, "resource_name", ""),
            "user": getattr(trace, "user", {}),
            "time": getattr(trace, "time", ""),
            "code": getattr(trace, "code", ""),
            "api_version": getattr(trace, "api_version", ""),
            "request": getattr(trace, "request", ""),
            "response": getattr(trace, "response", ""),
        }
