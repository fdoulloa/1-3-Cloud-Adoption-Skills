# CSS Testing - Huawei Cloud CSS Benchmark Suite

Comprehensive benchmark and autoscaling test harness for **Huawei Cloud CSS (Cloud Search Service)**, built around a **ColombiaEats food delivery** use case with vector similarity search, geolocation, and cross-query patterns.

## Overview

This project evaluates the performance, scalability, and autoscaling behavior of Huawei Cloud CSS (OpenSearch 3.4.0) under realistic workloads. It runs a 7-phase benchmark pipeline that covers everything from index setup to data node horizontal autoscaling, producing consolidated reports with latency percentiles, throughput metrics, and scaling event history.

The benchmark is modeled on a food delivery platform ("ColombiaEats") that uses **image vector embeddings** for visual dish search combined with **geolocation filters**, **text search**, and **cross-queries against a simulated RDS** for transactional data (pricing, availability, promotions).

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
├── stress_test_wrapper.py         <-- Locust wrapper with metrics reporting
└── phase5_monitor.py              <-- Real-time dashboard for Phase 6
```

## Benchmark Phases

### Phase 1: Index Setup (`setup_css_index.py`)

Creates the CSS index with the following schema:

| Field | Type | Purpose |
|---|---|---|
| `image_vector` | `knn_vector` (HNSW, cosine, 128d) | Visual similarity search |
| `dish_name`, `description` | `text` (Spanish analyzer) | Full-text search |
| `restaurant_location` | `geo_point` | Proximity filtering |
| `food_category`, `cuisine_type` | `keyword` | Exact-match filters |
| `base_price_cop` | `double` | Budget filtering |
| `avg_rating`, `popularity_score` | `float` | Quality ranking |
| `allergens`, `is_vegetarian` | `keyword` / `boolean` | Dietary restrictions |

### Phase 2: Bulk Ingestion (`ingesta_benchmark.py`)

Ingests Colombian food documents with synthetically generated image embeddings. Each document includes:

- A **visual embedding** derived from simulated plate images (color-based, with Gaussian blur and noise)
- **6 Colombian cities** with realistic population-weighted distribution (Bogota 35%, Medellin 25%, Cali 15%, etc.)
- **6 authentic dishes** (Bandeja Paisa, Ajiaco, Arepa con Todo, Empanadas, Cazuela de Mariscos, Sushi Fusion)
- GPS coordinates within real city boundaries, ratings, pricing in COP

Measures throughput (docs/sec) and extrapolates to the 100M vector scale.

### Phase 3: Query Evaluation (`evaluaciones_benchmark.py`)

Runs 7 strict query patterns representing real delivery use cases:

| Query | Pattern | Description |
|---|---|---|
| Q1 | Visual + Geo | "Find this dish within 3km" |
| Q2 | Visual + Category + Rating | "Similar soup from well-rated restaurants" |
| Q3 | Visual + City + Budget | "Something like this in Medellin under $20,000 COP" |
| Q4 | Visual + Vegetarian + Geo | "Vegetarian options like this nearby" |
| Q5 | Visual + Neighborhood + Popularity | "Traditional Colombian in Chapinero with reviews" |
| Q6 | Visual + Allergen-free + Geo | "Similar but without gluten/dairy nearby" |
| Q7 | Hybrid (Visual + Text) + Spice + City | "Like bandeja paisa but mild in Bogota" |

Reports avg/P95/P99 latencies and zero-result rates.

### Phase 4: Cross-Query Benchmark (`cross_query_benchmark.py`)

Simulates the **CSS + RDS** architecture where vector search in CSS is combined with transactional data in RDS (simulated via in-memory SQLite with 50K+ rows). Tests 5 cross-query patterns:

| Query | Pattern | Flow |
|---|---|---|
| CQ1 | Post-Filter | CSS visual+geo search -> RDS availability/ETA |
| CQ2 | Bidirectional | RDS user history -> CSS visual search -> RDS promotions |
| CQ3 | Parallel | CSS search || RDS deals -> intersection merge |
| CQ4 | RDS-First | RDS favorite restaurant -> CSS similar dishes -> RDS pricing |
| CQ5 | Post-Filter + Aggregation | CSS candidates -> RDS group-by restaurant |

RDS tables include: `menu_items` (availability, pricing, stock), `restaurants` (delivery fees, hours), `orders` (history, ratings), and `promotions` (active discounts).

### Phase 5: Performance Tests (`run_performance_tests.sh` + `locustfile.py`)

Runs Locust load tests at 3 load levels (20, 100, 200 concurrent users). The `locustfile.py` defines weighted user tasks:

- **Business queries** (high weight): Pure vector search, vector+city, vector+geo, vector+price, vector+multi-filter, hybrid text+vector, vector+amenities
- **Generic queries** (low weight): K=100, K=500, multi-vector, cluster health, node stats

### Phase 6: Autoscaling (`monitor_autoscaling.py` + `phase5_controller.py`)

Aggressively ramps load to trigger CSS data node horizontal autoscaling:

1. **`monitor_autoscaling.py`** runs in background, collecting cluster metrics (CPU, heap, disk) every 10s and detecting scaling events in real-time
2. **`phase5_controller.py`** drives the load through Locust bursts (master+workers distributed mode), progressing through states: `RAMP_UP` -> `SCALE_OUT_WAIT` -> `COOLDOWN` -> `SCALE_IN_WAIT` -> `DONE`

Scaling decisions use a **hysteresis-based engine** (`scaling_engine.py`):
- **Scale OUT**: when ANY metric exceeds its threshold (CPU >= 75%, Heap >= 80%, Disk >= 75%)
- **Scale IN**: when ALL metrics are below their thresholds (CPU <= 30%, Heap <= 40%, Disk <= 40%)
- Cooldown periods prevent thrashing (180s scale-out, 300s scale-in)

Scaling operations are executed via the **Huawei Cloud CSS SDK** (`huawei_css_api.py`) using AK/SK authentication.

### Phase 7: Report Generation (`generate_report.py`)

Consolidates all metrics into a single report covering ingestion throughput, query latencies, performance under load, API test results, and autoscaling events.

## Configuration

All settings are loaded from a `.env` file (see `.env.example` for template):

```bash
# CSS Cluster
CSS_HOST=your-css-host
CSS_PORT=9200
CSS_USERNAME=admin
CSS_PASSWORD=your-password
CSS_CLUSTER_ID=your-cluster-id
INDEX_NAME=benchmark_vectors
VECTOR_DIMENSION=128

