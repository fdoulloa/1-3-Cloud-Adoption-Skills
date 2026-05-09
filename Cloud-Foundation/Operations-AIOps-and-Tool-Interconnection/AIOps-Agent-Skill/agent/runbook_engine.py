"""Runbook template renderer and executor for the AIOps Agent.

Loads runbooks from runbooks/ directory and OBS.
Renders templates with current context (alert, metrics, resource info).
"""

import re
from pathlib import Path
from typing import Optional

from ops_agent_config import OpsAgentConfig


class RunbookEngine:
    """Runbook template renderer and executor."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self.runbook_dir = config.runbook_dir

    def lookup_runbook(self, alert_type: str) -> Optional[str]:
        """Find matching runbook file by alert type.

        Maps alert types to runbook filenames.
        """
        alert_to_runbook = {
            "css_cluster_high_cpu": "runbook_css_high_cpu.md",
            "ecs_cpu_high": "runbook_ecs_cpu_high.md",
            "cce_pod_crash_loop": "runbook_cce_pod_crash.md",
            "gaussdb_slow_sql": "runbook_gaussdb_slow_sql.md",
            "vpn_gateway_disconnect": "runbook_vpn_disconnect.md",
            "cbr_backup_failure": "runbook_cbr_backup_failure.md",
        }
        filename = alert_to_runbook.get(alert_type)
        if filename and (self.runbook_dir / filename).exists():
            return filename
        return None

    def load_runbook(self, runbook_id: str) -> Optional[str]:
        """Load raw runbook content."""
        path = self.runbook_dir / runbook_id
        if path.exists():
            return path.read_text()
        return None

    def render_runbook(self, runbook_id: str, context: dict) -> list[dict]:
        """Render a runbook with current context.

        Substitutes {{variable}} placeholders with context values.
        Returns list of steps: [{"step": int, "action": str, "tool": str,
                                  "params": dict, "level": str}]
        """
        content = self.load_runbook(runbook_id)
        if not content:
            return []

        rendered = self._substitute_template(content, context)
        return self._parse_steps(rendered)

    def preview_runbook(self, runbook_id: str, context: dict) -> str:
        """Preview what a runbook would do without executing.

        Returns human-readable summary of all steps.
        """
        steps = self.render_runbook(runbook_id, context)
        if not steps:
            return f"No runbook found for {runbook_id}"

        lines = [f"Runbook: {runbook_id}", "=" * 40, ""]
        for step in steps:
            lines.append(f"Step {step.get('step', '?')}: {step.get('action', 'Unknown')}")
            lines.append(f"  Tool: {step.get('tool', 'N/A')}")
            lines.append(f"  Level: {step.get('level', 'N/A')}")
            if step.get("params"):
                lines.append(f"  Params: {step['params']}")
            lines.append("")
        return "\n".join(lines)

    def _substitute_template(self, template: str, context: dict) -> str:
        """Replace {{key}} placeholders with context values."""
        def replacer(match):
            key = match.group(1)
            value = context.get(key, match.group(0))
            if isinstance(value, dict):
                return str(value)
            return str(value)

        return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replacer, template)

    def _parse_steps(self, rendered: str) -> list[dict]:
        """Parse rendered runbook into structured steps.

        Looks for lines matching: ## Step N: <action>
        Followed by: - Tool: <tool>
        Followed by: - Level: <level>
        Followed by: - Params: <json>
        """
        steps = []
        current_step = None

        for line in rendered.split("\n"):
            step_match = re.match(r"##\s+Step\s+(\d+):\s+(.+)", line)
            if step_match:
                if current_step:
                    steps.append(current_step)
                current_step = {
                    "step": int(step_match.group(1)),
                    "action": step_match.group(2).strip(),
                    "tool": "",
                    "level": "L1",
                    "params": {},
                }
                continue

            if current_step:
                tool_match = re.match(r"-\s+Tool:\s+(.+)", line)
                if tool_match:
                    current_step["tool"] = tool_match.group(1).strip()
                    continue

                level_match = re.match(r"-\s+Level:\s+(.+)", line)
                if level_match:
                    current_step["level"] = level_match.group(1).strip()
                    continue

                params_match = re.match(r"-\s+Params:\s+(.+)", line)
                if params_match:
                    try:
                        import json
                        current_step["params"] = json.loads(params_match.group(1).strip())
                    except (json.JSONDecodeError, ValueError):
                        current_step["params"] = {"raw": params_match.group(1).strip()}

        if current_step:
            steps.append(current_step)
        return steps
