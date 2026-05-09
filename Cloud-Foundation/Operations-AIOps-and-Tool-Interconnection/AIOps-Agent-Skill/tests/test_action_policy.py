"""Unit tests for L0/L1/L2/L3 action level enforcement."""

import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from action_policy import ActionPolicy

POLICY_DIR = Path(__file__).parent.parent / "policies"


class TestActionPolicy:
    def setup_method(self):
        self.policy = ActionPolicy(POLICY_DIR)

    def test_l0_tools_are_read_only(self):
        l0_tools = self.policy.get_tools_by_level("L0")
        assert len(l0_tools) > 0
        for tool in l0_tools:
            assert self.policy.classify(tool) == "L0"

    def test_l1_tools_are_suggest(self):
        l1_tools = self.policy.get_tools_by_level("L1")
        assert len(l1_tools) > 0
        for tool in l1_tools:
            assert self.policy.classify(tool) == "L1"

    def test_l2_tools_require_approval(self):
        l2_tools = self.policy.get_tools_by_level("L2")
        assert len(l2_tools) > 0
        for tool in l2_tools:
            result = self.policy.enforce(tool)
            assert result["requires_approval"] is True
            assert result["allowed"] is False

    def test_l3_tools_are_forbidden(self):
        l3_tools = self.policy.get_tools_by_level("L3")
        assert len(l3_tools) > 0
        for tool in l3_tools:
            assert self.policy.is_forbidden(tool) is True
            result = self.policy.enforce(tool)
            assert result["allowed"] is False

    def test_l0_auto_approved(self):
        result = self.policy.enforce("aom.list_alarms")
        assert result["allowed"] is True
        assert result["requires_approval"] is False

    def test_l1_auto_approved(self):
        result = self.policy.enforce("runbook.lookup")
        assert result["allowed"] is True
        assert result["requires_approval"] is False

    def test_l2_requires_token(self):
        result = self.policy.enforce("css.scale_out_data_nodes")
        assert result["allowed"] is False
        assert result["requires_approval"] is True

    def test_l2_approved_with_token(self):
        result = self.policy.enforce("css.scale_out_data_nodes", approval_token="valid-token")
        assert result["allowed"] is True

    def test_l3_never_approved(self):
        result = self.policy.enforce("ecs.delete_server", approval_token="any-token")
        assert result["allowed"] is False

    def test_unknown_tool_defaults_to_l3(self):
        assert self.policy.classify("unknown.tool") == "L3"

    def test_is_allowed_with_max_level(self):
        assert self.policy.is_allowed("aom.list_alarms", "L0") is True
        assert self.policy.is_allowed("runbook.lookup", "L0") is False
        assert self.policy.is_allowed("runbook.lookup", "L1") is True
        assert self.policy.is_allowed("css.scale_out_data_nodes", "L1") is False

    def test_read_only_tools_match_l0(self):
        read_only = self.policy.get_read_only_tools()
        l0 = self.policy.get_tools_by_level("L0")
        assert set(read_only) == set(l0)

    def test_all_tools_returns_mapping(self):
        all_tools = self.policy.get_all_tools()
        assert len(all_tools) > 0
        for tool, level in all_tools.items():
            assert level in ("L0", "L1", "L2", "L3")
