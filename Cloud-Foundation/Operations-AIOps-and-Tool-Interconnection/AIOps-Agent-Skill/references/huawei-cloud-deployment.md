# Huawei Cloud Deployment Defaults

## Required SDK Packages

```
# Huawei Cloud SDK
huaweicloudsdkcore
huaweicloudsdkaom
huaweicloudsdkces
huaweicloudsdkcts
huaweicloudsdkcss
huaweicloudsdkecs
huaweicloudsdkcce
huaweicloudsdkfunctiongraph
huaweicloudsdklts
huaweicloudsdkvpc
huaweicloudsdksmn
huaweicloudsdkobs

# OpenSearch
opensearch-py

# Agent framework
langgraph
llama-index-core
llama-index-vector-stores-opensearch

# LLM client (OpenAI-compatible for MaaS)
openai

# Monitoring
prometheus-client

# Tracing
opentelemetry-api
opentelemetry-sdk
traceloop-sdk

# Utilities
cachetools
python-dotenv
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HWC_ACCESS_KEY_ID` | Yes | - | Huawei Cloud AK |
| `HWC_SECRET_ACCESS_KEY` | Yes | - | Huawei Cloud SK |
| `HWC_REGION` | Yes | `la-north-2` | Region |
| `HWC_PROJECT_ID` | Yes | - | Project ID |
| `CSS_CLUSTER_ID` | Yes | - | CSS cluster ID |
| `CSS_ENDPOINT` | Yes | - | CSS endpoint URL |
| `CSS_USERNAME` | No | `admin` | CSS auth username |
| `CSS_PASSWORD` | Yes | - | CSS auth password |
| `HUAWEI_MAAS_API_BASE` | No | `https://maas-api.la-north-2.myhuaweicloud.com/v1` | MaaS endpoint |
| `HUAWEI_MAAS_API_KEY` | Yes | - | MaaS API key |
| `HUAWEI_MAAS_MODEL` | No | `glm-5.1` | LLM model |
| `LTS_LOG_GROUP_ID` | For ingestion | - | LTS log group |
| `LTS_LOG_TOPIC_ID` | For ingestion | - | LTS log topic |
| `CTS_TRACKER_NAME` | No | `system` | CTS tracker |
| `SMN_TOPIC_URN` | For L2 approval | - | SMN topic URN |
| `SMN_APPROVAL_EMAIL` | For L2 approval | - | Approver email |
| `OBS_BUCKET_NAME` | For reports | - | OBS bucket |
| `APPROVAL_TTL_SECONDS` | No | `900` | Token TTL (15 min) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | - | OTLP collector |
| `DEMO_MODE` | No | `false` | Use synthetic data |

## Terraform Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `huaweicloud_vpc.main` | VPC | `192.168.0.0/16` |
| `huaweicloud_vpc_subnet.main` | Subnet | `192.168.0.0/24` |
| `huaweicloud_networking_secgroup.main` | Security Group | Agent + CSS access |
| `huaweicloud_css_cluster.main` | CSS | 3-node OpenSearch cluster |
| `huaweicloud_compute_instance.agent` | ECS | Agent runtime (Ubuntu 22.04) |
| `huaweicloud_lts_group.ops` | LTS Group | Log aggregation |
| `huaweicloud_lts_topic.*` | LTS Topics | css-logs, ecs-logs, cce-logs, audit-logs |
| `huaweicloud_smn_topic.approval` | SMN | Approval notifications |
| `huaweicloud_obs_bucket.main` | OBS | Runbooks, reports, state |
| `huaweicloud_fgs_function.*` | FunctionGraph | Remediation functions |

Provider: `huaweicloud/huaweicloud ~> 1.60`, Terraform `>= 1.5`

## Security Group Rules

| Rule | Protocol | Port | Source | Purpose |
|------|----------|------|--------|---------|
| css_api | TCP | 9200 | subnet_cidr | OpenSearch API |
| https | TCP | 443 | operator_cidr | Management |
| ssh | TCP | 22 | operator_cidr | Operator access |
| agent_api | TCP | 8000 | subnet_cidr | Agent webhook |
| egress | All | All | 0.0.0.0/0 | Outbound |

## ECS Installation Steps

```bash
# 1. Install Python 3.11+
sudo apt update && sudo apt install -y python3.11 python3.11-venv

# 2. Create virtual environment
python3.11 -m venv /opt/aiops-agent/venv
source /opt/aiops-agent/venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with actual credentials

# 5. Provision CSS index templates
for template in index_templates/*.json; do
    curl -X PUT "https://${CSS_ENDPOINT}:9200/_index_template/$(basename $template .json)" \
         -H "Content-Type: application/json" \
         -u "${CSS_USERNAME}:${CSS_PASSWORD}" \
         -d @"$template"
done

# 6. Start agent (systemd or screen)
python -m agent.ops_agent_state  # or use scripts/run_agent_demo.py
```

## Verification Checklist

- [ ] CSS cluster reachable: `curl https://<endpoint>:9200 -u admin:<password>`
- [ ] Index templates applied: `curl https://<endpoint>:9200/_index_template`
- [ ] LTS ingestion working: `python scripts/ingest_lts_to_css.py`
- [ ] CTS ingestion working: `python scripts/ingest_cts_to_css.py`
- [ ] MaaS API accessible: verify with a test completion call
- [ ] SMN topic subscribed: Check SMN console for email confirmation
- [ ] FunctionGraph functions deployed: Check FunctionGraph console
- [ ] Agent processes alert end-to-end: `python scripts/run_agent_demo.py`
- [ ] OpenTelemetry spans emitted: Check OTLP collector or console output
