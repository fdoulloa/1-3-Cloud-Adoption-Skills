#!/usr/bin/env bash
set -euo pipefail

REGION="${HWC_REGION:-la-north-2}"
STORE_TYPE="${1:-css}"
PROJECT_ID="${HWC_PROJECT_ID:?HWC_PROJECT_ID is required}"
TENANT_ID="${TENANT_ID:-default}"
STATE_FILE=".memory-deploy-state.json"

echo "=== Deploying Enterprise Agent Memory Store ==="
echo "Region: ${REGION}"
echo "Store type: ${STORE_TYPE}"
echo "Project: ${PROJECT_ID}"
echo "Tenant: ${TENANT_ID}"

# Create VPC if not provided
if [ -z "${VPC_ID:-}" ]; then
  echo "Creating VPC..."
  VPC_ID=$(hcloud vpc create --name "agent-memory-vpc" --region "${REGION}" --cidr "10.0.0.0/16" --query "vpc.id")
  echo "VPC created: ${VPC_ID}"
fi

# Create CSS/OpenSearch cluster for L4 semantic index
if [ "${STORE_TYPE}" = "css" ]; then
  echo "Creating CSS/OpenSearch cluster for L4 semantic index..."
  CSS_CLUSTER_ID=$(hcloud css create \
    --name "agent-memory-semantic-${TENANT_ID}" \
    --region "${REGION}" \
    --flavor "css.medium.4" \
    --node-size 1 \
    --disk-size 100 \
    --disk-type "HIGH" \
    --vpc-id "${VPC_ID}" \
    --query "cluster.id")
  echo "CSS cluster created: ${CSS_CLUSTER_ID}"
fi

# Create OBS bucket for L2 episodic backups
echo "Creating OBS bucket for L2 episodic backups..."
OBS_BUCKET="hwc-memory-${TENANT_ID}-${REGION}"
hcloud obs create-bucket \
  --bucket "${OBS_BUCKET}" \
  --region "${REGION}" \
  --storage-class "STANDARD" || echo "Bucket may already exist"

# Create RDS instance for audit logs
echo "Creating RDS/GaussDB instance for audit logs..."
RDS_INSTANCE_ID=$(hcloud rds create \
  --name "agent-memory-audit-${TENANT_ID}" \
  --region "${REGION}" \
  --flavor "rds.mysql.c2.large" \
  --disk-size 50 \
  --vpc-id "${VPC_ID}" \
  --query "instance.id")
echo "RDS instance created: ${RDS_INSTANCE_ID}"

# Write deployment state
cat > "${STATE_FILE}" <<EOF
{
  "region": "${REGION}",
  "store_type": "${STORE_TYPE}",
  "project_id": "${PROJECT_ID}",
  "tenant_id": "${TENANT_ID}",
  "vpc_id": "${VPC_ID}",
  "css_cluster_id": "${CSS_CLUSTER_ID:-}",
  "obs_bucket": "${OBS_BUCKET}",
  "rds_instance_id": "${RDS_INSTANCE_ID}",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "=== Deployment complete. State saved to ${STATE_FILE} ==="
