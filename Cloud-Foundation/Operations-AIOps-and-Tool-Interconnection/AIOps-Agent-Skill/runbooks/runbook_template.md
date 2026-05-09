# Runbook: {{alert_type}}

**Alert Type**: `{{alert_type}}`
**Severity**: {{severity}}
**Action Level**: {{action_level}}

## Symptoms

- {{symptom_description}}

## Root Causes

1. {{root_cause_1}}
2. {{root_cause_2}}
3. {{root_cause_3}}

## Diagnosis Steps

## Step 1: Check current resource metrics
- Tool: `{{monitor_tool}}`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Step 2: Check recent logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}}"}`

## Step 3: Check CTS for recent changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Step 4: Execute remediation
- Tool: `{{remediation_tool}}`
- Level: {{action_level}}
- Params: `{{remediation_params}}`

## Step 5: Verify resolution
- Tool: `{{monitor_tool}}`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Rollback

If remediation does not resolve:
1. Check for additional root causes
2. Review recent changes in CTS audit trail
3. Escalate to {{escalation_team}}
