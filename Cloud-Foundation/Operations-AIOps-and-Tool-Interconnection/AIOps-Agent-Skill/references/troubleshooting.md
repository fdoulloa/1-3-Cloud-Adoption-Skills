# Troubleshooting

## SDK Connection Errors

**Symptom**: `ConnectionError` or `ConnectTimeout` when calling Huawei Cloud SDK.

**Causes and Fixes**:

1. **Wrong region**: Verify `HWC_REGION` matches the region where resources exist.
   ```bash
   echo $HWC_REGION  # Should be e.g. la-north-2, cn-north-4
   ```

2. **Invalid credentials**: Check AK/SK are correct and active.
   ```python
   from huaweicloudsdkcore.auth.credentials import BasicCredentials
   creds = BasicCredentials(ak=os.getenv("HWC_ACCESS_KEY_ID"),
                            sk=os.getenv("HWC_SECRET_ACCESS_KEY"),
                            project_id=os.getenv("HWC_PROJECT_ID"))
   ```

3. **Network ACL/Security Group**: Ensure ECS agent can reach Huawei Cloud API endpoints (port 443).

4. **Timeout too low**: Default timeout is (30, 60) seconds. Increase for slow regions:
   ```python
   http_config.timeout = (60, 120)
   ```

## CSS Cluster Unreachable

**Symptom**: `opensearchpy.exceptions.ConnectionError` or `AuthenticationException`.

**Causes and Fixes**:

1. **Wrong endpoint**: `CSS_ENDPOINT` must be the internal endpoint (not VPC endpoint) if agent runs in same VPC.
   ```bash
   curl -k https://<css-endpoint>:9200 -u admin:<password>
   ```

2. **Security group**: Port 9200 must allow inbound from agent subnet.
   - Check Terraform: `huaweicloud_networking_secgroup_rule.css_api`
   - Source must be `subnet_cidr`, not `0.0.0.0/0`

3. **CSS cluster not running**: Check cluster status in CSS console. Wait for `greennode` status.

4. **Wrong credentials**: `CSS_USERNAME`/`CSS_PASSWORD` must match cluster admin credentials set during creation.

5. **SSL certificate**: Agent uses `verify_certs=False`. For production, configure proper CA certs.

## MaaS API Errors

**Symptom**: `openai.APIError`, 401, or 403 from MaaS endpoint.

**Causes and Fixes**:

1. **Invalid API key**: Verify `HUAWEI_MAAS_API_KEY` is correct.
   ```bash
   curl -H "Authorization: Bearer $HUAWEI_MAAS_API_KEY" \
        $HUAWEI_MAAS_API_BASE/models
   ```

2. **Wrong model name**: Default is `glm-5.1`. Verify model is deployed in your MaaS instance.

3. **Rate limiting**: MaaS has QPS limits. Add retry logic or reduce concurrent requests.

4. **Endpoint URL**: Must include `/v1` suffix: `https://maas-api.la-north-2.myhuaweicloud.com/v1`

## Approval Token Expiration

**Symptom**: L2 action fails with `"approval_status": "expired"`.

**Causes and Fixes**:

1. **Token TTL exceeded**: Default is 15 minutes (900 seconds). If approver takes longer:
   ```bash
   export APPROVAL_TTL_SECONDS=1800  # 30 minutes
   ```

2. **Clock skew**: Agent and approver systems must have synchronized clocks (NTP).

3. **SMN delivery delay**: Email notifications may be delayed. Check SMN console for delivery status.

4. **Token not found**: If agent restarted, in-memory `_pending` dict is lost. Use persistent token storage for production.

## LangGraph State Persistence Issues

**Symptom**: Agent loses state after restart or approval wait.

**Causes and Fixes**:

1. **SQLite database missing**: Check `aiops_checkpoints.db` exists and is writable.
   ```bash
   ls -la aiops_checkpoints.db
   ```

2. **Thread ID collision**: Each alert must use a unique `thread_id`.
   ```python
   thread_id = f"alert-{alert['alert_id']}"  # Unique per alert
   ```

3. **Corrupted checkpoint**: Delete and recreate:
   ```bash
   rm aiops_checkpoints.db
   ```

4. **Concurrent access**: SQLite does not handle high concurrency. For production, consider PostgreSQL checkpointer.

## Demo Mode Fallback

**Symptom**: Agent returns synthetic data instead of real data.

**Causes and Fixes**:

1. **DEMO_MODE=true**: Check environment variable.
   ```bash
   echo $DEMO_MODE  # Should be "false" for production
   ```

2. **Missing credentials**: Agent auto-enables demo mode when required env vars are missing. Check `config.validate()`:
   ```python
   errors = config.validate()
   # ["HWC_ACCESS_KEY_ID is required", "CSS_ENDPOINT is required", ...]
   ```

3. **SDK import failure**: If Huawei Cloud SDK packages are not installed, connectors fall back to demo mode silently. Check:
   ```bash
   pip list | grep huaweicloudsdk
   ```

4. **CSS query failure**: `CSSLogCorrelator` returns empty list on query failure (not demo data). Check CSS cluster health.

## General Debugging

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check OpenTelemetry spans**: Each agent node emits a span. Review trace in console or OTLP backend.

3. **Validate config on startup**: `config = OpsAgentConfig.from_env(); errors = config.validate()`

4. **Run demo mode first**: Verify end-to-end with synthetic data before real cloud.
   ```bash
   DEMO_MODE=true python scripts/run_agent_demo.py
   ```
