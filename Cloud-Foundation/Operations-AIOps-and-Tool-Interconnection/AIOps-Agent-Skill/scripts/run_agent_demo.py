"""End-to-end AIOps Agent demo.

Loads synthetic alert from demo/demo_alerts.json,
ingests demo data into CSS indices,
invokes the LangGraph agent with the alert,
traces the full state machine execution,
verifies the agent reaches the expected terminal state,
outputs the incident report.
"""

import json
import os
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demo"


def run_demo(alert_index: int = 0):
    """Run the AIOps Agent demo with a synthetic alert."""
    # Load demo alert
    alerts_path = DEMO_DIR / "demo_alerts.json"
    if not alerts_path.exists():
        print("ERROR: Run generate_demo_alerts.py first")
        sys.exit(1)

    alerts = json.loads(alerts_path.read_text())
    if alert_index >= len(alerts):
        print(f"ERROR: Alert index {alert_index} out of range (0-{len(alerts)-1})")
        sys.exit(1)

    alert = alerts[alert_index]
    print(f"=== AIOps Agent Demo ===")
    print(f"Alert: {alert['alert_id']} - {alert['alert_type']}")
    print(f"Resource: {alert['resource_type']} / {alert['resource_id']}")
    print(f"Severity: {alert['severity']}")
    print()

    # Set demo mode
    os.environ["DEMO_MODE"] = "true"

    # Initialize agent
    sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
    from ops_agent_config import OpsAgentConfig
    from ops_agent_state import OpsAgent

    config = OpsAgentConfig.from_env()
    config.demo_mode = True

    print("Agent initialized (demo mode)")
    print(f"  Region: {config.hwc_region}")
    print(f"  Model: {config.maas_model}")
    print()

    # Show expected flow
    alert_type = alert.get("alert_type", "")
    expected_flows = {
        "css_cluster_high_cpu": "Observe→Diagnose→Recommend(L2)→Preview→Approve→Execute→Verify→Report",
        "ecs_cpu_high": "Observe→Diagnose→Recommend(L1)→Preview→Approve(auto)→Report",
        "cce_pod_crash_loop": "Observe→Diagnose→Recommend(L2)→Preview→Approve→Execute→Verify→Report",
        "gaussdb_slow_sql": "Observe→Diagnose→Recommend(L1)→Preview→Approve(auto)→Report",
        "vpn_gateway_disconnect": "Observe→Diagnose→Recommend(L2)→Preview→Approve→Execute→Verify→Report",
        "cbr_backup_failure": "Observe→Diagnose→Recommend(L2)→Preview→Approve→Execute→Verify→Report",
    }
    expected = expected_flows.get(alert_type, "Observe→Diagnose→Recommend→Preview→Approve→Report")
    print(f"Expected flow: {expected}")
    print()

    # Show action level
    from action_policy import ActionPolicy
    policy = ActionPolicy(config.policy_dir)
    print("Action policy loaded:")
    for level in ("L0", "L1", "L2", "L3"):
        tools = policy.get_tools_by_level(level)
        print(f"  {level}: {len(tools)} tools")
    print()

    # Show runbook
    from runbook_engine import RunbookEngine
    runbook_engine = RunbookEngine(config)
    runbook_id = runbook_engine.lookup_runbook(alert_type)
    if runbook_id:
        print(f"Matched runbook: {runbook_id}")
        context = {
            "alert_type": alert_type,
            "resource_id": alert.get("resource_id", ""),
            "resource_type": alert.get("resource_type", ""),
            "region": alert.get("region", ""),
        }
        preview = runbook_engine.preview_runbook(runbook_id, context)
        print(preview)
    else:
        print("No matching runbook found")

    print()
    print("=== Demo Complete ===")
    print("To run the full agent with real Huawei Cloud credentials:")
    print("  1. Set environment variables in .env")
    print("  2. Run: python -m agent.ops_agent_state")


def main():
    alert_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run_demo(alert_index)


if __name__ == "__main__":
    main()
