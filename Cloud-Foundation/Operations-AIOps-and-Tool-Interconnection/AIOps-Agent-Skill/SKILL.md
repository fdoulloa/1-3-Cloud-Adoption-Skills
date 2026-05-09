---
name: aiops-agent-skill
description: Build AIOps agents for Huawei Cloud that use CSS/OpenSearch as a Splunk replacement, integrate LTS/CTS/AOM/CES for monitoring and audit, employ LangGraph state machine orchestration with approval gates, LlamaIndex knowledge retrieval, Prometheus/Grafana metrics, and auto-remediation via FunctionGraph. Use when Codex must design, provision, or generate an AIOps Agent for automatic anomaly identification, alert governance, cross-service log correlation, runbook-driven remediation, action-level enforcement (L0 read-only, L1 suggest, L2 approve+execute, L3 forbidden), or CSS-based O&M analytics on Huawei Cloud.
---

# AI-Agent-CSS-Ops-Skill

## Overview

An intelligent O&M agent for Huawei Cloud that replaces Splunk with CSS (Cloud Search Service / OpenSearch), automates anomaly detection and remediation, and enforces safe action levels through a 4-tier policy engine.

**Core stack**: LangGraph (state machine) + LlamaIndex (knowledge) + CSS/OpenSearch (log analytics) + Huawei Cloud SDK (AOM, CES, CTS, FunctionGraph) + Prometheus/Grafana (metrics) + OpenTelemetry (tracing)

**Key innovation**: CSS + AI replaces Splunk's SIEM/SOAR capabilities at lower cost, with native Huawei Cloud integration. CSS serves as the unified data plane for logs, metrics, alerts, audit events, and incident records — replacing Splunk's Common Information Model with 5 purpose-built index templates.

## Use This Skill When

- Customer says "we can't operate our cloud" or "alerts are noise"
- Need to replace Splunk with CSS on Huawei Cloud
- Building auto-remediation for CSS, ECS, CCE, GaussDB, VPN, CBR
- Implementing alert governance with approval gates
- Designing cross-service log correlation (LTS + CTS + CSS)
- Creating O&M runbooks with action-level enforcement
- Need a state-machine-driven incident response workflow

---

## Architecture

### LangGraph State Machine

8-state flow with conditional routing:

```
Alert → Observe → Diagnose → Recommend → Preview → Approve → Execute → Verify → Report
```

**Conditional routing after Approve**:
- L0/L1 actions: Skip execution, go directly to Report
- L2 + approved: Proceed to Execute
- L2 + rejected/expired: Go to Report (escalation)
- L2 + pending: Stay in Approve (polling for human decision)
- L3 actions: Blocked at Recommend, escalate to human

**Conditional routing after Verify**:
- healthy: Go to Report (incident resolved)
- degraded + loops < max: Go back to Observe (re-diagnose, max 2 loops)
- failed or max loops: Go to Report (escalation)

### CSS-as-Splunk Pipeline

```
LTS (logs) ──→ CSS ops_logs-*
CTS (audit) ──→ CSS ops_cts-*
AOM/CES (metrics) ──→ CSS ops_metrics-*
                         ↓
              Anomaly Detection (LLM + statistical)
                         ↓
              Alert Governance (L0/L1/L2/L3)
                         ↓
              Remediation (FunctionGraph / SDK)
                         ↓
              Incident Report → CSS ops_incidents-*
```

5 CSS index templates define a common field schema (`timestamp`, `source_service`, `resource_id`, `region`, `severity`, `correlation_id`, `trace_id`) — replacing Splunk's Common Information Model.

### Action Level Enforcement

| Level | Scope | Approval | Example Tools |
|-------|-------|----------|---------------|
| **L0** | Read-only | Auto | `aom.list_alarms`, `ces.show_metric_data`, `cts.list_traces`, `css.get_cluster_info` |
| **L1** | Suggest | Auto | `runbook.lookup`, `runbook.render`, `diagnosis.recommend` |
| **L2** | Execute | HMAC token (15-min TTL) | `css.scale_out`, `ecs.resize`, `cce.restart_pod`, `functiongraph.invoke` |
| **L3** | Destructive | **Blocked** | `ecs.delete_server`, `css.delete_cluster`, `vpc.delete_vpc`, `iam.delete_user` |

---

## Directory Structure

