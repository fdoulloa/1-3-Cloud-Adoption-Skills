# Tiered Recall

## T1 — Compressed Summary

- **Token budget**: <2K tokens
- **Loading**: Always loaded at session start
- **Content**: Project overview, recent work summary, active goals, key conventions
- **Storage**: CSS/OpenSearch index `compression_t1_`
- **Update frequency**: After each compression operation
- **Self-contained**: Must be understandable without T2 or T3

Example T1 summary:
```
Project: payment-service migration
Recent: Migrated 3/5 endpoints from v1 to v2 API
Active: Debugging timeout on /payments/refund endpoint
Convention: All endpoints use circuit-breaker pattern
Last session: Identified root cause as connection pool exhaustion
```

## T2 — Key Artifacts

- **Token budget**: <8K tokens
- **Loading**: On relevance match (when current task relates to stored artifacts)
- **Content**: Decisions with rationale, outcomes, file changes, error resolutions, code patterns
- **Storage**: CSS/OpenSearch index `compression_t2_`
- **Relevance scoring**: Cosine similarity between current task embedding and artifact embedding

Relevance scoring formula:
```
score = cosine_similarity(task_embedding, artifact_embedding) × recency_weight
recency_weight = exp(-0.1 × days_since_artifact)
```

Loading trigger: score > 0.7 (configurable threshold)

## T3 — Raw Detail

- **Token budget**: Original size (no compression)
- **Loading**: Only on explicit agent request
- **Content**: Full context — all tool calls, outputs, reasoning, intermediate steps
- **Storage**: OBS bucket (cost-effective for large raw data)
- **Access**: Signed URL with TTL (time-limited access)

Loading trigger: Agent explicitly requests full detail for a specific artifact ID.

## Cache Invalidation

- T1 is rebuilt after every compression operation
- T2 entries are invalidated when source artifacts are modified (content hash comparison)
- T3 raw data is immutable (append-only, never modified)
- Cache TTL: T1 = 0 (always fresh), T2 = 1 hour, T3 = indefinite

## Tier Promotion/Demotion

- T2 → T1: When an artifact is referenced in >3 sessions, promote key points to T1 summary
- T3 → T2: When raw detail is accessed >2 times, extract artifacts and store in T2
- T1 → T2: When T1 summary grows beyond 2K tokens, demote older items to T2
