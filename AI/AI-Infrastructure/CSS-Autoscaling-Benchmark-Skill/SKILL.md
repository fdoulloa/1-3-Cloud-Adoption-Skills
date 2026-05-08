---
name: css-autoscaling-benchmark-skill
description: Benchmark and autoscaling test harness for Huawei Cloud CSS (OpenSearch). Use when the task is to evaluate CSS performance, run load tests, validate query quality, test data-node horizontal autoscaling, or generate consolidated benchmark reports for CSS clusters.
---

# CSS Autoscaling Benchmark Skill

Comprehensive benchmark and autoscaling test harness for **Huawei Cloud CSS (Cloud Search Service / OpenSearch)**, built around a **ColombiaEats food delivery** use case with vector similarity search, geolocation, and cross-query patterns.

## When to Use This Skill

- You need to evaluate CSS/OpenSearch performance under realistic workloads (ingestion throughput, query latency, vector search quality).
- You need to test or validate CSS data-node horizontal autoscaling behavior.
- You need a consolidated benchmark report with latency percentiles, throughput metrics, and scaling event history.
- You need to validate CSS API endpoints or run load tests against an existing CSS cluster.

## Architecture

```
run_complete_benchmark.sh          <-- Main entry point (7-phase pipeline)
├── config.py                      <-- Centralized .env configuration
├── setup_css_index.py             <-- Phase 1: Index creation
├── ingesta_benchmark.py           <-- Phase 2: Bulk ingestion
├── evaluaciones_benchmark.py      <-- Phase 3: Query quality evaluation
├── cross_query_benchmark.py       <-- Phase 4: CSS + RDS cross-queries
├── run_performance_tests.sh       <-- Phase 5: Locust load tests
│   └── locustfile.py
├── monitor_autoscaling.py         <-- Phase 6: Cluster monitoring
├── phase5_controller.py           <-- Phase 6: Aggressive load to trigger scaling
├── data_node_autoscaler.py        <-- Autoscaler orchestrator
├── css_monitor.py                 <-- Data node metrics collector
├── scaling_engine.py              <-- Hysteresis-based scaling decisions
├── huawei_css_api.py              <-- Huawei Cloud CSS SDK wrapper
├── generate_report.py             <-- Phase 7: Consolidated report
├── apis_test.py                   <-- API endpoint validation
├── load_generator.py              <-- Standalone load generator
└── stress_test_wrapper.py         <-- Stress test orchestration
```

## Required Inputs

- Huawei Cloud CSS cluster endpoint (host:port).
- CSS cluster credentials (if auth is enabled).
- Huawei Cloud AK/SK with CSS read/write scope (for SDK-based operations).
- Target region and project ID.

## Core Rules

- **Never run load tests against a production CSS cluster** without explicit authorization and during a maintenance window.
- **Always start with a small load** and scale up; use `config.py` to control concurrency and ramp rate.
- **Capture baseline metrics** before autoscaling tests so you can compare before/after.
- **Clean up test indices** after benchmark runs unless explicitly preserving them for analysis.
- **Respect CSS resource quotas**; the autoscaling phases create additional data nodes which consume project quota.

## Benchmark Phases

| Phase | Script | Description |
|-------|--------|-------------|
| 1 | `setup_css_index.py` | Create indices with mappings for vectors, geolocation, and text |
| 2 | `ingesta_benchmark.py` | Bulk ingest ColombiaEats documents with embeddings |
| 3 | `evaluaciones_benchmark.py` | Evaluate query quality (recall, precision, latency) |
| 4 | `cross_query_benchmark.py` | Cross-query CSS + simulated RDS for pricing/availability |
| 5 | `run_performance_tests.sh` | Locust load tests with configurable concurrency |
| 6 | `monitor_autoscaling.py` | Monitor cluster; trigger scaling with aggressive load |
| 7 | `generate_report.py` | Consolidated report with all metrics and scaling events |

## Quick Start

```bash
# Configure
cp .env.example .env
# Edit .env with CSS endpoint, AK/SK, region

# Install dependencies
pip install -r requirements.txt

# Run full 7-phase benchmark
bash run_complete_benchmark.sh

# Or run individual phases
python3 setup_css_index.py
python3 ingesta_benchmark.py
python3 evaluaciones_benchmark.py
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CSS.0065` disk sold out | COMMON disk unavailable | Change `css_volume_type` to `HIGH` in config |
| Locust connection timeout | CSS endpoint unreachable or SG blocked | Verify endpoint and security group rules |
| Autoscaling not triggered | Load too low or cooldown period active | Increase `phase5_controller.py` concurrency; check cluster cooldown |
| Ingestion rate drops | Bulk request too large | Reduce `chunk_size` in `config.py` |

## Resources

- [README.md](README.md): Detailed setup and usage instructions
- [scripts/run_complete_benchmark.sh](run_complete_benchmark.sh): Main 7-phase pipeline
- [scripts/config.py](config.py): Centralized configuration from .env
- [scripts/huawei_css_api.py](huawei_css_api.py): Huawei Cloud CSS SDK wrapper