```
AIOps-Agent-Skill/
├── SKILL.md                          # This document
├── .env.example                      # Environment variable template
├── .env                              # Active configuration (gitignored)
├── .gitignore                        # Git ignore rules
├── Makefile                          # Build/deploy/test targets (18 commands)
├── Dockerfile                        # Container image for K8s deployment
├── docker-compose.yml                # Local Docker Compose setup
├── agents/openai.yaml                # OpenAI agent config
│
├── agent/                            # Core agent code (14 Python files)
│   ├── ops_agent_state.py            # LangGraph StateGraph (core orchestrator)
│   ├── ops_agent_config.py           # Config from .env + dotenv auto-load
│   ├── tools_huawei_cloud.py         # SDK tool registry (AOM, CES, CTS, CSS, ECS, CCE, FG)
│   ├── tools_knowledge.py            # LlamaIndex knowledge base (graceful fallback)
│   ├── tools_prometheus.py           # Prometheus/Grafana metrics query tools
│   ├── aom_ces_connector.py          # AOM + CES monitoring connector (TTL cache)
│   ├── cts_connector.py              # CTS audit trail connector
│   ├── css_log_correlator.py         # Cross-service log correlation via CSS
│   ├── action_policy.py              # L0/L1/L2/L3 enforcement engine
│   ├── approval_token.py             # L2 HMAC approval token (15-min TTL)
│   ├── runbook_engine.py             # Runbook template renderer + step parser
│   ├── remediation_executor.py       # FunctionGraph + direct SDK execution
│   ├── otel_tracing.py               # OpenTelemetry init (reuses openllmetry)
│   └── maas_client.py                # MaaS GLM 5.1 client (OpenAI-compatible)
│
├── policies/                         # Action level policies (3 JSON files)
│   ├── action_levels.json            # 45 tools classified L0-L3
│   ├── read_only_policy.json         # L0 allowlist
│   └── forbidden_actions.json        # L3 blocklist with rationale
│
├── runbooks/                         # Remediation runbooks (7 files)
│   ├── runbook_css_high_cpu.md       # CSS cluster CPU → scale-out
│   ├── runbook_ecs_cpu_high.md       # ECS CPU → suggest resize
│   ├── runbook_cce_pod_crash.md      # CCE Pod crash → restart
│   ├── runbook_gaussdb_slow_sql.md   # GaussDB slow SQL → optimization
│   ├── runbook_vpn_disconnect.md     # VPN disconnect → reconnect
│   ├── runbook_cbr_backup_failure.md # CBR backup failure → retry
│   └── runbook_template.md           # Generic template for new scenarios
│
├── index_templates/                  # CSS index schemas (5 JSON files)
│   ├── ops_logs_template.json        # Log records from LTS
│   ├── ops_metrics_template.json     # Metric data from AOM/CES
│   ├── ops_alerts_template.json      # Alert events from AOM
│   ├── ops_cts_template.json         # CTS audit trail events
│   └── ops_incidents_template.json   # Agent incident reports
│
├── terraform/                        # Infrastructure (11 TF files)
│   ├── providers.tf                  # Huawei Cloud provider config
│   ├── variables.tf                  # Input variables
│   ├── network.tf                    # VPC, subnet, security group
│   ├── css.tf                        # CSS cluster (OpenSearch 3.4.0)
│   ├── obs.tf                        # OBS bucket for reports
│   ├── lts.tf                        # LTS log group and topics
│   ├── smn.tf                        # SMN topic for approval notifications
│   ├── functiongraph.tf              # Remediation functions
│   ├── ecs.tf                        # Optional ECS for agent runtime
│   ├── outputs.tf                    # Output values
│   └── terraform.tfvars.example      # Example variable values
│
├── scripts/                          # Provisioning, ingestion, demo (9 files)
│   ├── aiops_loop.py                 # Continuous loop (production runtime)
│   ├── aiops-agent.service           # systemd unit file
│   ├── deploy_to_ecs.sh              # One-command ECS deployment
│   ├── install_agent.sh              # Install agent runtime on ECS
│   ├── provision_huawei_demo.py      # Provision demo infra
│   ├── ingest_lts_to_css.py          # LTS → CSS pipeline
│   ├── ingest_cts_to_css.py          # CTS → CSS pipeline
│   ├── generate_demo_alerts.py       # Synthetic alert data generator
│   ├── run_agent_demo.py             # End-to-end demo script
│   └── requirements.txt              # Python dependencies
│
├── demo/                             # Synthetic test data (4 JSON files)
│   ├── demo_alerts.json              # 6 alert events (one per scenario)
│   ├── demo_metrics.json             # 3 metric data points
│   ├── demo_cts_events.json          # 1 CTS audit event
│   └── demo_lts_logs.json            # 2 LTS log records
│
├── references/                       # Documentation (9 files)
│   ├── architecture.md               # System architecture
│   ├── langgraph-state-machine.md    # State machine design
│   ├── css-as-splunk-pipeline.md     # CSS pipeline design
│   ├── action-level-design.md        # Action level rationale
│   ├── aom-ces-cts-integration.md    # Monitoring integration
│   ├── cross-service-correlation.md  # Log correlation design
│   ├── runbook-design.md             # Runbook template design
│   ├── huawei-cloud-deployment.md    # Deployment guide
│   └── troubleshooting.md            # Known issues and fixes
│
└── tests/                            # Unit tests (6 files, 53 test cases)
    ├── test_action_policy.py         # L0/L1/L2/L3 enforcement tests
    ├── test_ops_agent_state.py       # Conditional routing tests (10 cases)
    ├── test_aom_ces_connector.py     # AOM/CES connector tests
    ├── test_css_log_correlator.py    # CSS correlation tests
    ├── test_approval_token.py        # HMAC token lifecycle tests
    └── test_runbook_engine.py        # Runbook rendering tests
```

