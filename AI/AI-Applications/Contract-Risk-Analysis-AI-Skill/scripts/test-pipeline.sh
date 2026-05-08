#!/usr/bin/env bash
# Test Contract Risk Analysis Pipeline End-to-End
# Usage: bash scripts/test-pipeline.sh [API_ENDPOINT] [PDF_PATH]
#
# Prerequisites:
#   - curl, jq installed
#   - API running and accessible
#   - Test PDF available

set -euo pipefail

API_ENDPOINT="${1:-http://<YOUR_API_IP>:8001}"
PDF_PATH="${2:-data/contracts/contrato-01-alto-riesgo.pdf}"
TIMEOUT=60

echo "=== Contract Risk Analysis Pipeline Test ==="
echo "API: $API_ENDPOINT"
echo "PDF: $PDF_PATH"
echo ""

# 1. Health check
echo "[1/4] Health check..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/api/health" || echo "000")
if [ "$HEALTH" != "200" ]; then
    echo "  FAIL: Health check returned $HEALTH"
    exit 1
fi
echo "  OK: API is healthy"

# 2. Upload document
echo "[2/4] Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_ENDPOINT/api/upload" \
    -F "file=@$PDF_PATH" \
    --max-time 30)

JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.job_id // empty')
if [ -z "$JOB_ID" ]; then
    echo "  FAIL: No job_id returned"
    echo "  Response: $UPLOAD_RESPONSE"
    exit 1
fi
echo "  OK: job_id=$JOB_ID"

# 3. Poll for completion
echo "[3/4] Waiting for pipeline completion..."
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))

    STATUS_RESPONSE=$(curl -s "$API_ENDPOINT/api/status/$JOB_ID" || echo '{}')
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // "unknown"')

    case "$STATUS" in
        completed)
            echo "  OK: Pipeline completed in ${ELAPSED}s"
            break
            ;;
        failed)
            echo "  FAIL: Pipeline failed"
            echo "  Response: $STATUS_RESPONSE"
            exit 1
            ;;
        *)
            echo "  Waiting... (${ELAPSED}s, status=$STATUS)"
            ;;
    esac
done

if [ "$STATUS" != "completed" ]; then
    echo "  FAIL: Pipeline timed out after ${TIMEOUT}s"
    exit 1
fi

# 4. Validate result
echo "[4/4] Validating result..."
RISK_LEVEL=$(echo "$STATUS_RESPONSE" | jq -r '.result.risk_level // "unknown"')
RISK_SCORE=$(echo "$STATUS_RESPONSE" | jq -r '.result.risk_score // -1')
ALERTAS=$(echo "$STATUS_RESPONSE" | jq -r '.result.alertas | length // 0')

if [ "$RISK_LEVEL" = "unknown" ] || [ "$RISK_SCORE" = "-1" ]; then
    echo "  FAIL: Missing risk data in result"
    echo "  Response: $STATUS_RESPONSE"
    exit 1
fi

echo "  OK: risk_level=$RISK_LEVEL risk_score=$RISK_SCORE alerts=$ALERTAS"
echo ""
echo "=== Test Complete ==="
echo "Result: PASS"
echo "Pipeline processed $PDF_PATH → $RISK_LEVEL (score=$RISK_SCORE)"
