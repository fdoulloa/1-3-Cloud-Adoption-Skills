"""Remediation executor for the AIOps Agent.

Executes remediation actions via Huawei Cloud SDK or FunctionGraph.
"""

import time
from typing import Optional

from ops_agent_config import OpsAgentConfig
from tools_huawei_cloud import HuaweiCloudToolRegistry


class RemediationExecutor:
    """Execute remediation actions via Huawei Cloud SDK or FunctionGraph."""

    def __init__(self, config: OpsAgentConfig, tool_registry: HuaweiCloudToolRegistry):
        self.config = config
        self.tools = tool_registry

    def execute(self, tool_name: str, params: dict,
                approval_token: Optional[str] = None) -> dict:
        """Execute a remediation action.

        For FunctionGraph actions: invoke function via SDK.
        For direct SDK actions: call tool directly.
        """
        start = time.time()

        if tool_name.startswith("functiongraph.") or tool_name.startswith("fg."):
            result = self._invoke_functiongraph(tool_name, params)
        else:
            result = self._invoke_direct(tool_name, params)

        duration = time.time() - start
        return {
            "success": result.get("success", False),
            "result": result,
            "duration_seconds": round(duration, 3),
        }

    def _invoke_direct(self, tool_name: str, params: dict) -> dict:
        """Invoke a tool directly via the Huawei Cloud SDK."""
        tool_fn = self.tools.get_tool(tool_name)
        if tool_fn is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        try:
            result = tool_fn(**params)
            return {"success": True, "data": str(result)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _invoke_functiongraph(self, tool_name: str, params: dict) -> dict:
        """Invoke a FunctionGraph function for remediation."""
        function_urn = params.pop("function_urn", "")

        if not function_urn:
            return {"success": False, "error": "function_urn is required"}

        try:
            result = self.tools.fg.invoke_function(function_urn, params)
            return {"success": True, "data": str(result)}
        except Exception as e:
            return {"success": False, "error": str(e)}