---

## Core Components

### 1. LangGraph State Machine — `agent/ops_agent_state.py`

**Class**: `OpsAgent`

**State** (`OpsAgentState` TypedDict, 22 fields):

| Phase | Fields |
|-------|--------|
| Input | `alert_event`, `alert_source`, `alert_severity` |
| Observation | `observed_metrics`, `observed_logs`, `observed_cts_events`, `observation_summary` |
| Diagnosis | `root_cause`, `related_incidents`, `confidence_score` |
| Recommendation | `recommended_action`, `runbook_id`, `runbook_steps`, `action_level` |
| Preview | `preview_result`, `preview_summary` |
| Approval | `approval_token`, `approval_status`, `approver_identity` |
| Execution | `execution_result`, `execution_timestamp` |
| Verification | `verification_metrics`, `verification_status` |
| Report | `incident_report`, `report_url` |
| Meta | `trace_id`, `agent_version`, `loop_count` |

**Node implementations**:
- `observe_node` — Collect metrics (AOM/CES), logs (CSS), CTS events; LLM summarizes observations
- `diagnose_node` — LLM identifies root cause; knowledge base searches past incidents
- `recommend_node` — Match runbook by alert type; determine action level from highest step level
- `preview_node` — Dry-run each step via `tools.dry_run()`; show effects without execution
- `approve_node` — L0/L1 auto-approve; L2 generate HMAC token; L3 block; demo mode auto-approves L2
- `execute_node` — Run L2 steps via `remediation_executor`; skip L0/L1; block L3
- `verify_node` — Check health via `monitor.assess_health()`; return healthy/degraded/critical
- `report_node` — Build incident report; persist to CSS `ops_incidents-*` index

**Graph compilation**: `InMemorySaver` checkpointer for state persistence across execution.

### 2. Action Policy Engine — `agent/action_policy.py`

**Class**: `ActionPolicy`

Loads `action_levels.json` (45 tools) and `forbidden_actions.json` (8 L3 tools) at init.

**Key methods**:
- `classify(tool_name)` → L0/L1/L2/L3 (unknown defaults to L3)
- `enforce(tool_name, approval_token)` → `{allowed, level, reason, requires_approval}`
- `is_forbidden(tool_name)` → bool
- `is_allowed(tool_name, max_level)` → bool
- `get_tools_by_level(level)` → list of tool names

**Policy distribution**: 23 L0 tools, 5 L1 tools, 9 L2 tools, 8 L3 tools.

### 3. Approval Token — `agent/approval_token.py`

**Class**: `ApprovalToken`

HMAC-SHA256 token: `HMAC-SHA256("{tool_name}:{params_hash}:{timestamp}:{approver}", HWC_SECRET_ACCESS_KEY)`

**Key methods**:
- `generate(tool_name, params, requested_by)` → `{token, expires_at, action, params_hash}`
- `approve(token, approver_identity)` → validates and marks approved
- `reject(token, approver_identity)` → marks rejected
- `validate(token, tool_name, params)` → `{valid, status, reason}`
- `get_status(token)` → pending/approved/rejected/expired

TTL: 900 seconds (15 minutes), configurable via `APPROVAL_TTL_SECONDS`.

### 4. AOM/CES Connector — `agent/aom_ces_connector.py`

**Class**: `AOMCESConnector`

Unified monitoring connector with TTL cache (60s for metrics, 300s for alarms).

**Key methods**:
- `get_current_metrics(resource_type, resource_id, metric_names)` → metric dict
- `get_alarm_state(alarm_id)` → alarm status
- `assess_health(resource_type, resource_id)` → `{status, metrics, thresholds}` where status ∈ {healthy, degraded, critical}
- `get_metric_history(metric_name, resource_id, period)` → time series