# Huawei Cloud API
HW_ACCESS_KEY=your-ak
HW_SECRET_KEY=your-sk
HW_PROJECT_ID=your-project-id
HW_REGION=la-north-2

# Benchmark
INGESTION_TOTAL_VECTORS=10000
INGESTION_BATCH_SIZE=100
EVAL_N_QUERIES=100

# Autoscaling Thresholds
SCALE_OUT_CPU_THRESHOLD=75
SCALE_OUT_HEAP_THRESHOLD=80
SCALE_IN_CPU_THRESHOLD=30
SCALE_IN_HEAP_THRESHOLD=40
MIN_DATA_NODES=3
MAX_DATA_NODES=10
```

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv ~/css-benchmark-env
source ~/css-benchmark-env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env with your CSS cluster and Huawei Cloud credentials

# 4. Run full benchmark (all 7 phases)
bash run_complete_benchmark.sh

# 5. Or verify dependencies only
bash run_complete_benchmark.sh --dry-run
```

## Individual Components

Each Python script can also be run independently:

```bash
# Index setup
python3 setup_css_index.py

# Ingestion benchmark
python3 ingesta_benchmark.py

# Query evaluation
python3 evaluaciones_benchmark.py

# Cross-query benchmark (CSS + RDS)
python3 cross_query_benchmark.py

# API tests
python3 apis_test.py

# Standalone load generator
python3 load_generator.py --host YOUR_HOST --knn-search --duration 60

# Autoscaler (standalone)
python3 data_node_autoscaler.py

# Report generation
python3 generate_report.py
```

## Output

Results are saved to a timestamped directory `results_YYYYMMDD_HHMMSS/` containing:

| File | Content |
|---|---|
| `fase1_setup.log` | Index creation log |
| `fase2_ingesta.log` | Ingestion progress log |
| `ingesta_metrics.csv` | Throughput checkpoints |
| `fase3_evaluaciones.log` | Query evaluation log |
| `evaluaciones_results.csv` | Latency and recall metrics |
| `fase4_cross_queries.log` | Cross-query benchmark log |
| `cross_query_results.csv` | CSS/RDS latency breakdown |
| `performance_*.html` | Interactive Locust reports |
| `performance_*_stats.csv` | Locust statistics |
| `data_node_autoscaler_output.log` | Autoscaler log |
| `phase5_controller.log` | Load controller log |
| `phase5_burst_*.html` | Per-burst Locust reports |
| `autoscaling_monitor.csv` | Cluster metrics time series |
| `REPORTE_FINAL_CSS_BENCHMARK.txt` | Consolidated executive summary |

## Dependencies

- **opensearch-py** 2.4.2 - CSS/OpenSearch client
- **locust** 2.17.0 - Load testing framework
- **numpy** 1.26.0 - Vector generation and manipulation
- **pandas** 2.1.0 - Metrics data processing
- **scikit-learn** 1.3.0 - Recall/precision computation
- **Pillow** 10.1.0 - Synthetic image generation for embeddings
- **faker** 20.1.0 - Realistic data generation
- **huaweicloudsdkcss** - Huawei Cloud CSS API (for autoscaling)
- **tabulate** 0.9.0 - Formatted table output

## Key Design Decisions

- **Hot data nodes only**: The autoscaler monitors and scales only **hot data nodes** (type: `ess`), excluding cold/warm/frozen tiers and cluster manager nodes
- **Hysteresis scaling**: Scale-out triggers on ANY metric exceeding threshold; scale-in requires ALL metrics below threshold, with separate cooldowns
- **Real Huawei Cloud API**: Scaling operations use the official Huawei Cloud Python SDK with AK/SK authentication, not simulated scaling
- **Distributed Locust**: Phase 6 uses Locust master+worker mode for higher throughput during autoscaling stress tests
- **No hardcoded credentials**: All configuration flows through `.env` -> `config.py`
- **Graceful shutdown**: Signal handlers (SIGINT/SIGTERM) ensure cleanup of background processes, temporary files, and report generation on interruption
