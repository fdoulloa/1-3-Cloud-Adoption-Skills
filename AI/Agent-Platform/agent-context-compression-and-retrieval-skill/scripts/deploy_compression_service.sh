#!/usr/bin/env bash
set -euo pipefail

REGION="${HWC_REGION:-la-north-2}"
STRATEGY="${1:-hybrid}"
PROJECT_ID="${HWC_PROJECT_ID:?HWC_PROJECT_ID is required}"
STATE_FILE=".compression-deploy-state.json"

echo "=== Deploying Agent Context Compression Service ==="
echo "Region: ${REGION}"
echo "Strategy: ${STRATEGY}"
echo "Project: ${PROJECT_ID}"

# Create VPC if not provided
if [ -z "${VPC_ID:-}" ]; then
  echo "Creating VPC..."
  VPC_ID=$(hcloud vpc create --name "compression-vpc" --region "${REGION}" --cidr "10.0.0.0/16" --query "vpc.id")
  echo "VPC created: ${VPC_ID}"
fi

# Create CSS/OpenSearch cluster for T1 and T2 tiers
echo "Creating CSS/OpenSearch cluster for tier storage..."
CSS_CLUSTER_ID=$(hcloud css create \
  --name "compression-tiers" \
  --region "${REGION}" \
  --flavor "css.medium.4" \
  --node-size 1 \
  --disk-size 100 \
  --disk-type "HIGH" \
  --vpc-id "${VPC_ID}" \
  --query "cluster.id")
echo "CSS cluster created: ${CSS_CLUSTER_ID}"

# Create OBS bucket for T3 raw storage
echo "Creating OBS bucket for T3 raw storage..."
OBS_BUCKET="hwc-compression-raw-${REGION}"
hcloud obs create-bucket \
  --bucket "${OBS_BUCKET}" \
  --region "${REGION}" \
  --storage-class "STANDARD" || echo "Bucket may already exist"

# Write deployment state
cat > "${STATE_FILE}" <<EOF
{
  "region": "${REGION}",
  "strategy": "${STRATEGY}",
  "project_id": "${PROJECT_ID}",
  "vpc_id": "${VPC_ID}",
  "css_cluster_id": "${CSS_CLUSTER_ID}",
  "obs_bucket": "${OBS_BUCKET}",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "=== Deployment complete. State saved to ${STATE_FILE} ==="
