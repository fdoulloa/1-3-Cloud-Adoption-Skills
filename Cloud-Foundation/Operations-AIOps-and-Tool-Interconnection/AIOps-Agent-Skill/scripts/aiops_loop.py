#!/usr/bin/env python3
"""AIOps Agent continuous loop.

Cycles through all 6 alert scenarios, runs the LangGraph agent,
persists incident reports to CSS, and sleeps between cycles.

Environment variables:
  AIOPS_CYCLE_SLEEP  - Seconds between cycles (default: 120)
  AIOPS_MAX_CYCLES   - Max cycles before stopping (default: 0 = infinite)
  AIOPS_AGENT_DIR    - Agent root directory (default: /opt/aiops-agent)
"""

import json
import os
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = os.getenv("AIOPS_AGENT_DIR", str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.join(AGENT_DIR, "agent"))
os.chdir(AGENT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(AGENT_DIR, ".env"), override=False)

from ops_agent_config import OpsAgentConfig
from ops_agent_state import OpsAgent
from opensearchpy import OpenSearch

AGENT_ROOT = Path(AGENT_DIR)
LOG_FILE = AGENT_ROOT / "aiops_loop.log"


def log(msg):
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_css_client(config):
    from urllib.parse import urlparse
    parsed = urlparse(config.css_endpoint)
    return OpenSearch(
        hosts=[{"host": parsed.hostname, "port": parsed.port or 9200}],
        http_auth=(config.css_username, config.css_password),
        use_ssl=parsed.scheme == "https",
        verify_certs=False,
        ssl_show_warn=False,
    )


def index_incident_to_css(client, incident):
    index_name = "ops_incidents-{}".format(datetime.now(tz=timezone.utc).strftime("%Y.%m.%d"))
    try:
        client.index(index=index_name, body=incident, refresh=True)
        log("  Incident indexed to {}".format(index_name))
    except Exception as e:
        log("  CSS index error: {}".format(e))


def inject_fresh_alert(alert_template, cycle):
    """Create a fresh alert with current timestamp and varied metric values."""
    alert = dict(alert_template)
    now = datetime.now(tz=timezone.utc).isoformat()
    alert["timestamp"] = now
    alert["alert_id"] = "{}-C{}".format(alert["alert_id"], cycle)
    if "metric_value" in alert:
        base = float(alert["metric_value"])
        alert["metric_value"] = round(base * (0.9 + random.random() * 0.3), 2)
    return alert


def main():
    log("=" * 60)
    log("AIOps Agent Loop Starting")
    log("=" * 60)

    config = OpsAgentConfig.from_env()

    agent = OpsAgent(config)
    css_client = get_css_client(config)

    alerts = json.loads((AGENT_ROOT / "demo" / "demo_alerts.json").read_text())
    alert_names = [a.get("alert_type", "unknown") for a in alerts]
    log("Loaded {} alert scenarios: {}".format(len(alerts), alert_names))
    log("  Demo mode: {}".format(config.demo_mode))
    log("  Region: {}".format(config.hwc_region))
    log("  Model: {}".format(config.maas_model))

    cycle = 0
    total_incidents = 0
    max_cycles = int(os.getenv("AIOPS_MAX_CYCLES", "0"))
    sleep_seconds = int(os.getenv("AIOPS_CYCLE_SLEEP", "120"))

    while True:
        if max_cycles > 0 and cycle >= max_cycles:
            log("Reached max cycles ({}), stopping.".format(max_cycles))
            break

        cycle += 1
        # Round-robin with 20% random pick for variety
        if random.random() < 0.2:
            idx = random.randint(0, len(alerts) - 1)
        else:
            idx = (cycle - 1) % len(alerts)

        alert_template = alerts[idx]
        alert = inject_fresh_alert(alert_template, cycle)

        log("--- Cycle {}: {} (severity={}) ---".format(
            cycle, alert["alert_type"], alert.get("severity", "?")))

        try:
            result = agent.run(alert, thread_id="loop-c{}".format(cycle))

            report = result.get("incident_report", {})
            if not report:
                report = {
                    "incident_id": "INC-{}-{}".format(alert["alert_id"], int(time.time())),
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "alert": alert,
                    "root_cause": result.get("root_cause", ""),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "action_level": result.get("action_level", ""),
                    "approval_status": result.get("approval_status", ""),
                    "verification_status": result.get("verification_status", ""),
                    "execution_result": result.get("execution_result", {}),
                    "agent_version": result.get("agent_version", "1.0.0"),
                    "cycle": cycle,
                }

            index_incident_to_css(css_client, report)
            total_incidents += 1

            rc = str(result.get("root_cause", ""))[:120]
            log("  Root cause: {}...".format(rc))
            log("  Action: {} | Approval: {} | Verify: {}".format(
                result.get("action_level", "?"),
                result.get("approval_status", "?"),
                result.get("verification_status", "?")))
            log("  Total incidents indexed: {}".format(total_incidents))

        except Exception as e:
            log("  ERROR: {}".format(e))
            import traceback
            traceback.print_exc()

        log("  Sleeping {}s until next cycle...".format(sleep_seconds))
        time.sleep(sleep_seconds)

    log("AIOps Agent Loop finished. {} incidents processed.".format(total_incidents))


if __name__ == "__main__":
    main()
