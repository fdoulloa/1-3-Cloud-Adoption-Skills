"""Generate synthetic alert/metric data for AIOps Agent testing."""

import json
from datetime import datetime, timezone
from pathlib import Path

DEMO_DIR = Path(__file__).parent.parent / "demo"


def generate_alerts() -> list[dict]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return [
        {
            "alert_id": "ALERT-CSS-CPU-001",
            "alert_source": "aom",
            "alert_type": "css_cluster_high_cpu",
            "severity": "high",
            "resource_type": "css_cluster",
            "resource_id": "cluster-abc123",
            "resource_name": "prod-css-cluster",
            "region": "la-north-2",
            "metric_name": "cpu_utilization",
            "metric_value": 92.5,
            "threshold": 85.0,
            "timestamp": now,
            "description": "CSS cluster CPU utilization exceeded 85% for 5 minutes",
        },
        {
            "alert_id": "ALERT-ECS-CPU-001",
            "alert_source": "ces",
            "alert_type": "ecs_cpu_high",
            "severity": "high",
            "resource_type": "ecs_server",
            "resource_id": "server-def456",
            "resource_name": "prod-app-server",
            "region": "la-north-2",
            "metric_name": "cpu_utilization",
            "metric_value": 88.3,
            "threshold": 85.0,
            "timestamp": now,
            "description": "ECS CPU utilization exceeded 85% for 5 minutes",
        },
        {
            "alert_id": "ALERT-CCE-POD-001",
            "alert_source": "aom",
            "alert_type": "cce_pod_crash_loop",
            "severity": "high",
            "resource_type": "cce_pod",
            "resource_id": "pod-ghi789",
            "resource_name": "api-gateway-pod",
            "region": "la-north-2",
            "metric_name": "pod_restart_count",
            "metric_value": 12,
            "threshold": 5,
            "timestamp": now,
            "description": "CCE Pod in CrashLoopBackOff, 12 restarts in 10 minutes",
        },
        {
            "alert_id": "ALERT-GAUSSDB-SQL-001",
            "alert_source": "ces",
            "alert_type": "gaussdb_slow_sql",
            "severity": "medium",
            "resource_type": "gaussdb_instance",
            "resource_id": "db-jkl012",
            "resource_name": "prod-order-db",
            "region": "la-north-2",
            "metric_name": "slow_sql_count",
            "metric_value": 47,
            "threshold": 10,
            "timestamp": now,
            "description": "GaussDB slow SQL count exceeded 10 in 5 minutes",
        },
        {
            "alert_id": "ALERT-VPN-DISC-001",
            "alert_source": "ces",
            "alert_type": "vpn_gateway_disconnect",
            "severity": "high",
            "resource_type": "vpn_connection",
            "resource_id": "vpn-mno345",
            "resource_name": "prod-dc-vpn",
            "region": "la-north-2",
            "metric_name": "connection_status",
            "metric_value": 0,
            "threshold": 1,
            "timestamp": now,
            "description": "VPN gateway connection status DOWN",
        },
        {
            "alert_id": "ALERT-CBR-BACKUP-001",
            "alert_source": "ces",
            "alert_type": "cbr_backup_failure",
            "severity": "high",
            "resource_type": "cbr_backup",
            "resource_id": "backup-pqr678",
            "resource_name": "prod-daily-backup",
            "region": "la-north-2",
            "metric_name": "backup_status",
            "metric_value": 2,
            "threshold": 1,
            "timestamp": now,
            "description": "CBR backup task failed (status=2)",
        },
    ]


def generate_metrics() -> list[dict]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return [
        {"timestamp": now, "metric_name": "cpu_utilization", "namespace": "SYS.CSS",
         "resource_id": "cluster-abc123", "value": 92.5, "unit": "%"},
        {"timestamp": now, "metric_name": "mem_utilization", "namespace": "SYS.CSS",
         "resource_id": "cluster-abc123", "value": 78.3, "unit": "%"},
        {"timestamp": now, "metric_name": "disk_utilization", "namespace": "SYS.CSS",
         "resource_id": "cluster-abc123", "value": 65.1, "unit": "%"},
    ]


def generate_cts_events() -> list[dict]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return [
        {"timestamp": now, "trace_name": "updateCssCluster", "trace_type": "ConsoleApi",
         "resource_id": "cluster-abc123", "resource_type": "css_cluster",
         "user_name": "admin", "code": 200},
    ]


def generate_lts_logs() -> list[dict]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return [
        {"timestamp": now, "source_service": "css", "resource_id": "cluster-abc123",
         "severity": "warning", "message": "High CPU usage detected on data node 1",
         "log_level": "WARN"},
        {"timestamp": now, "source_service": "css", "resource_id": "cluster-abc123",
         "severity": "error", "message": "Query timeout after 30s on index ops_logs-2026.05",
         "log_level": "ERROR"},
    ]


def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    alerts = generate_alerts()
    (DEMO_DIR / "demo_alerts.json").write_text(json.dumps(alerts, indent=2))

    metrics = generate_metrics()
    (DEMO_DIR / "demo_metrics.json").write_text(json.dumps(metrics, indent=2))

    cts_events = generate_cts_events()
    (DEMO_DIR / "demo_cts_events.json").write_text(json.dumps(cts_events, indent=2))

    lts_logs = generate_lts_logs()
    (DEMO_DIR / "demo_lts_logs.json").write_text(json.dumps(lts_logs, indent=2))

    print(f"Generated demo data in {DEMO_DIR}/")
    print(f"  Alerts: {len(alerts)}")
    print(f"  Metrics: {len(metrics)}")
    print(f"  CTS events: {len(cts_events)}")
    print(f"  LTS logs: {len(lts_logs)}")


if __name__ == "__main__":
    main()
