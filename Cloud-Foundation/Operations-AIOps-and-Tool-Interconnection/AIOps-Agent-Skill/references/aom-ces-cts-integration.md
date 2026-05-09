# AOM/CES/CTS SDK Integration

## SDK Client Construction Pattern

All SDK clients follow the same builder pattern:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig

credentials = BasicCredentials(
    ak=config.hwc_ak,
    sk=config.hwc_sk,
    project_id=config.hwc_project_id,
)
http_config = HttpConfig.get_default_config()
http_config.timeout = (30, 60)  # (connect, read) seconds

client = (
    ClientClass.new_builder()
    .with_http_config(http_config)
    .with_credentials(credentials)
    .with_region(ClientClass.region.value_of(config.hwc_region))
    .build()
)
```

Lazy initialization via `@property` to defer SDK imports until first use.

## AOMTools

| Method | SDK Call | Level |
|--------|----------|-------|
| `list_alarms(alarm_name?, severity?)` | `ListAlarmsRequest` | L0 |
| `show_alarm_history(alarm_id)` | `ShowAlarmHistoryRequest` | L0 |
| `list_components(app_id)` | `ListComponentsRequest` | L0 |
| `show_component_metrics(component_id, metric_names)` | `ShowComponentMetricsRequest` | L0 |

Module: `huaweicloudsdkaom.v1`, Client: `AomClient`

## CESTools

| Method | SDK Call | Level |
|--------|----------|-------|
| `list_metrics(namespace, dim_name, dim_id)` | `ListMetricsRequest` | L0 |
| `show_metric_data(metric_name, namespace, dim_name, dim_id, period, _from, to)` | `ShowMetricDataRequest` | L0 |
| `list_alarms(alarm_name?)` | `ListAlarmsRequest` | L0 |
| `show_alarm_history(alarm_id)` | `ShowAlarmHistoryRequest` | L0 |

Module: `huaweicloudsdkces.v1`, Client: `CesClient`

## CTSTools

| Method | SDK Call | Level |
|--------|----------|-------|
| `list_traces(resource_type?, resource_id?, from_time?, to_time?)` | `ListTracesRequest` | L0 |
| `list_trace_quotas()` | `ListTraceQuotasRequest` | L0 |

Module: `huaweicloudsdkcts.v3`, Client: `CtsClient`

## AOMCESConnector (Unified Interface)

Combines AOM and CES into a single monitoring interface with caching:

| Method | Source | Returns |
|--------|--------|---------|
| `get_current_metrics(resource_type, resource_id, metric_names?)` | CES | `{metric_name: value}` |
| `get_alarm_state(resource_type?, resource_id?, severity?)` | AOM | `[alarm dicts]` |
| `assess_health(resource_type, resource_id, thresholds?)` | CES | `{status, violations, metrics}` |
| `get_metric_history(resource_type, resource_id, metric_name, period_minutes)` | CES | `[{timestamp, value}]` |

### Health Assessment

```python
health = connector.assess_health("ecs", server_id)
# Returns:
# {
#   "status": "healthy" | "degraded" | "critical",
#   "violations": [{"metric": "cpu_utilization", "value": 92, "threshold": 90, "level": "critical"}],
#   "metrics": {"cpu_utilization": 92.0, "mem_utilization": 72.0}
# }
```

### Default Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| `cpu_utilization` | 80% | 90% |
| `mem_utilization` | 85% | 95% |
| `disk_utilization` | 80% | 90% |
| `disk_read_await` | 20ms | 50ms |

## CTSConnector (Audit Trail Interface)

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_recent_events(resource_id?, resource_type?, minutes=60)` | `[event dicts]` | Recent CTS events for a resource |
| `find_config_changes(resource_id, from_time, to_time)` | `[change dicts]` | Filtered for update/create/delete/modify/resize/restart |
| `correlate_with_alert(alert, window_minutes=30)` | `[change dicts]` | CTS events near alert time for same resource |

## Caching Strategy

```python
from cachetools import TTLCache

class AOMCESConnector:
    _metric_cache = TTLCache(maxsize=100, ttl=60)   # 60s for metrics
    _alarm_cache  = TTLCache(maxsize=50,  ttl=300)  # 5min for alarms
```

- **Metric cache**: 60-second TTL, 100 entries. Avoids hammering CES API during observe and verify nodes.
- **Alarm cache**: 300-second TTL, 50 entries. Alarm state changes less frequently.
- **CTS**: No cache (always fresh audit trail needed for correlation).
- Cache keys include resource_type, resource_id, and metric names for precise invalidation.
