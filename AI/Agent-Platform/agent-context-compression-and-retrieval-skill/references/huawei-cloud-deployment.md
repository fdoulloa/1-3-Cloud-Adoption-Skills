# Huawei Cloud Deployment

## Resources

| Resource | Purpose | Specification |
|---|---|---|
| CSS/OpenSearch | T1 and T2 tier storage | Single-node, 4 vCPUs, 16GB RAM, 100GB disk |
| OBS | T3 raw detail storage | Standard storage class, lifecycle policy for old raw data |
| ECS | Compression service runtime | General-purpose, 4 vCPUs, 8GB RAM |

## SDK Setup

```bash
export HWC_REGION="la-north-2"
export HWC_ACCESS_KEY_ID="${HWC_ACCESS_KEY_ID}"
export HWC_SECRET_ACCESS_KEY="${HWC_SECRET_ACCESS_KEY}"
export HWC_PROJECT_ID="${HWC_PROJECT_ID}"
```

## CSS/OpenSearch for Tier Storage

```bash
# Create CSS cluster for T1 and T2 tiers
hcloud css create \
  --name "compression-tiers" \
  --region "${HWC_REGION}" \
  --flavor "css.medium.4" \
  --node-size 1 \
  --disk-size 100 \
  --disk-type "HIGH" \
  --vpc-id "${VPC_ID}" \
  --subnet-id "${SUBNET_ID}" \
  --security-group-id "${SG_ID}"

# Create T1 index (summaries)
curl -X PUT "https://${CSS_ENDPOINT}/compression_t1_v1" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "summary": {"type": "text"},
      "embedding": {"type": "knn_vector", "dimension": 1536},
      "timestamp": {"type": "date"},
      "session_id": {"type": "keyword"}
    }
  }
}'

# Create T2 index (artifacts)
curl -X PUT "https://${CSS_ENDPOINT}/compression_t2_v1" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "artifact_type": {"type": "keyword"},
      "summary": {"type": "text"},
      "detail": {"type": "text"},
      "embedding": {"type": "knn_vector", "dimension": 1536},
      "relevance_tags": {"type": "keyword"},
      "timestamp": {"type": "date"},
      "session_id": {"type": "keyword"}
    }
  }
}'
```

## OBS for T3 Raw Storage

```bash
# Create OBS bucket for T3 raw context
hcloud obs create-bucket \
  --bucket "hwc-compression-raw-${HWC_REGION}" \
  --region "${HWC_REGION}" \
  --storage-class "STANDARD"

# Set lifecycle policy: transition to GLACIER after 30 days
hcloud obs lifecycle \
  --bucket "hwc-compression-raw-${HWC_REGION}" \
  --rule-id "archive-old-raw" \
  --prefix "t3/" \
  --transition-days 30 \
  --storage-class "GLACIER"
```

## Verification Commands

```bash
# Verify CSS cluster
hcloud css show --cluster-id "${CSS_CLUSTER_ID}" --query "status"

# Verify T1 index
curl -s "https://${CSS_ENDPOINT}/compression_t1_v1/_count?pretty"

# Verify T2 index
curl -s "https://${CSS_ENDPOINT}/compression_t2_v1/_count?pretty"

# Verify OBS bucket
hcloud obs head-bucket --bucket "hwc-compression-raw-${HWC_REGION}"
```

## Deployment Defaults

- Region: `la-north-2`
- Compression threshold: 70% context utilization
- T1 budget: 2K tokens
- T2 budget: 8K tokens
- T3 lifecycle: GLACIER after 30 days
- All resources encrypted at rest and in transit
