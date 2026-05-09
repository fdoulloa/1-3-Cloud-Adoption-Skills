"""Unit tests for LangGraph state transitions and conditional routing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from ops_agent_state import OpsAgentState, OpsAgent
from ops_agent_config import OpsAgentConfig


def _make_config() -> OpsAgentConfig:
    config = OpsAgentConfig(
        hwc_ak="test-ak", hwc_sk="test-sk",
        hwc_region="la-north-2", hwc_project_id="test-project",
        css_endpoint="https://css.example.com", maas_api_key="test-key",
        demo_mode=True,
    )
    return config


class TestConditionalRouting:
    def setup_method(self):
        self.config = _make_config()
        self.agent = OpsAgent(self.config)

    def test_route_after_approval_l0_goes_to_report(self):
        state = {"action_level": "L0", "approval_status": "auto_approved"}
        assert self.agent._route_after_approval(state) == "report"

    def test_route_after_approval_l1_goes_to_report(self):
        state = {"action_level": "L1", "approval_status": "auto_approved"}
        assert self.agent._route_after_approval(state) == "report"

    def test_route_after_approval_l2_approved_goes_to_execute(self):
        state = {"action_level": "L2", "approval_status": "approved"}
        assert self.agent._route_after_approval(state) == "execute"

    def test_route_after_approval_l2_rejected_goes_to_report(self):
        state = {"action_level": "L2", "approval_status": "rejected"}
        assert self.agent._route_after_approval(state) == "report"

    def test_route_after_approval_l2_expired_goes_to_report(self):
        state = {"action_level": "L2", "approval_status": "expired"}
        assert self.agent._route_after_approval(state) == "report"

    def test_route_after_approval_l2_pending_stays_in_approve(self):
        state = {"action_level": "L2", "approval_status": "pending"}
        assert self.agent._route_after_approval(state) == "approve"

    def test_route_after_approval_l3_blocked_goes_to_report(self):
        state = {"action_level": "L3", "approval_status": "blocked"}
        assert self.agent._route_after_approval(state) == "report"

    def test_route_after_verification_healthy_goes_to_report(self):
        state = {"verification_status": "healthy", "loop_count": 0}
        assert self.agent._route_after_verification(state) == "report"

    def test_route_after_verification_degraded_re_diagnoses(self):
        state = {"verification_status": "degraded", "loop_count": 0}
        assert self.agent._route_after_verification(state) == "observe"

    def test_route_after_verification_degraded_max_loops_goes_to_report(self):
        state = {"verification_status": "degraded", "loop_count": 2}
        assert self.agent._route_after_verification(state) == "report"

    def test_route_after_verification_failed_goes_to_report(self):
        state = {"verification_status": "failed", "loop_count": 0}
        assert self.agent._route_after_verification(state) == "report"
