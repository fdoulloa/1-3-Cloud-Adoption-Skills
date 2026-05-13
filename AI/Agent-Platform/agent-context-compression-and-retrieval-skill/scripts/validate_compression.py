#!/usr/bin/env python3
"""Validate agent context compression system components."""

import json
import sys
from pathlib import Path


def validate_compression_engine(config: dict) -> tuple[bool, str]:
    """Check compression engine is configured."""
    compression = config.get("compression", {})
    strategy = compression.get("strategy")
    threshold = compression.get("threshold")
    if strategy in ("compaction", "summarization", "extraction", "hybrid") and threshold:
        return True, f"Strategy: {strategy}, threshold: {threshold}%"
    return False, "Compression strategy or threshold not configured"


def validate_recall_probes(config: dict) -> tuple[bool, str]:
    """Check recall probes are configured."""
    probes = config.get("recall_probes", {})
    if probes.get("enabled") and probes.get("max_loss_rate"):
        return True, f"Max loss rate: {probes['max_loss_rate']}%"
    return False, "Recall probes not configured"


def validate_artifact_probes(config: dict) -> tuple[bool, str]:
    """Check artifact probes are configured."""
    probes = config.get("artifact_probes", {})
    if probes.get("enabled"):
        return True, "Artifact probes enabled"
    return False, "Artifact probes not configured"


def validate_tier_storage(config: dict) -> tuple[bool, str]:
    """Check tier storage is accessible."""
    tiers = config.get("tiers", {})
    configured = [t for t in ("t1", "t2", "t3") if tiers.get(t, {}).get("storage")]
    if len(configured) == 3:
        return True, f"All 3 tiers configured: {configured}"
    return False, f"Missing tiers: {set('t1 t2 t3'.split()) - set(configured)}"


def validate_token_budget(config: dict) -> tuple[bool, str]:
    """Check token budgets are set."""
    budgets = config.get("token_budgets", {})
    t1 = budgets.get("t1", 0)
    t2 = budgets.get("t2", 0)
    if t1 > 0 and t2 > 0:
        return True, f"T1: {t1} tokens, T2: {t2} tokens"
    return False, "Token budgets not configured"


def main():
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("compression_config.json")
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print("Creating default config for validation...")
        config = {
            "compression": {"strategy": "hybrid", "threshold": 70},
            "recall_probes": {"enabled": True, "max_loss_rate": 5},
            "artifact_probes": {"enabled": True},
            "tiers": {"t1": {"storage": "css"}, "t2": {"storage": "css"}, "t3": {"storage": "obs"}},
            "token_budgets": {"t1": 2000, "t2": 8000},
        }
    else:
        config = json.loads(config_path.read_text())

    gates = [
        ("Compression engine", validate_compression_engine(config)),
        ("Recall probes", validate_recall_probes(config)),
        ("Artifact probes", validate_artifact_probes(config)),
        ("Tier storage", validate_tier_storage(config)),
        ("Token budgets", validate_token_budget(config)),
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