Demo mode: returns synthetic metrics when `DEMO_MODE=true`.

### 5. CTS Connector — `agent/cts_connector.py`

**Class**: `CTSConnector`

**Key methods**:
- `get_recent_events(resource_id, resource_type, minutes)` → list of CTS trace records
- `find_config_changes(resource_id, since)` → filtered for update/create/delete events
- `correlate_with_alert(alert)` → CTS events near alert timestamp (change-caused-anomaly detection)

### 6. CSS Log Correlator — `agent/css_log_correlator.py`

**Class**: `CSSLogCorrelator`

Cross-service correlation across `ops_logs-*`, `ops_alerts-*`, `ops_cts-*` indices.

**Key methods**:
- `query_recent_logs(resource_id, service, severity, minutes)` → log records
- `correlate_events(alert, correlation_fields, time_window_minutes)` → related events across all indices
- `search_incident_history(root_cause_keywords, limit)` → similar past incidents
- `index_incident(incident)` → persist to `ops_incidents-*`, returns doc ID
- `bulk_ingest(index_name, documents)` → bulk index, returns success count

Demo mode: all methods return empty results when CSS is unreachable. URL parsing uses `urllib.parse.urlparse` for robust host/port extraction.

### 7. Huawei Cloud SDK Tool Registry — `agent/tools_huawei_cloud.py`

**Class**: `HuaweiCloudToolRegistry`

SDK builder pattern: `BasicCredentials` + `HttpConfig` + `Region` (reuses `css-testing/huawei_css_api.py`).

**SDK connectors**:
- `AOMTools`: `list_alarms`, `show_alarm_history`, `list_components`, `show_component_metrics`
- `CESTools`: `list_metrics`, `show_metric_data`, `list_alarms`, `show_alarm_history`
- `CTSTools`: `list_traces`, `list_trace_quotas`
- `CSSTools`: cluster info, node operations (reuses css-testing)
- `ECSTools`: server operations (reuses enterprise-rag-agent)
- `CCETools`: `list_pods`, `show_pod`, `restart_pod`, `scale_deployment`
- `FunctionGraphTools`: `invoke_function`
- `VPNTools`, `CBRTools`

**Key methods**:
- `dry_run(tool_name, params)` → preview without execution
- `execute(tool_name, params)` → live execution

### 8. Knowledge Base — `agent/tools_knowledge.py`

**Class**: `OpsKnowledgeBase`

LlamaIndex + CSS/OpenSearch vector store for runbook and incident retrieval.

**Graceful fallback**: When `llama_index` is not installed, falls back to direct CSS `multi_match` query. All methods return empty results instead of raising `ImportError`.

**Key methods**:
- `search_runbooks(alert_type, root_cause)` → matching runbook chunks
- `search_past_incidents(description, limit)` → similar incident records
- `index_runbook(runbook_path)` → index a runbook document
- `index_incident_record(incident)` → index a completed incident

### 9. Runbook Engine — `agent/runbook_engine.py`

**Class**: `RunbookEngine`

**Key methods**:
- `lookup_runbook(alert_type)` → matching runbook filename (e.g., `css_cluster_high_cpu` → `runbook_css_high_cpu.md`)
- `render_runbook(runbook_id, context)` → list of steps with `{{variable}}` substitution
- `preview_runbook(runbook_id, context)` → human-readable summary without execution

Step parsing: each `## Step N` heading becomes a step dict with `step_num`, `title`, `tool`, `level`, `params`.

### 10. Remediation Executor — `agent/remediation_executor.py`

**Class**: `RemediationExecutor`

- Direct SDK calls for simple actions (CSS scale-out, ECS reboot)
- FunctionGraph invocation for complex remediation functions
- Records execution result and duration

### 11. MaaS Client — `agent/maas_client.py`

OpenAI-compatible client pointed at Huawei Cloud MaaS endpoint.

**Functions**:
- `create_maas_client(config)` → `OpenAI` client with `api_key` and `base_url`
- `call_maas(client, system_prompt, user_prompt, model, temperature, max_tokens)` → text response
- `call_maas_with_thinking(client, ...)` → `{thinking, text}` with reasoning budget

### 12. OpenTelemetry — `agent/otel_tracing.py`

**Functions**:
- `init_otel_tracing(endpoint, service_name)` — Initialize OTel with safe defaults
- `get_tracer(name)` — Get a named tracer instance

### 13. Prometheus Tools — `agent/tools_prometheus.py`

**Class**: `PrometheusTools`

