# SQL Safety Validation

## Why Validate

LLMs can generate dangerous SQL. Without validation:
- DROP TABLE, DELETE, UPDATE can destroy data
- INSERT can corrupt results
- UNION-based queries can leak data across schemas
- Subqueries can cause performance issues

## Whitelist Approach

Only allow SELECT and WITH (CTEs). Block everything else:

```python
import re

DANGEROUS_SQL = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b',
    re.IGNORECASE
)

def validate_sql(sql):
    """Return (is_safe, reason). Block anything that isn't SELECT."""
    stripped = sql.strip().rstrip(';').strip()

    # Must start with SELECT or WITH
    if not stripped.upper().startswith(('SELECT', 'WITH')):
        return False, f"Solo SELECT permitido. Detectado: {stripped[:40]}..."

    # Block dangerous operations
    if DANGEROUS_SQL.search(sql):
        return False, "Query contiene operaciones no permitidas (DDL/DML)."

    return True, ""
```

## LIMIT Enforcement

Always add LIMIT if the LLM forgot:

```python
def enforce_limit(sql, max_rows=200):
    """Add LIMIT if missing."""
    if 'limit' not in sql.lower():
        sql = sql.rstrip(';') + f' LIMIT {max_rows}'
    return sql
```

## Blocking Patterns

| Pattern | Risk | Action |
|---------|------|--------|
| `INSERT INTO` | Data corruption | Block |
| `UPDATE ... SET` | Data corruption | Block |
| `DELETE FROM` | Data loss | Block |
| `DROP TABLE` | Schema destruction | Block |
| `ALTER TABLE` | Schema change | Block |
| `CREATE TABLE` | Schema change | Block |
| `TRUNCATE` | Data loss | Block |
| `GRANT` / `REVOKE` | Permission change | Block |
| `EXEC` / `EXECUTE` | Code execution | Block |
| `UNION` (without SELECT first) | Data leak | Allow with caution |
| `INTO OUTFILE` | File write | Block |

## Additional Safety Rules

- Never allow `pg_catalog` or `information_schema` access.
- Never allow `\!` (psql shell commands).
- Never allow `COPY TO` (file export).
- Always use parameterized queries when possible.
- Log all generated SQL for audit trail.
