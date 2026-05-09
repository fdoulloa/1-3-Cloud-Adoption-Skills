# Runbook: CCE Pod Crash Loop

**Alert Type**: `cce_pod_crash_loop`
**Severity**: High
**Action Level**: L2 (requires approval)

## Symptoms

- CCE Pod in CrashLoopBackOff state
- Container exits repeatedly
- Application endpoint returns 5xx errors

## Root Causes

1. Application error (unhandled exception, OOM)
2. Configuration error (missing env var, wrong config)
3. Image pull failure (wrong tag, registry auth)
4. Resource limits too low (OOMKilled)
5. Dependency unavailable (database, API)

## Diagnosis Steps

## Step 1: Check pod status and events
- Tool: `cce.show_pod`
- Level: L0
- Params: `{"cluster_id": "{{cluster_id}}", "namespace": "{{namespace}}", "pod_name": "{{pod_name}}"}`

## Step 2: Check recent application logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND severity:error"}`

## Step 3: Check CTS for recent deployment changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Step 4: Restart the pod/deployment
- Tool: `cce.restart_pod`
- Level: L2
- Params: `{"cluster_id": "{{cluster_id}}", "namespace": "{{namespace}}", "deployment_name": "{{deployment_name}}"}`

**Note**: Restart is a first-aid measure. If the pod crashes again after restart, the root cause must be fixed (code, config, or resource limits).

## Step 5: Verify pod is running
- Tool: `cce.show_pod`
- Level: L0
- Params: `{"cluster_id": "{{cluster_id}}", "namespace": "{{namespace}}", "pod_name": "{{pod_name}}"}`

## Rollback

If restart does not resolve:
1. Check if a recent deployment caused the issue (CTS audit)
2. If so, rollback to previous deployment version
3. Escalate to application team with pod logs and events
