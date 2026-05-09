# CSS Replacing Splunk Pipeline

## LTS -> CSS Log Ingestion

```
LTS Log Group/Topic ──► LTS SDK (list_logs) ──► transform_lts_record() ──► CSS ops_logs-YYYY.MM.dd
```

```python
def transform_lts_record(record: dict) -> dict:
    return {
        "timestamp": record.get("time"),
        "source_service": record.get("service", "unknown"),
        "source_type": "lts",
        "resource_id": record.get("resource_id", ""),
        "resource_type": record.get("resource_type", ""),
        "region": record.get("region", ""),
        "severity": record.get("severity", "info"),
        "log_level": record.get("level", "INFO"),
        "message": record.get("content", ""),
        "error_code": record.get("error_code", ""),
        "trace_id": record.get("trace_id", ""),
        "correlation_id": record.get("correlation_id", ""),
        "host": record.get("host", ""),
        "app": record.get("app", ""),
    }
```

## CTS -> CSS Audit Ingestion

```
CTS Tracker ──► CTS SDK (list_traces) ──► transform_cts_event() ──► CSS ops_cts-YYYY.MM.dd
```

```python
def transform_cts_event(event: dict) -> dict:
    return {
        "timestamp": event.get("time"),
        "trace_id": event.get("id", ""),
        "trace_name": event.get("trace_name", ""),
        "trace_type": event.get("trace_type", ""),
        "trace_status": event.get("trace_status", ""),
        "resource_id": event.get("resource_id", ""),
        "resource_type": event.get("resource_type", ""),
        "region": event.get("region", ""),
        "user_name": event.get("user", {}).get("name", ""),
        "user_domain": event.get("user", {}).get("domain", ""),
        "api_version": event.get("api_version", ""),
        "code": event.get("code", 0),
        "correlation_id": event.get("correlation_id", ""),
    }
```

## Common Field Schema (Replacing Splunk CIM)

| Field | Type | Present In | Purpose |
|-------|------|-----------|---------|
| `timestamp` | date | all indices | Unified time field |
| `source_service` | keyword | ops_logs | Originating service |
| `resource_id` | keyword | all indices | Cross-index correlation key |
| `resource_type` | keyword | all indices | Resource category (ecs, css, cce) |
| `region` | keyword | all indices | Huawei Cloud region |
| `severity` | keyword | ops_logs, ops_alerts | Alert/log severity |
| `correlation_id` | keyword | all indices | Cross-event correlation |
| `trace_id` | keyword | ops_logs, ops_cts | OpenTelemetry trace ID |

## 5 CSS Index Templates

| Template | Pattern | Shards | Purpose |
|----------|---------|--------|---------|
| `ops_logs_template` | `ops_logs-*` | 3 | Application and infrastructure logs from LTS |
| `ops_metrics_template` | `ops_metrics-*` | 3 | AOM/CES metric time series |
| `ops_alerts_template` | `ops_alerts-*` | 3 | AOM/CES alarm events |
| `ops_cts_template` | `ops_cts-*` | 3 | CTS audit trail events |
| `ops_incidents_template` | `ops_incidents-*` | 1 | Agent incident reports |

Daily rollover: `ops_logs-2026.05.08`, `ops_cts-2026.05.08`, etc.

## OpenSearch Anomaly Detection + Alerting

CSS includes OpenSearch Anomaly Detection and Alerting plugins:

- **Anomaly Detection**: Create detectors on `ops_metrics-*` indices for cpu_utilization, mem_utilization, disk_utilization. Uses random cut forest (RCF) algorithm.
- **Alerting**: Define monitors on `ops_logs-*` and `ops_alerts-*` indices. Triggers send alerts to the AIOps agent webhook.

## Splunk vs CSS/OpenSearch Capability Comparison

| Capability | Splunk | CSS/OpenSearch |
|-----------|--------|----------------|
| Log ingestion | Universal Forwarder | LTS SDK + opensearch-py bulk |
| Search language | SPL | OpenSearch DSL / SQL |
| Common schema | CIM (Common Information Model) | Custom field schema (see above) |
| Anomaly detection | MLTK app | Anomaly Detection plugin (RCF) |
| Alerting | Saved searches + alert actions | Alerting plugin + monitors |
| Audit trail | Add-on for CloudTrail | CTS SDK + ops_cts index |
| Dashboards | Splunk Web | OpenSearch Dashboards |
| Vector search | Not native | OpenSearch k-NN plugin |
| Cost model | GB/day license | CSS node hourly rate |

## Cost Advantage

| Factor | Splunk | CSS/OpenSearch |
|--------|--------|----------------|
| Licensing | $150+/GB/day enterprise | CSS node hourly (ess.spec-4u8g ~$0.5/hr) |
| 3-node cluster | ~$15K/month (100GB/day) | ~$1K/month (3 nodes) |
| Data retention | License-limited | OBS-backed, configurable per index |
| Vendor lock-in | Proprietary SPL, formats | OpenSearch (open source fork of ES 7.10.2) |
