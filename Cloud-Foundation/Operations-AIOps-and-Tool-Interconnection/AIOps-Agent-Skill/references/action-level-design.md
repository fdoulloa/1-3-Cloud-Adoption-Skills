# Action Level Design (L0/L1/L2/L3)

## Level Definitions

| Level | Name | Description | Approval |
|-------|------|-------------|----------|
| L0 | Read-only | Query and observe operations. No side effects. | Auto-approved |
| L1 | Suggest | Agent recommends actions but does not execute. Human decides. | Auto-approved |
| L2 | Approve + Execute | Execute after human approval via HMAC token. | Required (15-min TTL) |
| L3 | Forbidden | Never allowed. Would cause data loss or security breach. | Blocked |

## L0 Read-Only Tools

```
aom.list_alarms, aom.show_alarm_history, aom.list_components, aom.show_component_metrics
ces.list_metrics, ces.show_metric_data, ces.list_alarms, ces.show_alarm_history
cts.list_traces, cts.list_trace_quotas
css.get_cluster_info, css.get_cluster_status, css.get_data_node_count
ecs.show_server, ecs.list_servers
cce.list_pods, cce.show_pod
css_log.query, css_log.correlate, css_log.search_incidents
prometheus.query, prometheus.query_range, prometheus.get_alerts
```

## L1 Suggest Tools

```
runbook.lookup, runbook.render, runbook.preview
diagnosis.explain, diagnosis.recommend
```

## L2 Approve + Execute Tools

```
css.scale_out_data_nodes, css.scale_in_data_nodes
ecs.resize_server, ecs.reboot_server
cce.restart_pod, cce.scale_deployment
functiongraph.invoke_remediation
vpn.recreate_connection
cbr.retry_backup
```

## L3 Forbidden Tools

| Tool | Rationale |
|------|-----------|
| `ecs.delete_server` | Destroys compute instance and local data |
| `css.delete_cluster` | Destroys search cluster and all indexed data |
| `cce.delete_cluster` | Destroys container cluster and all workloads |
| `obs.delete_bucket` | Destroys object storage and all objects |
| `iam.delete_user` | Removes IAM identity, breaks access |
| `iam.delete_role` | Removes IAM role, breaks authorization |
| `vpc.delete_vpc` | Destroys network, disconnects all resources |
| `cbr.delete_vault` | Destroys backup vault and all backups |

## Enforcement Flow

```python
result = policy.enforce(tool_name, approval_token=token)
# Returns: {"allowed": bool, "level": str, "reason": str, "requires_approval": bool}
```

1. Tool is classified via `action_levels.json` mapping
2. Unknown tools default to **L3** (safest default)
3. Forbidden tools list checked from `forbidden_actions.json`
4. L0/L1: auto-approved, no token needed
5. L2: requires valid approval token
6. L3: always blocked

## Approval Token Design

### HMAC-SHA256 Token

```
message = f"{tool_name}:{params_hash}:{timestamp}:{requested_by}"
token   = HMAC-SHA256(message, HWC_SECRET_ACCESS_KEY)
```

- **Secret**: Derived from `HWC_SECRET_ACCESS_KEY` (never stored separately)
- **params_hash**: SHA-256 of JSON-serialized params (sort_keys=True) to bind token to specific action
- **TTL**: 15 minutes (configurable via `APPROVAL_TTL_SECONDS`)
- **Validation**: Checks token exists, not expired, params match, tool name match

### Token Lifecycle

```python
# 1. Generate (in approve_node)
request = approval.generate(tool_name="css.scale_out_data_nodes",
                            params={"cluster_id": "xxx", "node_count": 2},
                            requested_by="aiops-agent")
# Returns: {"token": "abc123...", "expires_at": "2026-05-08T10:15:00Z", ...}

# 2. SMN notification sent to approver
#    Subject: "AIOps Approval Required: css.scale_out_data_nodes"
#    Body: token, tool, params, expires_at

# 3. Validate (when approver responds)
result = approval.validate(token, tool_name, params, approver="admin@company.com")
# Returns: {"valid": True/False, "expired": True/False, "approver": "..."}

# 4. Approve or Reject
approval.approve(token, approver_identity="admin@company.com")
approval.reject(token, rejector_identity="admin@company.com", reason="risk too high")
```

## SMN Notification for L2 Approvals

When an L2 approval token is generated, an SMN notification is sent:

- **Topic**: `aiops-approval` (provisioned via Terraform)
- **Protocol**: Email
- **Endpoint**: Configured via `SMN_APPROVAL_EMAIL`
- **Content**: Tool name, parameters, token, expiration time

## Routing After Approval

| Condition | Route |
|-----------|-------|
| L0/L1 auto-approved | Skip Execute, go to Report |
| L2 + approved | Proceed to Execute |
| L2 + rejected | Go to Report (no execution) |
| L2 + expired | Go to Report (no execution) |
| L3 blocked | Go to Report (escalation) |