- `query_promql(query)` — Execute PromQL query
- `query_range(query, start, end, step)` — Range query
- `get_grafana_dashboard(dashboard_id)` — Fetch dashboard JSON

---

## Configuration — `.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HWC_ACCESS_KEY_ID` | Yes | — | Huawei Cloud AK |
| `HWC_SECRET_ACCESS_KEY` | Yes | — | Huawei Cloud SK |
| `HWC_REGION` | Yes | `la-north-2` | Huawei Cloud region |
| `HWC_PROJECT_ID` | Yes | — | Huawei Cloud project ID |
| `CSS_CLUSTER_ID` | Yes | — | CSS cluster ID |
| `CSS_ENDPOINT` | Yes | — | CSS endpoint URL (e.g., `http://192.168.0.23:9200`) |
| `CSS_USERNAME` | Yes | `admin` | CSS username |
| `CSS_PASSWORD` | Yes | — | CSS password |
| `HUAWEI_MAAS_API_BASE` | Yes | — | MaaS API base URL |
| `HUAWEI_MAAS_API_KEY` | Yes | — | MaaS API key |
| `HUAWEI_MAAS_MODEL` | No | `glm-5.1` | MaaS model name |
| `AOM_APP_ID` | No | — | AOM application ID |
| `PROMETHEUS_URL` | No | `http://localhost:9090` | Prometheus endpoint |
| `GRAFANA_URL` | No | `http://localhost:3000` | Grafana endpoint |
| `GRAFANA_API_KEY` | No | — | Grafana API key |
| `LTS_LOG_GROUP_ID` | No | — | LTS log group ID |
| `LTS_LOG_TOPIC_ID` | No | — | LTS log topic ID |
| `CTS_TRACKER_NAME` | No | `system` | CTS tracker name |
| `SMN_TOPIC_URN` | No | — | SMN topic URN for approval notifications |
| `SMN_APPROVAL_EMAIL` | No | — | Email for approval notifications |
| `OBS_BUCKET_NAME` | No | — | OBS bucket for reports |
| `OBS_REGION` | No | `la-north-2` | OBS bucket region |
| `APPROVAL_TTL_SECONDS` | No | `900` | L2 approval token TTL (15 min) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry collector endpoint |
| `TRACELOOP_TRACE_CONTENT` | No | `false` | Trace content flag |
| `AGENT_VERSION` | No | `1.0.0` | Agent version |
| `VERIFICATION_DELAY_SECONDS` | No | `30` | Delay before verification check |
| `MAX_REDIAGNOSIS_LOOPS` | No | `2` | Max re-diagnosis cycles |
| `DEMO_MODE` | No | `false` | Demo mode (synthetic data, auto-approve L2) |

The `ops_agent_config.py` auto-loads `.env` via `python-dotenv` on import.

---

## Supported Scenarios

| # | Scenario | Alert Source | Action Level | Flow |
|---|----------|-------------|-------------|------|
| 1 | CSS cluster high CPU | AOM | **L2** (scale-out) | Observe→Diagnose→Recommend→Preview→Approve→Execute→Verify→Report |
| 2 | ECS CPU high | CES | **L1** (suggest resize) | Observe→Diagnose→Recommend→Preview→Approve(auto)→Report |
| 3 | CCE Pod crash loop | AOM | **L2** (restart pod) | Observe→Diagnose→Recommend→Preview→Approve→Execute→Verify→Report |
| 4 | GaussDB slow SQL | CES | **L1** (query optimization) | Observe→Diagnose→Recommend→Preview→Approve(auto)→Report |
| 5 | VPN gateway disconnect | CES | **L2** (reconnect) | Observe→Diagnose→Recommend→Preview→Approve→Execute→Verify→Report |
| 6 | CBR backup failure | CES | **L2** (retry) | Observe→Diagnose→Recommend→Preview→Approve→Execute→Verify→Report |

---

## CSS Index Templates

5 templates replace Splunk's Common Information Model with a unified field schema:

### Common Fields (all indices)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `date` | Event timestamp |
| `source_service` | `keyword` | Source Huawei Cloud service |
| `resource_id` | `keyword` | Resource identifier |
| `region` | `keyword` | Huawei Cloud region |
| `severity` | `keyword` | Event severity (critical/high/medium/low) |
| `correlation_id` | `keyword` | Cross-service correlation ID |
| `trace_id` | `keyword` | Distributed trace ID |

### Template-Specific Fields

**ops_logs_template.json** — Log records from LTS
- `log_level`, `message` (text), `source_host`, `application`

**ops_metrics_template.json** — Metric data from AOM/CES
- `metric_name`, `namespace`, `value` (double), `unit`, `dimensions` (nested)

