# Runbook: ECS CPU High

**Alert Type**: `ecs_cpu_high`
**Severity**: High
**Action Level**: L1 (suggest only)

## Symptoms

- ECS instance CPU utilization exceeds 85% for 5+ minutes
- Application response time increases
- SSH access may be slow

## Root Causes

1. Application workload spike
2. Runaway process (memory leak, infinite loop)
3. Insufficient instance flavor for workload
4. Scheduled batch job or cron

## Diagnosis Steps

## Step 1: Check current ECS metrics
- Tool: `ecs.show_server`
- Level: L0
- Params: `{"server_id": "{{resource_id}}"}`

## Step 2: Check CES metric history
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "cpu_utilization", "namespace": "SYS.ECS", "dim_id": "{{resource_id}}"}`

## Step 3: Check recent processes in logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND log_level:ERROR"}`

## Step 4: Check CTS for recent changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Recommendation (L1 - Suggest Only)

This runbook does NOT auto-execute. It generates a recommendation:

1. If CPU spike is transient (batch job): No action needed, monitor
2. If CPU is sustained and instance is undersized: Suggest `ecs.resize_server` to larger flavor
3. If runaway process detected: Suggest SSH in and kill process, or `ecs.reboot_server`

**Human decides whether to proceed with the suggested action.**
