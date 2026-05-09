# AIOps Agent Skill

An intelligent O&M agent for Huawei Cloud that replaces Splunk with CSS (Cloud Search Service / OpenSearch), automates anomaly detection and remediation, and enforces safe action levels through a 4-tier policy engine.

## What It Does

- **CSS as Splunk replacement**: Unified data plane for logs, metrics, alerts, audit events, and incident records via 5 CSS index templates
- **LangGraph state machine**: 8-state flow (Observe → Diagnose → Recommend → Preview → Approve → Execute → Verify → Report) with conditional routing
- **Action level enforcement**: L0 (read-only) → L1 (suggest) → L2 (approve+execute) → L3 (forbidden) — 45 tools classified
- **6 remediation scenarios**: CSS high CPU, ECS CPU high, CCE Pod crash, GaussDB slow SQL, VPN disconnect, CBR backup failure
- **Cross-service correlation**: LTS logs + CTS audit + AOM/CES metrics → CSS → anomaly detection → runbook-driven remediation
- **HMAC approval tokens**: L2 actions require cryptographic approval with 15-minute TTL
- **Auto-remediation**: Direct SDK calls or FunctionGraph invocation for complex remediation

## Core Stack

LangGraph + LlamaIndex + CSS/OpenSearch + Huawei Cloud SDK (AOM, CES, CTS, FunctionGraph) + Prometheus/Grafana + OpenTelemetry

## Quick Start

```bash
# Run demo
DEMO_MODE=true python3 scripts/run_agent_demo.py 0

# Run unit tests (53 test cases)
DEMO_MODE=true python3 -m pytest tests/ -v

# Deploy to ECS
bash scripts/deploy_to_ecs.sh 101.44.184.244 ~/.ssh/your-key
```

## Live Deployment

Running on ECS `101.44.184.244` as systemd service `aiops-agent`:
- **500+ cycles** completed, **500+ incidents** indexed in CSS
- **~20 incidents/hour** throughput, **0 errors** over 21+ hours
- CSS cluster: yellow (1 node), Heap 36%, RAM 96%

## Files

| Directory | Contents |
|-----------|----------|
| `agent/` | 14 Python files — LangGraph orchestrator, connectors, policy engine, runbook engine |
| `policies/` | 3 JSON files — L0-L3 tool classification (45 tools) |
| `runbooks/` | 7 Markdown files — 6 scenario runbooks + template |
| `index_templates/` | 5 JSON files — CSS index schemas (replaces Splunk CIM) |
| `terraform/` | 11 TF files — VPC, CSS, OBS, LTS, SMN, FunctionGraph, ECS |
| `scripts/` | 9 files — loop, deploy, install, demo, ingestion |
| `demo/` | 4 JSON files — synthetic test data |
| `tests/` | 6 files — 53 test cases, all pass |

See [SKILL.md](./SKILL.md) for the complete agent-facing workflow and operational documentation.
