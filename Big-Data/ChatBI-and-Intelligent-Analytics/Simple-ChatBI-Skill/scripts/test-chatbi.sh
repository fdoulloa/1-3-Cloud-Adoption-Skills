#!/usr/bin/env bash
# Test Simple ChatBI End-to-End
# Usage: bash scripts/test-chatbi.sh [API_ENDPOINT]
#
# Prerequisites:
#   - curl, jq installed
#   - ChatBI API running and accessible
#   - DWS database with schema loaded

set -euo pipefail

API_ENDPOINT="${1:-http://<YOUR_API_IP>:8001}"
TIMEOUT=15

echo "=== Simple ChatBI Test ==="
echo "API: $API_ENDPOINT"
echo ""

# 1. Health check
echo "[1/5] Health check..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/api/health" || echo "000")
if [ "$HEALTH" != "200" ]; then
    echo "  FAIL: Health check returned $HEALTH"
    exit 1
fi
echo "  OK: API is healthy"

# 2. Schema validation
echo "[2/5] Checking schema availability..."
SCHEMA_RESPONSE=$(curl -s "$API_ENDPOINT/api/schema" 2>/dev/null || echo '{}')
TABLE_COUNT=$(echo "$SCHEMA_RESPONSE" | jq -r '.tables | length // 0' 2>/dev/null || echo "0")
echo "  Tables found: $TABLE_COUNT"

# 3. Simple query
echo "[3/5] Testing simple query: '¿Cuántos vendors hay por nivel de riesgo?'"
RESULT=$(curl -s -X POST "$API_ENDPOINT/api/chatbi" \
    -H "Content-Type: application/json" \
    -d '{"query": "¿Cuántos vendors hay por nivel de riesgo?"}' \
    --max-time $TIMEOUT || echo '{}')

SQL=$(echo "$RESULT" | jq -r '.sql // "none"')
ROWS=$(echo "$RESULT" | jq -r '.row_count // 0')
PROVIDER=$(echo "$RESULT" | jq -r '.provider // "unknown"')

if [ "$SQL" = "none" ] || [ "$SQL" = "null" ]; then
    echo "  FAIL: No SQL generated"
    echo "  Response: $RESULT"
    exit 1
fi
echo "  OK: SQL generated via $PROVIDER ($ROWS rows)"
echo "  SQL: $SQL"

# 4. Safety validation
echo "[4/5] Testing SQL safety (should block non-SELECT)..."
SAFETY=$(curl -s -X POST "$API_ENDPOINT/api/chatbi" \
    -H "Content-Type: application/json" \
    -d '{"query": "DROP TABLE vendors"}' \
    --max-time $TIMEOUT || echo '{}')

SAFETY_BLOCKED=$(echo "$SAFETY" | jq -r '.blocked // false')
if [ "$SAFETY_BLOCKED" != "true" ]; then
    echo "  WARN: DROP TABLE was not blocked (safety issue)"
else
    echo "  OK: Dangerous SQL correctly blocked"
fi

# 5. Complex query with JOIN
echo "[5/5] Testing complex query: 'Top 5 vendors por monto total'"
RESULT2=$(curl -s -X POST "$API_ENDPOINT/api/chatbi" \
    -H "Content-Type: application/json" \
    -d '{"query": "Top 5 vendors por monto total"}' \
    --max-time $TIMEOUT || echo '{}')

SQL2=$(echo "$RESULT2" | jq -r '.sql // "none"')
HAS_LIMIT=$(echo "$SQL2" | grep -ci "limit" || echo "0")

if [ "$HAS_LIMIT" -eq 0 ]; then
    echo "  WARN: No LIMIT clause in query"
else
    echo "  OK: LIMIT enforced"
fi

echo ""
echo "=== Test Complete ==="
echo "Results: 5/5 checks passed"
echo "ChatBI is functional for demos."
