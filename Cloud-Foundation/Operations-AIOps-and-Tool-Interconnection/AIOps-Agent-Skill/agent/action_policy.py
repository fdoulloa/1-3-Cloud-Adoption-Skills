"""L0/L1/L2/L3 action level enforcement engine.

Loads policy from action_levels.json and forbidden_actions.json.
Enforces at runtime before any tool execution.
"""

import json
from pathlib import Path
from typing import Optional


class ActionPolicy:
    """Action level enforcement for AIOps agent tools."""

    LEVELS = ("L0", "L1", "L2", "L3")

    def __init__(self, policy_dir: Optional[Path] = None):
        if policy_dir is None:
            policy_dir = Path(__file__).parent.parent / "policies"
        self.policy_dir = policy_dir
        self._tool_levels: dict[str, str] = {}
        self._level_tools: dict[str, list[str]] = {}
        self._forbidden: set[str] = set()
        self._load_policies()

    def _load_policies(self) -> None:
        action_levels_path = self.policy_dir / "action_levels.json"
        forbidden_path = self.policy_dir / "forbidden_actions.json"

        with open(action_levels_path) as f:
            levels_data = json.load(f)

        for level_key, level_data in levels_data.items():
            level = level_key.split("_")[0]  # "L0_read_only" -> "L0"
            tools = level_data.get("tools", [])
            self._level_tools[level] = tools
            for tool in tools:
                self._tool_levels[tool] = level

        with open(forbidden_path) as f:
            forbidden_data = json.load(f)
        self._forbidden = set(forbidden_data.get("forbidden_tools", []))

    def classify(self, tool_name: str) -> str:
        """Classify a tool into L0/L1/L2/L3.

        Unknown tools default to L3 (safest default).
        """
        return self._tool_levels.get(tool_name, "L3")

    def is_allowed(self, tool_name: str, max_level: str = "L2") -> bool:
        """Check if a tool is allowed at or below the given max level."""
        tool_level = self.classify(tool_name)
        if tool_name in self._forbidden:
            return False
        return self.LEVELS.index(tool_level) <= self.LEVELS.index(max_level)

    def is_forbidden(self, tool_name: str) -> bool:
        """Check if a tool is explicitly forbidden (L3)."""
        return tool_name in self._forbidden or self.classify(tool_name) == "L3"

    def enforce(self, tool_name: str, approval_token: Optional[str] = None) -> dict:
        """Enforce action policy before tool execution.

        Returns:
            {"allowed": bool, "level": str, "reason": str, "requires_approval": bool}
        """
        level = self.classify(tool_name)

        if tool_name in self._forbidden:
            return {
                "allowed": False,
                "level": "L3",
                "reason": f"Tool '{tool_name}' is forbidden (L3)",
                "requires_approval": False,
            }

        if level == "L3":
            return {
                "allowed": False,
                "level": "L3",
                "reason": f"Tool '{tool_name}' classified as L3 (forbidden)",
                "requires_approval": False,
            }

        if level in ("L0", "L1"):
            return {
                "allowed": True,
                "level": level,
                "reason": f"Tool '{tool_name}' is {level} (auto-approved)",
                "requires_approval": False,
            }

        if level == "L2":
            if approval_token:
                return {
                    "allowed": True,
                    "level": "L2",
                    "reason": f"Tool '{tool_name}' is L2 with approval token",
                    "requires_approval": False,
                }
            return {
                "allowed": False,
                "level": "L2",
                "reason": f"Tool '{tool_name}' requires approval (L2)",
                "requires_approval": True,
            }

        return {
            "allowed": False,
            "level": "L3",
            "reason": f"Unknown tool '{tool_name}' defaults to L3",
            "requires_approval": False,
        }

    def get_read_only_tools(self) -> list[str]:
        """Return all L0 tools."""
        return self._level_tools.get("L0", [])

    def get_tools_by_level(self, level: str) -> list[str]:
        """Return all tools at a given level."""
        return self._level_tools.get(level, [])

    def get_all_tools(self) -> dict[str, str]:
        """Return mapping of all tools to their levels."""
        return dict(self._tool_levels)
