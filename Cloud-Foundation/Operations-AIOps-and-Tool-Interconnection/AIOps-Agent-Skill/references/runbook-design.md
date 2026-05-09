# Runbook Template System

## RunbookEngine API

| Method | Returns | Description |
|--------|---------|-------------|
| `lookup_runbook(alert_type)` | `str or None` | Map alert type to runbook filename |
| `load_runbook(runbook_id)` | `str or None` | Load raw runbook content from file |
| `render_runbook(runbook_id, context)` | `list[dict]` | Substitute variables and parse into steps |
| `preview_runbook(runbook_id, context)` | `str` | Human-readable preview without execution |

## Alert Type to Runbook Mapping

| Alert Type | Runbook File |
|------------|-------------|
| `css_cluster_high_cpu` | `runbook_css_high_cpu.md` |
| `ecs_cpu_high` | `runbook_ecs_cpu_high.md` |
| `cce_pod_crash_loop` | `runbook_cce_pod_crash.md` |
| `gaussdb_slow_sql` | `runbook_gaussdb_slow_sql.md` |
| `vpn_gateway_disconnect` | `runbook_vpn_disconnect.md` |
| `cbr_backup_failure` | `runbook_cbr_backup_failure.md` |

## Template Variable Substitution

Runbooks use `{{variable}}` placeholders. The engine substitutes them with context values:

```python
context = {
    "alert_type": "css_cluster_high_cpu",
    "resource_id": "cluster-abc",
    "resource_type": "css",
    "region": "la-north-2",
    "metric_value": "92.5",
    "threshold": "80",
    "root_cause": "Insufficient data nodes for query load",
}

steps = runbook_engine.render_runbook("runbook_css_high_cpu.md", context)
```

Substitution supports dotted paths: `{{alert.severity}}` resolves `context["alert"]["severity"]`.

## Step Parsing

Runbooks use markdown headers to define steps:

```markdown
## Step 1: Check current resource metrics
- Tool: `css.get_cluster_info`
- Level: L0
- Params: `{"cluster_id": "{{resource_id}}"}`

## Step 2: Scale out data nodes
- Tool: `css.scale_out_data_nodes`
- Level: L2
- Params: `{"cluster_id": "{{resource_id}}", "node_count": 2}`
```

Parsed into:
```python
[
    {"step": 1, "action": "Check current resource metrics",
     "tool": "css.get_cluster_info", "level": "L0",
     "params": {"cluster_id": "cluster-abc"}},
    {"step": 2, "action": "Scale out data nodes",
     "tool": "css.scale_out_data_nodes", "level": "L2",
     "params": {"cluster_id": "cluster-abc", "node_count": 2}},
]
```

## 6 Scenario Runbooks

| Runbook | Scenario | Steps | Max Level |
|---------|----------|-------|-----------|
| `runbook_css_high_cpu.md` | CSS cluster CPU high | 5 | L2 (scale-out) |
| `runbook_ecs_cpu_high.md` | ECS instance CPU high | 5 | L1 (suggest resize) |
| `runbook_cce_pod_crash.md` | CCE pod crash loop | 5 | L2 (restart pod) |
| `runbook_gaussdb_slow_sql.md` | GaussDB slow SQL | 5 | L1 (query optimization) |
| `runbook_vpn_disconnect.md` | VPN gateway disconnect | 5 | L2 (recreate connection) |
| `runbook_cbr_backup_failure.md` | CBR backup failure | 5 | L2 (retry backup) |

## Generic Template

`runbook_template.md` provides a 5-step structure:

1. **Check current resource metrics** (L0)
2. **Check recent logs** (L0) via `css_log.query`
3. **Check CTS for recent changes** (L0) via `cts.list_traces`
4. **Execute remediation** (variable level) via `{{remediation_tool}}`
5. **Verify resolution** (L0)

## Preview Output

```
Runbook: runbook_css_high_cpu.md
========================================

Step 1: Check current resource metrics
  Tool: css.get_cluster_info
  Level: L0
  Params: {"cluster_id": "cluster-abc"}

Step 2: Scale out data nodes
  Tool: css.scale_out_data_nodes
  Level: L2
  Params: {"cluster_id": "cluster-abc", "node_count": 2}
```

## FunctionGraph Execution

L2 remediation steps execute via FunctionGraph:

```python
# In remediation_executor.py
result = executor.execute("css.scale_out_data_nodes", params)
# Internally invokes: functiongraph.invoke_function(function_urn, params)
```

Pre-provisioned FunctionGraph functions: `css_scale_out`, `ecs_reboot`, `cce_restart_pod`, `vpn_reconnect`.
