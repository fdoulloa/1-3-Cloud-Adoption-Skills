# Runbook: CSS Cluster High CPU

**Alert Type**: `css_cluster_high_cpu`
**Severity**: High
**Action Level**: L2 (requires approval)

## Symptoms

- CSS cluster CPU utilization exceeds 85% for 5+ minutes
- Query latency increases
- Indexing throughput drops

## Root Causes

1. Sudden increase in query volume
2. Heavy aggregation queries
3. Insufficient data nodes for current load
4. Index mapping explosion

## Diagnosis Steps

## Step 1: Check current cluster metrics
- Tool: `css.get_cluster_info`
- Level: L0
- Params: `{"cluster_id": "{{resource_id}}"}`

## Step 2: Check data node count and distribution
- Tool: `css.get_data_node_count`
- Level: L0
- Params: `{"cluster_id": "{{resource_id}}"}`

## Step 3: Check recent query patterns in logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND severity:high"}`

## Step 4: Scale out data nodes
- Tool: `css.scale_out_data_nodes`
- Level: L2
- Params: `{"cluster_id": "{{resource_id}}", "node_count": 2}`

**Scaling logic** (reuses css-testing hysteresis pattern):
- If CPU > 90%: add 3 nodes
- If CPU > 85%: add 2 nodes
- If CPU > 80%: add 1 node
- Cooldown: 10 minutes between scale operations
- Max nodes: 20 (configurable)

## Step 5: Verify CPU normalized
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "cpu_utilization", "namespace": "SYS.CSS", "dim_id": "{{resource_id}}"}`

## Rollback

If scaling does not resolve within 15 minutes:
1. Check for runaway queries and kill them via Kibana
2. Review index mappings for mapping explosion
3. Escalate to CSS support team
