#!/usr/bin/env bash
set -euo pipefail

REGION="${HWC_REGION:-la-north-2}"
PROJECT_ID="${HWC_PROJECT_ID:?HWC_PROJECT_ID is required}"
TENANT_ID="${TENANT_ID:-default}"
WITH_GRAPHRAG="${1:-true}"
WITH_MCP="${2:-true}"
STATE_FILE=".rag-deploy-state.json"

echo "=== Deploying Project Memory RAG Pipeline ==="
echo "Region: ${REGION}"
echo "Project: ${PROJECT_ID}"
echo "Tenant: ${TENANT_ID}"
echo "GraphRAG: ${WITH_GRAPHRAG}"
echo "MCP: ${WITH_MCP}"

# Create VPC if not provided
if [ -z "${VPC_ID:-}" ]; then
  echo "Creating VPC..."
  VPC_ID=$(hcloud vpc create --name "project-memory-vpc" --region "${REGION}" --cidr "10.0.0.0/16" --query "vpc.id")
  echo "VPC created: ${VPC_ID}"
fi

# Create OBS bucket for document storage
echo "Creating OBS bucket for document storage..."
OBS_BUCKET="hwc-project-docs-${TENANT_ID}-${REGION}"
hcloud obs create-bucket \
  --bucket "${OBS_BUCKET}" \
  --region "${REGION}" \
  --storage-class "STANDARD" || echo "Bucket may already exist"

# Create CSS/OpenSearch cluster for all indices
echo "Creating CSS/OpenSearch cluster for memory indices..."
CSS_CLUSTER_ID=$(hcloud css create \
  --name "project-memory-indices-${TENANT_ID}" \
  --region "${REGION}" \
  --flavor "css.medium.4" \
  --node-size 1 \
  --disk-size 200 \
  --disk-type "HIGH" \
  --vpc-id "${VPC_ID}" \
  --query "cluster.id")
echo "CSS cluster created: ${CSS_CLUSTER_ID}"

# Create RDS for metadata and audit
echo "Creating RDS/GaussDB for metadata and audit..."
RDS_INSTANCE_ID=$(hcloud rds create \
  --name "project-memory-audit-${TENANT_ID}" \
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
  "project_id": "${PROJECT_ID}",
  "tenant_id": "${TENANT_ID}",
  "vpc_id": "${VPC_ID}",
  "obs_bucket": "${OBS_BUCKET}",
  "css_cluster_id": "${CSS_CLUSTER_ID}",
  "rds_instance_id": "${RDS_INSTANCE_ID}",
  "with_graphrag": ${WITH_GRAPHRAG},
  "with_mcp": ${WITH_MCP},
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "=== Deployment complete. State saved to ${STATE_FILE} ==="
echo "Next: Deploy RAGFlow on ECS and create CSS indices."
