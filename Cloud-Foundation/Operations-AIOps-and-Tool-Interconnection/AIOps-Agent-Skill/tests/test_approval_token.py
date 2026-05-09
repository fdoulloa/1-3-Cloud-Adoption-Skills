"""Unit tests for approval token lifecycle."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from approval_token import ApprovalToken
from ops_agent_config import OpsAgentConfig


def _make_config() -> OpsAgentConfig:
    return OpsAgentConfig(
        hwc_ak="test-ak", hwc_sk="test-sk-key-for-hmac",
        hwc_region="la-north-2", hwc_project_id="test-project",
        approval_ttl_seconds=900,
    )


class TestApprovalToken:
    def setup_method(self):
        self.config = _make_config()
        self.token_mgr = ApprovalToken(self.config)

    def test_generate_token(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        assert "token" in request
        assert "expires_at" in request
        assert request["tool_name"] == "css.scale_out_data_nodes"

    def test_validate_token(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        result = self.token_mgr.validate(
            request["token"], "css.scale_out_data_nodes",
            {"cluster_id": "abc123"}, "admin",
        )
        assert result["valid"] is True
        assert result["expired"] is False

    def test_validate_token_wrong_params(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        result = self.token_mgr.validate(
            request["token"], "css.scale_out_data_nodes",
            {"cluster_id": "wrong"}, "admin",
        )
        assert result["valid"] is False

    def test_validate_token_wrong_tool(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        result = self.token_mgr.validate(
            request["token"], "ecs.reboot_server",
            {"cluster_id": "abc123"}, "admin",
        )
        assert result["valid"] is False

    def test_approve_token(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        result = self.token_mgr.approve(request["token"], "admin@example.com")
        assert result["approved"] is True
        assert result["approval_timestamp"] != ""

    def test_reject_token(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        result = self.token_mgr.reject(request["token"], "admin@example.com", "Too risky")
        assert result["rejected"] is True

    def test_get_status_pending(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        status = self.token_mgr.get_status(request["token"])
        assert status is not None
        assert status["approval_status"] == "pending"

    def test_get_status_approved(self):
        request = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        self.token_mgr.approve(request["token"], "admin@example.com")
        status = self.token_mgr.get_status(request["token"])
        assert status["approval_status"] == "approved"

    def test_get_status_unknown_token(self):
        status = self.token_mgr.get_status("nonexistent-token")
        assert status is None

    def test_unique_tokens_for_same_action(self):
        r1 = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        time.sleep(0.01)
        r2 = self.token_mgr.generate("css.scale_out_data_nodes", {"cluster_id": "abc123"})
        assert r1["token"] != r2["token"]
