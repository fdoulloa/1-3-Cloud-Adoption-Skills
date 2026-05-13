# Privacy and Audit

## Sensitive Content Exclusion

Default exclusion patterns (checked before storage):

| Pattern | Description | Regex |
|---|---|---|
| API Keys | Generic API key patterns | `(?:api[_-]?key\|apikey)\s*[:=]\s*["']?[A-Za-z0-9]{20,}` |
| AWS/HWC Access Keys | Cloud provider keys | `AKIA[0-9A-Z]{16}\|HWC[A-Z]{34}` |
| Bearer Tokens | Auth tokens | `Bearer\s+[A-Za-z0-9\-._~+/]+=*` |
| Passwords | Password fields | `(?:password\|passwd\|pwd)\s*[:=]\s*["']?[^\s"']{8,}` |
| Private Keys | PEM keys | `-----BEGIN (?:RSA \|EC \|DSA )?PRIVATE KEY-----` |
| PII - Email | Email addresses | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| PII - Phone | Phone numbers | `\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}` |
| PII - CPF/CNPJ | Brazilian tax IDs | `\d{3}\.\d{3}\.\d{3}-\d{2}\|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` |

Custom exclusion patterns can be added in L5 configuration.

## Privacy Configuration Schema

```json
{
  "privacy": {
    "exclusion_patterns": ["custom_regex_1", "custom_regex_2"],
    "pii_detection": true,
    "pii_storage_consent": false,
    "redaction_mode": "replace",
    "redaction_placeholder": "[REDACTED]",
    "tenant_isolation": true,
    "data_residency": "la-north-2"
  }
}
```

## Audit Event Schema

Every capture, compress, store, and retrieve operation generates an audit event:

```json
{
  "timestamp": "2026-05-12T10:30:00Z",
  "operation": "capture|compress|store|retrieve|delete",
  "agent_id": "agent-001",
  "session_id": "sess-abc123",
  "memory_layer": "L1|L2|L3|L4|L5",
  "content_hash": "sha256:...",
  "token_count": 550,
  "privacy_status": "clean|redacted|blocked",
  "tenant_id": "tenant-001",
  "project_id": "project-001"
}
```

## Compliance Requirements

- **GDPR**: Right to erasure — support deletion of all memory for a given user/tenant
- **Data residency**: All storage in configured region (default `la-north-2`)
- **Retention policy**: Configurable per tenant (default: 90 days for L2, indefinite for L4)
- **Audit retention**: Audit logs retained per compliance policy (default: 1 year)
- **Encryption at rest**: CSS/OpenSearch and OBS encryption enabled by default
- **Encryption in transit**: TLS 1.2+ for all memory store connections

## Tenant Isolation

- Each tenant has a separate CSS/OpenSearch index prefix: `tenant_{id}_memory_*`
- OBS buckets are tenant-scoped: `hwc-memory-{tenant_id}-{region}`
- L2 SQLite databases are per-tenant files
- L3 skill directories are per-tenant: `.skills/{tenant_id}/`
- Cross-tenant access is blocked at the storage layer
