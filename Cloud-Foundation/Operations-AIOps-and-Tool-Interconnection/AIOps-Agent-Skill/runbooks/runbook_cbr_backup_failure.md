# Runbook: CBR Backup Failure

**Alert Type**: `cbr_backup_failure`
**Severity**: High
**Action Level**: L2 (requires approval)

## Symptoms

- CBR backup task status is FAILED
- Backup not completed within expected window
- Vault backup count not increasing

## Root Causes

1. Insufficient vault capacity
2. Source resource unavailable during backup window
3. Network timeout during data transfer
4. Agent installation issue on ECS
5. Backup policy misconfiguration

## Diagnosis Steps

## Step 1: Check backup vault status
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "backup_status", "namespace": "SYS.CBR", "dim_id": "{{resource_id}}"}`

## Step 2: Check CTS for recent backup policy changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Step 3: Check backup error logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND source_service:cbr AND severity:error"}`

## Step 4: Retry backup
- Tool: `cbr.retry_backup`
- Level: L2
- Params: `{"backup_id": "{{resource_id}}"}`

## Step 5: Verify backup succeeded
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "backup_status", "namespace": "SYS.CBR", "dim_id": "{{resource_id}}"}`

## Rollback

If retry fails:
1. Check vault capacity and expand if needed
2. Verify backup agent is running on source ECS
3. Check if source resource was in a transitional state
4. Escalate to backup team