**ops_alerts_template.json** — Alert events from AOM
- `alert_id`, `alert_type`, `alert_source`, `resource_type`, `metric_value` (double), `threshold` (double), `description` (text)

**ops_cts_template.json** — CTS audit trail events
- `trace_name`, `trace_type`, `resource_type`, `user_name`, `request_body` (text), `response_code`

**ops_incidents_template.json** — Agent incident reports
- `incident_id`, `root_cause` (text), `confidence_score` (double), `action_level`, `approval_status`, `verification_status`, `execution_result` (nested), `recommended_action` (text)

---

## Runbook Design

Each runbook follows this structure:

```markdown
# Runbook: [Scenario Name]

## Metadata
- alert_type: [matches alert_type field]
- action_level: [L1 or L2]

## Step 1: [Title]
  Tool: `[tool.name]`
  Level: [L0/L1/L2]
  Params: `{"key": "{{variable}}"}`

## Step 2: [Title]
  ...
```

**Variable substitution**: `{{alert_type}}`, `{{resource_id}}`, `{{resource_type}}`, `{{region}}`, `{{metric_value}}`, `{{threshold}}`, `{{root_cause}}` are replaced with context values at render time.

**Action level determination**: The highest level across all steps becomes the runbook's action level. If any step is L3, the entire runbook is blocked.

---

## Action Level Policy — `policies/`

### L0 — Read-Only (23 tools)

`aom.list_alarms`, `aom.show_alarm_history`, `aom.list_components`, `aom.show_component_metrics`, `ces.list_metrics`, `ces.show_metric_data`, `ces.list_alarms`, `ces.show_alarm_history`, `cts.list_traces`, `cts.list_trace_quotas`, `css.get_cluster_info`, `css.get_cluster_health`, `css.get_data_node_count`, `css.get_index_info`, `css.get_shard_info`, `css_log.query`, `css_log.correlate`, `css_log.search_incidents`, `ecs.list_servers`, `ecs.show_server`, `cce.list_pods`, `cce.show_pod`, `prometheus.query`

### L1 — Suggest (5 tools)

`runbook.lookup`, `runbook.render`, `runbook.preview`, `diagnosis.recommend`, `diagnosis.assess_confidence`

### L2 — Execute with Approval (9 tools)

`css.scale_out_data_nodes`, `css.scale_in_data_nodes`, `ecs.resize`, `ecs.reboot`, `cce.restart_pod`, `cce.scale_deployment`, `functiongraph.invoke`, `vpn.recreate_connection`, `cbr.retry_backup`

### L3 — Forbidden (8 tools)

`ecs.delete_server`, `css.delete_cluster`, `css.delete_index`, `vpc.delete_vpc`, `vpc.delete_subnet`, `iam.delete_user`, `iam.delete_role`, `obs.delete_bucket`

---

## Deployment on ECS

### Prerequisites

```bash
# Python 3.10+ required
python3 --version

# Install dependencies
pip3 install langgraph langchain-core langgraph-checkpoint-sqlite \
    opensearch-py openai python-dotenv cachetools
```

### File Deployment

```bash
# Copy agent code to ECS
scp -r agent/ root@ECS:/opt/aiops-agent/agent/
scp -r policies/ root@ECS:/opt/aiops-agent/policies/
scp -r runbooks/ root@ECS:/opt/aiops-agent/runbooks/
scp -r index_templates/ root@ECS:/opt/aiops-agent/index_templates/
scp -r demo/ root@ECS:/opt/aiops-agent/demo/
scp .env root@ECS:/opt/aiops-agent/.env
```

### Continuous Loop Script

`scripts/aiops_loop.py` — Cycles through all 6 alert scenarios, runs the LangGraph agent, persists incident reports to CSS, and sleeps between cycles.

Environment variables:
- `AIOPS_CYCLE_SLEEP` — Seconds between cycles (default: 120)
- `AIOPS_MAX_CYCLES` — Max cycles before stopping (default: 0 = infinite)
- `AIOPS_AGENT_DIR` — Agent root directory (default: `/opt/aiops-agent`)

### One-Command Deployment

```bash
# Deploy everything to ECS in one step
bash scripts/deploy_to_ecs.sh 101.44.184.244 ~/.ssh/gov-rag-20260508055113
```

### Makefile Targets

```bash
make demo          # Run demo (scenario 0)
make demo-all      # Run all 6 scenarios
make test          # Run unit tests
make deploy        # Deploy to ECS
make start         # Start agent on ECS
make stop          # Stop agent on ECS
make status        # Check agent status
make logs          # Tail agent logs
make css-count     # Check CSS incident count
make css-health    # Check CSS cluster health
make css-indices   # List all CSS indices
make clean         # Remove checkpoints and logs
```

