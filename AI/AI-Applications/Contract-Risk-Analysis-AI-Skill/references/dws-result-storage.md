# DWS Result Storage Patterns

## Three-Layer Schema Design

Use a three-layer schema pattern for risk analysis results:

```
ods (Operational Data Store)  → Raw data from pipeline
dw (Data Warehouse)           → Star schema for analytics
dm (Data Mart)                → Aggregated views for dashboards
```

### ODS Layer — Raw Results

Store raw pipeline output as-is. No transformations.

```sql
CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE ods.risk_results_raw (
    job_id          VARCHAR(64) PRIMARY KEY,
    contract_number VARCHAR(128),
    status          VARCHAR(32),
    risk_score      INTEGER,
    risk_level      VARCHAR(32),
    alertas         TEXT,          -- JSON array as text
    recomendaciones TEXT,          -- JSON array as text
    resumen         TEXT,
    llm_provider    VARCHAR(64),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DW Layer — Star Schema

Normalize for analytical queries.

```sql
CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE dw.dim_contracts (
    contract_id     SERIAL PRIMARY KEY,
    contract_number VARCHAR(128) UNIQUE,
    risk_level      VARCHAR(32),
    risk_score      INTEGER,
    llm_provider    VARCHAR(64),
    processed_at    TIMESTAMP
);

CREATE TABLE dw.fact_alerts (
    alert_id    SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES dw.dim_contracts(contract_id),
    alert_text  VARCHAR(256),
    category    VARCHAR(64)
);
```

### DM Layer — Aggregated Views

Create views for dashboard consumption.

```sql
CREATE SCHEMA IF NOT EXISTS dm;

CREATE OR REPLACE VIEW dm.risk_summary AS
SELECT
    risk_level,
    COUNT(*) AS contract_count,
    AVG(risk_score) AS avg_score,
    MAX(risk_score) AS max_score
FROM dw.dim_contracts
GROUP BY risk_level;
```

## Check Constraints

DWS/GaussDB enforces check constraints on risk levels. Always validate before insert:

```sql
ALTER TABLE ods.risk_results_raw
ADD CONSTRAINT risk_level_check
CHECK (risk_level IN ('BAJO', 'MEDIO', 'ALTO', 'CRITICO', 'PENDIENTE'));
```

**Common failure:** Inserting a risk_level like `'Indeterminado'` or `'UNKNOWN'` violates this constraint and crashes the pipeline.

## DWS Connection Pattern

```python
import psycopg2

def get_dws_connection():
    return psycopg2.connect(
        host="<YOUR_DWS_ENDPOINT>",
        port=8000,
        database="<YOUR_DATABASE>",
        user="<YOUR_USER>",
        password="<YOUR_PASSWORD>",
        connect_timeout=10
    )

def insert_risk_result(result):
    conn = get_dws_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ods.risk_results_raw
                (job_id, contract_number, status, risk_score, risk_level,
                 alertas, recomendaciones, resumen, llm_provider)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                result["job_id"],
                result["contract_number"],
                "completed",
                result["risk_score"],
                result["risk_level"],
                json.dumps(result["alertas"]),
                json.dumps(result["recomendaciones"]),
                result["resumen"],
                result.get("llm_provider", "unknown")
            ))
        conn.commit()
    finally:
        conn.close()
```

## DataService REST API

Expose DWS data through DataArts DataService for frontend consumption:

```yaml
# DataArts DataService API definition
api_name: risk-results-api
type: REST
datasource: <YOUR_DWS_CONNECTION>
request_type: GET
path: /api/risk-results
sql: |
  SELECT contract_number, risk_level, risk_score, alertas, created_at
  FROM ods.risk_results_raw
  ORDER BY created_at DESC
  LIMIT 100
```

## DWS Limitations

- **No foreign keys** — enforce referential integrity in application code
- **No SERIAL auto-increment** — use application-generated IDs or sequences
- **No materialized views** — use regular views; re-execute on every query
- **Risk level comparison is alphabetical** — `"MEDIO" > "CRITICO"` alphabetically. Use CASE statements for severity ordering.
