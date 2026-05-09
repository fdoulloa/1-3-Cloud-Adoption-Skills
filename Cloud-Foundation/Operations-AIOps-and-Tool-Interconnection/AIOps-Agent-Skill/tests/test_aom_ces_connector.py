"""Unit tests for AOM/CES connector (demo mode)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from aom_ces_connector import AOMCESConnector
from ops_agent_config import OpsAgentConfig


def _make_config() -> OpsAgentConfig:
    return OpsAgentConfig(
        hwc_ak="test-ak", hwc_sk="test-sk",
        hwc_region="la-north-2", hwc_project_id="test-project",
        demo_mode=True,
    )


class TestAOMCESConnectorDemo:
    def setup_method(self):
        self.config = _make_config()
        self.connector = AOMCESConnector(self.config)

    def test_get_current_metrics_demo(self):
        metrics = self.connector.get_current_metrics(
            "css_cluster", "cluster-abc123",
            metric_names=["cpu_utilization", "mem_utilization"],
        )
        assert "cpu_utilization" in metrics
        assert "mem_utilization" in metrics

    def test_get_alarm_state_demo(self):
        alarms = self.connector.get_alarm_state()
        assert isinstance(alarms, list)

    def test_assess_health_healthy(self):
        health = self.connector.assess_health(
            "css_cluster", "cluster-abc123",
            metric_names=["cpu_utilization"],
            thresholds={"cpu_utilization": {"warning": 95.0, "critical": 99.0}},
        )
        assert health["status"] == "healthy"
        assert len(health["violations"]) == 0

    def test_assess_health_degraded(self):
        health = self.connector.assess_health(
            "css_cluster", "cluster-abc123",
            metric_names=["cpu_utilization"],
            thresholds={"cpu_utilization": {"warning": 50.0, "critical": 99.0}},
        )
        assert health["status"] in ("degraded", "critical")

    def test_get_metric_history_demo(self):
        history = self.connector.get_metric_history(
            "css_cluster", "cluster-abc123", "cpu_utilization", period_minutes=5,
        )
        assert len(history) == 5
        for point in history:
            assert "timestamp" in point
            assert "value" in point