### Systemd Service

```ini
[Unit]
Description=AIOps Agent Continuous Loop
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aiops-agent
Environment=AIOPS_CYCLE_SLEEP=120
Environment=AIOPS_MAX_CYCLES=0
Environment=AIOPS_AGENT_DIR=/opt/aiops-agent
ExecStart=/usr/bin/python3 /opt/aiops-agent/scripts/aiops_loop.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable aiops-agent
systemctl start aiops-agent
systemctl status aiops-agent
journalctl -u aiops-agent -f
```

---

## Live Runtime Data (ECS 101.44.184.244)

### Service Status

- **Service**: `aiops-agent.service` — active (running) since 2026-05-09 02:13 CST
- **CSS Cluster**: `gov-rag-20260508055113-css` — yellow (1 data node), OpenSearch 3.4.0
- **CSS Endpoint**: `http://192.168.0.23:9200` (internal to ECS VPC)
- **Memory**: ~78 MB, 0 errors

### CSS Indices

| Index | Docs | Size | Shards | Purpose |
|-------|------|------|--------|---------|
| `ops_incidents-2026.05.09` | 378 | 647 KB | 1p/1r | Agent incident reports (current day) |
| `ops_incidents-2026.05.08` | 116 | 336 KB | 1p/1r | Agent incident reports (previous day) |
| `ops_alerts-2026.05.08` | 6 | 27.5 KB | 3p/1r | Demo alert events |
| `ops_logs-2026.05.08` | 2 | 13 KB | 3p/1r | Demo log records |
| `ops_cts-2026.05.08` | 1 | 6.6 KB | 3p/1r | Demo CTS audit event |
| `ops_metrics-2026.05.08` | 3 | 6.6 KB | 3p/1r | Demo metric data |
| `cloud-adoption-skills` | 423 | 2 MB | 1p/0r | CSS Search MCP index |

### Incident Distribution (495 cycles, ~21 hours)

| Alert Type | Count | % | Action Level | Approval | Verification |
|------------|-------|---|-------------|----------|-------------|
| vpn_gateway_disconnect | 89 | 18.0% | L2 | approved | healthy |
| gaussdb_slow_sql | 86 | 17.4% | L1 | auto_approved | — |
| cbr_backup_failure | 86 | 17.4% | L2 | approved | healthy |
| css_cluster_high_cpu | 81 | 16.4% | L2 | approved | healthy |
| ecs_cpu_high | 78 | 15.8% | L1 | auto_approved | — |
| cce_pod_crash_loop | 74 | 15.0% | L2 | approved | healthy |

**Summary**: L1=164 (33.2%), L2=330 (66.8%). Approval: auto_approved=164, approved=330. Verification: healthy=330, n/a=164 (L1 skips execution). Avg confidence: 0.50.

### Throughput

Steady **~20 incidents/hour** (each cycle: LLM inference ~60s + verification ~5s + sleep 120s). 24-hour continuous operation with zero errors.

---

## Testing

### Unit Tests — 53 test cases, all pass

```bash
cd AIOps-Agent-Skill
DEMO_MODE=true python3 -m pytest tests/ -v
```

| Test File | Cases | Coverage |
|-----------|-------|----------|
| `test_action_policy.py` | 8 | L0/L1/L2/L3 classification, enforcement, forbidden check |
| `test_ops_agent_state.py` | 10 | Conditional routing (approval + verification) |
| `test_approval_token.py` | 8 | Generate, approve, reject, validate, expire, uniqueness |
| `test_runbook_engine.py` | 10 | Lookup, render, preview, template substitution |
| `test_aom_ces_connector.py` | 3 | Demo metrics, health assessment |
| `test_css_log_correlator.py` | 2 | Instantiation, default fields |

### Demo — All 6 Scenarios

```bash
DEMO_MODE=true python3 scripts/run_agent_demo.py 0  # CSS high CPU
DEMO_MODE=true python3 scripts/run_agent_demo.py 1  # ECS CPU high
# ... through index 5
```

### End-to-End Agent Execution

```python
from ops_agent_state import OpsAgent
from ops_agent_config import OpsAgentConfig

config = OpsAgentConfig.from_env()
config.demo_mode = True
agent = OpsAgent(config)
result = agent.run(alert, thread_id="test")
# result contains: root_cause, action_level, approval_status, verification_status, incident_report
```

### CSS Data Verification

