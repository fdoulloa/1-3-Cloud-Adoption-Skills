"""Unit tests for runbook template rendering."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from runbook_engine import RunbookEngine
from ops_agent_config import OpsAgentConfig


def _make_config() -> OpsAgentConfig:
    return OpsAgentConfig(
        hwc_ak="test-ak", hwc_sk="test-sk",
        skill_root=Path(__file__).parent.parent,
    )


class TestRunbookEngine:
    def setup_method(self):
        self.config = _make_config()
        self.engine = RunbookEngine(self.config)

    def test_lookup_css_high_cpu(self):
        result = self.engine.lookup_runbook("css_cluster_high_cpu")
        assert result == "runbook_css_high_cpu.md"

    def test_lookup_ecs_cpu_high(self):
        result = self.engine.lookup_runbook("ecs_cpu_high")
        assert result == "runbook_ecs_cpu_high.md"

    def test_lookup_cce_pod_crash(self):
        result = self.engine.lookup_runbook("cce_pod_crash_loop")
        assert result == "runbook_cce_pod_crash.md"

    def test_lookup_gaussdb_slow_sql(self):
        result = self.engine.lookup_runbook("gaussdb_slow_sql")
        assert result == "runbook_gaussdb_slow_sql.md"

    def test_lookup_vpn_disconnect(self):
        result = self.engine.lookup_runbook("vpn_gateway_disconnect")
        assert result == "runbook_vpn_disconnect.md"

    def test_lookup_cbr_backup_failure(self):
        result = self.engine.lookup_runbook("cbr_backup_failure")
        assert result == "runbook_cbr_backup_failure.md"

    def test_lookup_unknown_returns_none(self):
        result = self.engine.lookup_runbook("unknown_alert")
        assert result is None

    def test_load_runbook(self):
        content = self.engine.load_runbook("runbook_css_high_cpu.md")
        assert content is not None
        assert "CSS Cluster High CPU" in content

    def test_render_runbook(self):
        context = {
            "resource_id": "cluster-abc123",
            "resource_type": "css_cluster",
            "region": "la-north-2",
        }
        steps = self.engine.render_runbook("runbook_css_high_cpu.md", context)
        assert len(steps) > 0
        assert steps[0]["step"] == 1

    def test_preview_runbook(self):
        context = {
            "resource_id": "cluster-abc123",
            "resource_type": "css_cluster",
            "region": "la-north-2",
        }
        preview = self.engine.preview_runbook("runbook_css_high_cpu.md", context)
        assert "Step" in preview
        assert "Tool" in preview
        assert "Level" in preview

    def test_template_substitution(self):
        template = "Alert: {{alert_type}} on {{resource_id}}"
        result = self.engine._substitute_template(template, {
            "alert_type": "css_cluster_high_cpu",
            "resource_id": "cluster-abc123",
        })
        assert result == "Alert: css_cluster_high_cpu on cluster-abc123"

    def test_template_unsubstituted_preserved(self):
        template = "Alert: {{alert_type}} on {{unknown_var}}"
        result = self.engine._substitute_template(template, {
            "alert_type": "css_cluster_high_cpu",
        })
        assert "css_cluster_high_cpu" in result
        assert "{{unknown_var}}" in result
