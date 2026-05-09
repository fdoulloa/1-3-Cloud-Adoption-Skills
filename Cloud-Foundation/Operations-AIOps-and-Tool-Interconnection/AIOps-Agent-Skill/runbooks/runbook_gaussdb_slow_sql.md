# Runbook: GaussDB Slow SQL

**Alert Type**: `gaussdb_slow_sql`
**Severity**: Medium
**Action Level**: L1 (suggest only)

## Symptoms

- GaussDB query execution time exceeds threshold (>1s)
- Database CPU utilization high
- Application latency increases

## Root Causes

1. Missing index on queried columns
2. Inefficient query (full table scan, N+1)
3. Table statistics stale (ANALYZE not run)
4. Lock contention from concurrent writes
5. Insufficient database resources

## Diagnosis Steps

## Step 1: Check database metrics
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "cpu_utilization", "namespace": "SYS.GaussDB", "dim_id": "{{resource_id}}"}`

## Step 2: Query slow SQL log from CSS
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND source_service:gaussdb AND log_level:WARN"}`

## Step 3: Check CTS for recent schema changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Recommendation (L1 - Suggest Only)

This runbook does NOT auto-execute. It generates a recommendation:

1. If missing index: Suggest `CREATE INDEX` statement with column analysis
2. If stale statistics: Suggest `ANALYZE` on affected tables
3. If inefficient query: Suggest query rewrite with EXPLAIN ANALYZE output
4. If resource bottleneck: Suggest scaling the GaussDB instance

**Human DBA decides whether to proceed with the suggested optimization.**
