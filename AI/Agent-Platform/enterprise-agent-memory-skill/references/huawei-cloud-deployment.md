# Huawei Cloud Deployment

## Resources

| Resource | Purpose | Specification |
|---|---|---|
| CSS/OpenSearch | L4 Semantic Index (vector + keyword search) | Single-node, 4 vCPUs, 16GB RAM, 100GB disk |
| OBS | L2 Episodic Buffer backups | Standard storage class, tenant-scoped buckets |
| ECS | Agent runtime + compression engine | General-purpose, 4 vCPUs, 8GB RAM |
| RDS/GaussDB | Audit log storage | MySQL-compatible, 2 vCPUs, 4GB RAM |
| VPC | Network isolation | Tenant-scoped VPC with security groups |

## SDK Setup

```bash
# Install Huawei Cloud CLI
pip install hcloud

# Configure credentials (never hardcode)
export HWC_REGION="la-north-2"
export HWC_ACCESS_KEY_ID="${HWC_ACCESS_KEY_ID}"
export HWC_SECRET_ACCESS_KEY="${HWC_SECRET_ACCESS_KEY}"
export HWC_PROJECT_ID="${HWC_PROJECT_ID}"
```

## CSS/OpenSearch Provisioning

```bash
# Create CSS cluster for L4 semantic index
hcloud css create \
  --name "agent-memory-semantic" \
  --region "${HWC_REGION}" \
  --flavor "css.medium.4" \
  --node-size 1 \
  --disk-size 100 \
  --disk-type "HIGH" \
  --vpc-id "${VPC_ID}" \
  --subnet-id "${SUBNET_ID}" \
  --security-group-id "${SG_ID}"
```

## OBS Bucket Provisioning

```bash
# Create OBS bucket for L2 episodic backups
hcloud obs create-bucket \
  --bucket "hwc-memory-${TENANT_ID}-${HWC_REGION}" \
  --region "${HWC_REGION}" \
  --storage-class "STANDARD"
```

## RDS/GaussDB for Audit Logs

```bash
# Create RDS instance for audit log storage
hcloud rds create \
  --name "agent-memory-audit" \
  --region "${HWC_REGION}" \
  --flavor "rds.mysql.c2.large" \
  --disk-size 50 \
  --vpc-id "${VPC_ID}" \
  --subnet-id "${SUBNET_ID}"
```

## Verification Commands

```bash
# Verify CSS cluster is available
hcloud css show --cluster-id "${CSS_CLUSTER_ID}" --query "status"

# Verify OBS bucket exists
hcloud obs head-bucket --bucket "hwc-memory-${TENANT_ID}-${HWC_REGION}"

# Verify RDS instance is running
hcloud rds show --instance-id "${RDS_INSTANCE_ID}" --query "status"

# Test vector index connectivity
curl -s "https://${CSS_ENDPOINT}/_cluster/health?pretty"
```

## Deployment Defaults

- Region: `la-north-2`
- CSS disk type: HIGH (SSD)
- OBS storage class: STANDARD
- RDS engine: MySQL 8.0
- All resources encrypted at rest and in transit
- Security group restricts CSS/RDS to ECS subnet only
- EIP restricted to operator's current public IP (for demo only)

## Cleanup

```bash
# Delete all provisioned resources (use with caution)
hcloud css delete --cluster-id "${CSS_CLUSTER_ID}"
hcloud obs delete-bucket --bucket "hwc-memory-${TENANT_ID}-${HWC_REGION}" --force
hcloud rds delete --instance-id "${RDS_INSTANCE_ID}"
```
