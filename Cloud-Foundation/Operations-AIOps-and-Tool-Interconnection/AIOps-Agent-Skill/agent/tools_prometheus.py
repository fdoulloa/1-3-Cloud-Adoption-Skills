"""Prometheus/Grafana metrics query tools for the AIOps Agent."""

import requests
from typing import Optional

from ops_agent_config import OpsAgentConfig


class PrometheusTools:
    """Prometheus query tools for metrics not covered by AOM/CES."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self.base_url = config.prometheus_url.rstrip("/")

    def query(self, promql: str, timestamp: Optional[str] = None) -> dict:
        """Execute instant PromQL query. L0 read-only."""
        url = f"{self.base_url}/api/v1/query"
        params = {"query": promql}
        if timestamp:
            params["time"] = timestamp

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def query_range(self, promql: str, start: str, end: str, step: str) -> dict:
        """Execute range PromQL query. L0 read-only."""
        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": promql, "start": start, "end": end, "step": step}

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_alerts(self) -> list[dict]:
        """Get current Prometheus alerts. L0 read-only."""
        url = f"{self.base_url}/api/v1/alerts"

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("alerts", [])
        except Exception:
            return []