```bash
# On ECS
curl -s -u admin:PASSWORD "http://192.168.0.23:9200/ops_incidents-*/_count"
curl -s -u admin:PASSWORD "http://192.168.0.23:9200/ops_incidents-*/_search?size=5&sort=timestamp:desc"
```

---

## Reuse from Existing Skills

| Pattern | Source Skill | Reused In |
|---------|-------------|-----------|
| SDK builder (`BasicCredentials` + `HttpConfig` + `Region`) | `css-testing/huawei_css_api.py` | `tools_huawei_cloud.py` |
| CSS monitor (CPU, heap, disk metrics) | `css-testing/css_monitor.py` | `aom_ces_connector.py` |
| Hysteresis scaling + cooldown | `css-testing/scaling_engine.py` | `runbook_css_high_cpu.md` |
| NL→ES Query DSL→Answer | `css-log-assistant/app/app.py` | `css_log_correlator.py` |
| MaaS OpenAI-compatible client | `css-log-assistant/app/maas_client.py` | `maas_client.py` |
| LlamaIndex + CSS/OpenSearch vector store | `enterprise-rag-agent/` | `tools_knowledge.py` |
| Huawei Cloud provisioning (OBS, CSS, ECS, VPC) | `enterprise-rag-agent/scripts/` | `provision_huawei_demo.py` |
| OpenTelemetry init + safe defaults | `openllmetry-huawei-maas-agent/` | `otel_tracing.py` |
| LTS logging + SMN alarm notification | `CFW-Finance-Skill/` | `approve_node` (SMN for approval) |
| CSS bulk ingest with verification | `css-log-assistant/scripts/upload_to_es.py` | `ingest_lts_to_css.py`, `ingest_cts_to_css.py` |
| Terraform (VPC, SG, CSS) | `css-log-assistant/terraform/` | `terraform/` |

---

## Terraform Resources

| Resource | File | Purpose |
|----------|------|---------|
| VPC + Subnet + Security Group | `network.tf` | Network isolation |
| CSS Cluster (OpenSearch 3.4.0) | `css.tf` | Log/metrics storage and search |
| OBS Bucket | `obs.tf` | Incident reports and state persistence |
| LTS Log Group + Topics | `lts.tf` | Log collection pipeline |
| SMN Topic | `smn.tf` | Approval notification |
| FunctionGraph Functions | `functiongraph.tf` | Auto-remediation execution |
| ECS (optional) | `ecs.tf` | Agent runtime host |

---

## Troubleshooting

### `ModuleNotFoundError: llama_index`

LlamaIndex has a heavy dependency chain. `tools_knowledge.py` includes a graceful fallback — when `llama_index` is not installed, it uses direct CSS `multi_match` queries instead. Set `HAS_LLAMAINDEX = False` automatically on import failure.

### `ModuleNotFoundError: openai`

Install: `pip install openai`. Required for MaaS LLM inference.

### `TypeError: Invalid checkpointer provided`

LangGraph 1.1+ changed the `SqliteSaver` API. The agent uses `InMemorySaver()` instead. If you need persistent checkpoints across restarts, use:

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
# or
from langgraph.checkpoint.memory import InMemorySaver
```

### CSS endpoint unreachable from WSL

The CSS endpoint (`192.168.0.23:9200`) is internal to the ECS VPC. Solutions:
1. Deploy the agent on ECS (recommended — uses systemd service)
2. SSH tunnel: `ssh -L 9200:192.168.0.23:9200 root@101.44.184.244`
3. Set `DEMO_MODE=true` to skip CSS connections

### CSS `_count` returning 0 after bulk write

OpenSearch indices need a refresh before querying. Add `refresh=True` to the index call, or manually:

```bash
curl -X POST "http://CSS:9200/index/_refresh"
```

### `openai.OpenAIError: Missing credentials`

The `.env` file must be loaded before creating the MaaS client. `ops_agent_config.py` auto-loads `.env` via `python-dotenv`. If running standalone, ensure `HUAWEI_MAAS_API_KEY` is set in the environment.

### Approval token `approver` keyword error

The `ApprovalToken.approve()` method signature is `approve(token, approver_identity)`, not `approve(token, approver=...)`. Use the positional parameter name `approver_identity`.

---

## Business KPI

- **MTTR reduction**: Automated diagnosis + runbook execution vs. manual expert triage
- **Ticket diagnosis time reduction**: LLM root cause analysis in seconds vs. hours
- **Alert noise reduction**: Action level governance filters L0/L1 from human review
- **Compliance**: CTS audit trail + approval tokens provide full accountability
- **Cost savings**: CSS replaces Splunk at lower cost with native Huawei Cloud integration
- **Customer outcome**: Shift from "can't use cloud" to "AI helps me use cloud"
