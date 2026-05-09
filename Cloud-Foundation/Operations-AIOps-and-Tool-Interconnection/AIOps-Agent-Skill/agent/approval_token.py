"""L2 approval token mechanism for the AIOps Agent.

HMAC-SHA256 token with configurable TTL (default 15 minutes).
Tokens are derived from HWC_SECRET_ACCESS_KEY.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Optional

from ops_agent_config import OpsAgentConfig


class ApprovalToken:
    """Cryptographic approval token for L2 actions.

    Token = HMAC-SHA256(f"{tool_name}:{params_hash}:{timestamp}:{approver}", secret)
    Tokens expire after configurable TTL (default 15 minutes).
    """

    def __init__(self, config: OpsAgentConfig):
        self.secret = config.hwc_sk.encode("utf-8")
        self.ttl_seconds = config.approval_ttl_seconds
        self._pending: dict[str, dict] = {}

    def _compute_hmac(self, message: str) -> str:
        return hmac.new(self.secret, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def _params_hash(self, params: dict) -> str:
        return hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()

    def generate(self, tool_name: str, params: dict, requested_by: str = "aiops-agent") -> dict:
        """Generate an approval request with token.

        Returns:
            {"token": str, "expires_at": str, "action": str, "params_hash": str}
        """
        now = time.time()
        now_iso = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
        expires_iso = datetime.fromtimestamp(now + self.ttl_seconds, tz=timezone.utc).isoformat()

        p_hash = self._params_hash(params)
        message = f"{tool_name}:{p_hash}:{now_iso}:{requested_by}"
        token = self._compute_hmac(message)

        request = {
            "token": token,
            "tool_name": tool_name,
            "params_hash": p_hash,
            "generated_at": now_iso,
            "expires_at": expires_iso,
            "requested_by": requested_by,
        }
        self._pending[token] = request
        return request

    def validate(self, token: str, tool_name: str, params: dict,
                 approver: str) -> dict:
        """Validate an approval token.

        Returns:
            {"valid": bool, "expired": bool, "approver": str}
        """
        request = self._pending.get(token)
        if not request:
            return {"valid": False, "expired": False, "approver": approver}

        now = time.time()
        expires_at = datetime.fromisoformat(request["expires_at"]).timestamp()
        expired = now > expires_at

        p_hash = self._params_hash(params)
        params_match = request["params_hash"] == p_hash
        tool_match = request["tool_name"] == tool_name

        valid = not expired and params_match and tool_match
        return {"valid": valid, "expired": expired, "approver": approver}

    def approve(self, token: str, approver_identity: str) -> dict:
        """Record approval for a token.

        Returns:
            {"approved": bool, "approval_timestamp": str}
        """
        request = self._pending.get(token)
        if not request:
            return {"approved": False, "approval_timestamp": ""}

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        now = time.time()
        expires_at = datetime.fromisoformat(request["expires_at"]).timestamp()

        if now > expires_at:
            return {"approved": False, "approval_timestamp": now_iso}

        request["approval_status"] = "approved"
        request["approver_identity"] = approver_identity
        request["approval_timestamp"] = now_iso
        return {"approved": True, "approval_timestamp": now_iso}

    def reject(self, token: str, rejector_identity: str, reason: str = "") -> dict:
        """Record rejection for a token."""
        request = self._pending.get(token)
        if not request:
            return {"rejected": False}

        request["approval_status"] = "rejected"
        request["rejector_identity"] = rejector_identity
        request["rejection_reason"] = reason
        request["rejection_timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        return {"rejected": True}

    def get_status(self, token: str) -> Optional[dict]:
        """Get the current status of a pending approval request."""
        request = self._pending.get(token)
        if not request:
            return None
        return {
            "token": request["token"],
            "tool_name": request["tool_name"],
            "approval_status": request.get("approval_status", "pending"),
            "expires_at": request["expires_at"],
        }
