"""Template for agent memory capture hooks."""

import json
import re
from datetime import datetime, timezone


# Default sensitive content patterns
SENSITIVE_PATTERNS = [
    re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*[\"']?[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*[\"']?[^\s\"']{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
]


def check_privacy(content: str) -> tuple[str, list[str]]:
    """Check content for sensitive information and redact if found."""
    redactions = []
    for pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(content):
            redactions.append(match.group())
            content = content.replace(match.group(), "[REDACTED]")
    return content, redactions


def capture_tool_start(tool_name: str, input_data: dict, agent_id: str, session_id: str) -> dict:
    """Capture a tool invocation start event."""
    return {
        "event": "tool_start",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "input_hash": hash(str(input_data)),
        "agent_id": agent_id,
        "session_id": session_id,
    }


def capture_tool_end(tool_name: str, result: str, success: bool, duration_ms: int,
                     agent_id: str, session_id: str) -> dict:
    """Capture a tool invocation end event."""
    filtered_result, redactions = check_privacy(result)
    return {
        "event": "tool_end",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "result_summary": filtered_result[:500],
        "success": success,
        "duration_ms": duration_ms,
        "redactions": len(redactions),
        "agent_id": agent_id,
        "session_id": session_id,
    }
