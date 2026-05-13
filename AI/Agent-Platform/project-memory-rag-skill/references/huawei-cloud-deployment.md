# Huawei Cloud Deployment

## Resources

| Resource | Purpose | Specification |
|---|---|---|
| OBS | Document storage (raw files) | Standard class, tenant-scoped |
| CSS/OpenSearch | Learned memory index + document chunk index + graph index | Single-node, 4 vCPUs, 16GB RAM, 200GB disk |
| RAGFlow | Document parsing, OCR, chunking | Docker Compose on ECS |
| ECS | Agent runtime + RAGFlow | General-purpose, 8 vCPUs, 16GB RAM |
| RDS/GaussDB | Metadata + audit logs | MySQL-compatible, 2 vCPUs, 4GB RAM |

## SDK Setup

```bash
export HWC_REGION="la-north-2"
export HWC_ACCESS_KEY_ID="${HWC_ACCESS_KEY_ID}"
export HWC_SECRET_ACCESS_KEY="${HWC_SECRET_ACCESS_KEY}"
export HWC_PROJECT_ID="${HWC_PROJECT_ID}"
```

## OBS for Document Storage

```bash
# Create OBS bucket for document storage
hcloud obs create-bucket \
  --bucket "hwc-project-docs-${TENANT_ID}-${HWC_REGION}" \
  --region "${HWC_REGION}" \
  --storage-class "STANDARD"
```

## CSS/OpenSearch for Indices

```bash
# Create CSS cluster for all indices
hcloud css create \
  --name "project-memory-indices" \
  --region "${HWC_REGION}" \
  --flavor "css.medium.4" \
  --node-size 1 \
  --disk-size 200 \
  --disk-type "HIGH" \
  --vpc-id "${VPC_ID}" \
  --subnet-id "${SUBNET_ID}" \
  --security-group-id "${SG_ID}"

# Create learned memory index
curl -X PUT "https://${CSS_ENDPOINT}/learned_memory_v1" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "insight": {"type": "text"},
      "embedding": {"type": "knn_vector", "dimension": 1536},
      "tags": {"type": "keyword"},
      "confidence": {"type": "float"},
      "derived_at": {"type": "date"},
      "derived_from": {"type": "keyword"}
    }
  }
}'

# Create document chunk index
curl -X PUT "https://${CSS_ENDPOINT}/document_chunks_v1" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "content": {"type": "text"},
      "embedding": {"type": "knn_vector", "dimension": 1536},
      "source": {"type": "keyword"},
      "page": {"type": "integer"},
      "chunk_id": {"type": "keyword"}
    }
  }
}'

# Create graph index
curl -X PUT "https://${CSS_ENDPOINT}/graph_entities_v1" -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "entity_name": {"type": "keyword"},
      "entity_type": {"type": "keyword"},
      "embedding": {"type": "knn_vector", "dimension": 1536},
      "relationships": {"type": "nested"}
    }
  }
}'
```

## RAGFlow on ECS

```bash
# Deploy RAGFlow via Docker Compose on ECS
ssh ecs-instance "docker compose -f /opt/ragflow/docker-compose.yml up -d"
```

## Verification Commands

```bash
# Verify CSS cluster
hcloud css show --cluster-id "${CSS_CLUSTER_ID}" --query "status"

# Verify learned memory index
curl -s "https://${CSS_ENDPOINT}/learned_memory_v1/_count?pretty"

# Verify document chunk index
curl -s "https://${CSS_ENDPOINT}/document_chunks_v1/_count?pretty"

# Verify graph index
curl -s "https://${CSS_ENDPOINT}/graph_entities_v1/_count?pretty"

# Verify OBS bucket
hcloud obs head-bucket --bucket "hwc-project-docs-${TENANT_ID}-${HWC_REGION}"

# Verify RAGFlow
curl -s "http://${ECS_IP}:9380/api/v1/system/status"
```

## Deployment Defaults

- Region: `la-north-2`
- All resources encrypted at rest and in transit
- Security group restricts CSS/RDS to ECS subnet only
- RAGFlow on dedicated ECS with Docker Compose
