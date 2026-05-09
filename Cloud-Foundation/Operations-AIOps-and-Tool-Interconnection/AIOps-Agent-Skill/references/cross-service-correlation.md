# Cross-Service Log Correlation

## CSSLogCorrelator Query Patterns

### Query Recent Logs

```python
logs = correlator.query_recent_logs(
    resource_id="i-abc123",
    service="css",
    severity="error",
    minutes=15,
    index_pattern="ops_logs-*"
)
```

Generated OpenSearch DSL:
```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"timestamp": {"gte": "2026-05-08T09:45:00Z", "lte": "2026-05-08T10:00:00Z"}}},
        {"term": {"resource_id": "i-abc123"}},
        {"term": {"source_service": "css"}},
        {"term": {"severity": "error"}}
      ]
    }
  },
  "sort": [{"timestamp": {"order": "desc"}}],
  "size": 100
}
```

### Correlate Events Across Indices

```python
events = correlator.correlate_events(
    alert={
        "resource_id": "cluster-abc",
        "region": "la-north-2",
        "timestamp": "2026-05-08T10:00:00Z"
    },
    correlation_fields=["resource_id", "region"],
    time_window_minutes=15
)
```

Searches across `ops_logs-*`, `ops_alerts-*`, `ops_cts-*` simultaneously. Each hit is annotated with `_index` and `_correlation_source`.

### Search Incident History

```python
incidents = correlator.search_incident_history(
    root_cause_keywords=["cpu", "high", "css"],
    limit=5
)
```

Uses `match` query on `root_cause` field in `ops_incidents-*` index with `minimum_should_match: 1`.

### Index Incident

```python
doc_id = correlator.index_incident({
    "incident_id": "INC-alert123-1715157600",
    "timestamp": "2026-05-08T10:00:00Z",
    "root_cause": "...",
    "recommended_action": "...",
    "action_level": "L2",
    "approval_status": "approved",
    "verification_status": "healthy",
})
```

Index name: `ops_incidents-YYYY.MM` (monthly rollover).

## Cross-Index Correlation Strategy

### Correlation Keys

| Field | Description | Example |
|-------|-------------|---------|
| `resource_id` | Primary correlation key across all indices | `i-abc123`, `cluster-xyz` |
| `region` | Huawei Cloud region | `la-north-2` |
| `correlation_id` | Application-level correlation ID | UUID set by caller |
| `timestamp` | Time window correlation (+/- N minutes) | ISO 8601 |

### Correlation Flow

```
1. Alert arrives with resource_id, region, timestamp
2. Query ops_logs-* for same resource_id within time window
3. Query ops_alerts-* for same resource_id within time window
4. Query ops_cts-* for same resource_id within time window
5. Merge and sort all events by timestamp (descending)
6. Return top 100 events with _index annotation
```

### Time Window

Default: 15 minutes before and after alert timestamp. Configurable via `time_window_minutes` parameter.

## Common Field Schema for Correlation

All indices share these fields enabling cross-index joins:

```
timestamp          date      - Unified time (strict_date_optional_time or epoch_millis)
resource_id        keyword   - Cross-index join key
resource_type      keyword   - ecs, css, cce, gaussdb, vpn, cbr
region             keyword   - Huawei Cloud region
correlation_id     keyword   - Application correlation ID
trace_id           keyword   - OpenTelemetry trace ID
```

Index-specific fields extend this base schema:

- **ops_logs**: source_service, source_type, severity, log_level, message, error_code, span_id, host, app
- **ops_metrics**: metric_name, namespace, value, unit, source, dimensions (nested)
- **ops_alerts**: alert_id, alert_type, alert_source, severity, metric_name, metric_value, threshold
- **ops_cts**: trace_id, trace_name, trace_type, trace_status, user_name, user_domain, api_version, code
- **ops_incidents**: incident_id, root_cause, confidence_score, action_level, approval_status, verification_status

## Bulk Ingest

```python
count = correlator.bulk_ingest("ops_logs-2026.05.08", documents)
```

Uses `opensearchpy.helpers.bulk` for efficient batch indexing. Returns count of successfully indexed documents.
