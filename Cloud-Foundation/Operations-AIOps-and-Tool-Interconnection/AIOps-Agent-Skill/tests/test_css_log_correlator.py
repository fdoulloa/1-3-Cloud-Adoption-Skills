"""Unit tests for CSS log correlation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from css_log_correlator import CSSLogCorrelator
from ops_agent_config import OpsAgentConfig


class TestCSSLogCorrelator:
    """Tests for CSSLogCorrelator structure.

    Full integration tests require a running CSS cluster.
    These test the class can be instantiated and methods exist.
    """

    def test_class_instantiation(self):
        config = OpsAgentConfig(
            css_endpoint="https://css.example.com",
            css_username="admin", css_password="test",
        )
        correlator = CSSLogCorrelator(config)
        assert correlator.config is config

    def test_default_correlation_fields(self):
        assert "resource_id" in CSSLogCorrelator.DEFAULT_CORRELATION_FIELDS
        assert "region" in CSSLogCorrelator.DEFAULT_CORRELATION_FIELDS
        assert "correlation_id" in CSSLogCorrelator.DEFAULT_CORRELATION_FIELDS
