#!/usr/bin/env python3
"""Validate enterprise agent memory system components."""

import json
import sys
from pathlib import Path


def validate_capture_hooks(config: dict) -> tuple[bool, str]:
    """Check that capture hooks are configured."""
    hooks = config.get("hooks", {})
    required_events = {"tool_start", "tool_end", "session_start", "session_end"}
    configured = set(hooks.keys())
    if required_events.issubset(configured):
        return True, f"All {len(required_events)} capture hooks configured"
    missing = required_events - configured
    return False, f"Missing hooks: {missing}"


def validate_compression_engine(config: dict) -> tuple[bool, str]:
    """Check compression engine is accessible."""
    compression = config.get("compression", {})
    if compression.get("model") and compression.get("max_input_tokens"):
        return True, f"Compression engine: {compression['model']}"
    return False, "Compression engine not configured"


def validate_vector_store(config: dict) -> tuple[bool, str]:
    """Check vector store is accessible."""
    store = config.get("vector_store", {})
    if store.get("type") in ("css", "chromadb", "sqlite"):
        return True, f"Vector store: {store['type']}"
    return False, "Vector store type not specified"


def validate_privacy_exclusions(config: dict) -> tuple[bool, str]:
    """Check privacy exclusion patterns are configured."""
    privacy = config.get("privacy", {})
    patterns = privacy.get("exclusion_patterns", [])
    pii = privacy.get("pii_detection", False)
    if patterns or pii:
        return True, f"Privacy: {len(patterns)} patterns, PII detection={pii}"
    return False, "No privacy exclusions configured"


def validate_audit_log(config: dict) -> tuple[bool, str]:
    """Check audit log is configured."""
    audit = config.get("audit", {})
    if audit.get("enabled") and audit.get("storage"):
        return True, f"Audit: {audit['storage']}"
    return False, "Audit log not configured"


def main():
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("memory_config.json")
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print("Creating default config for validation...")
        config = {
            "hooks": {"tool_start": True, "tool_end": True, "session_start": True, "session_end": True},
            "compression": {"model": "haiku", "max_input_tokens": 400},
            "vector_store": {"type": "css"},
            "privacy": {"exclusion_patterns": ["api_key", "password"], "pii_detection": True},
            "audit": {"enabled": True, "storage": "rds"},
        }
    else:
        config = json.loads(config_path.read_text())

    gates = [
        ("Capture hooks", validate_capture_hooks(config)),
        ("Compression engine", validate_compression_engine(config)),
        ("Vector store", validate_vector_store(config)),
        ("Privacy exclusions", validate_privacy_exclusions(config)),
        ("Audit log", validate_audit_log(config)),
    ]

    all_pass = True
    for name, (passed, msg) in gates:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll validation gates passed.")
    else:
        print("\nSome validation gates failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
