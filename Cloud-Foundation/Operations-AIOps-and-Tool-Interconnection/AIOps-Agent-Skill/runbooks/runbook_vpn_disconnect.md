# Runbook: VPN Gateway Disconnect

**Alert Type**: `vpn_gateway_disconnect`
**Severity**: High
**Action Level**: L2 (requires approval)

## Symptoms

- VPN gateway connection status is DOWN
- Cross-region/cross-cloud connectivity lost
- Dependent services report connection timeouts

## Root Causes

1. Peer gateway configuration change
2. IKE/IPsec negotiation failure
3. Network route change
4. Peer gateway unreachable
5. Certificate or PSK expiry

## Diagnosis Steps

## Step 1: Check VPN gateway status
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "vpn_connection_status", "namespace": "SYS.VPN", "dim_id": "{{resource_id}}"}`

## Step 2: Check CTS for recent VPN config changes
- Tool: `cts.list_traces`
- Level: L0
- Params: `{"resource_id": "{{resource_id}}"}`

## Step 3: Check related network logs
- Tool: `css_log.query`
- Level: L0
- Params: `{"index": "ops_logs-*", "query": "resource_id:{{resource_id}} AND source_service:vpn"}`

## Step 4: Recreate VPN connection
- Tool: `vpn.recreate_connection`
- Level: L2
- Params: `{"vpn_connection_id": "{{resource_id}}"}`

**Note**: Recreating the connection re-establishes IKE negotiation. If the peer gateway has changed, the connection config must be updated first.

## Step 5: Verify connection is UP
- Tool: `ces.show_metric_data`
- Level: L0
- Params: `{"metric_name": "vpn_connection_status", "namespace": "SYS.VPN", "dim_id": "{{resource_id}}"}`

## Rollback

If recreation does not resolve:
1. Check peer gateway reachability (ping/traceroute)
2. Verify IKE proposal and PSK/certificate match
3. Escalate to network team
