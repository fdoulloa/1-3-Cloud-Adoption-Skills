# GraphRAG Design

## Entity Extraction

Entities are extracted from:
1. **Documents** — during RAGFlow parsing, named entities are extracted (people, organizations, systems, APIs, concepts)
2. **Agent interactions** — when the agent references entities in tool calls or decisions
3. **Learned memory** — when insights reference specific entities

Entity schema:
```json
{
  "entity_id": "ent_001",
  "name": "payment-service",
  "type": "system|person|organization|api|concept|document",
  "properties": {"language": "Java", "owner": "payments-team"},
  "mentions": 15,
  "first_seen": "2026-05-01T00:00:00Z",
  "last_seen": "2026-05-12T00:00:00Z"
}
```

## Relationship Mapping

Relationships connect entities with typed edges:

```json
{
  "source_id": "ent_001",
  "target_id": "ent_002",
  "type": "depends_on|calls|owns|implements|related_to",
  "weight": 0.85,
  "evidence": ["doc://architecture.pdf#page5", "insight://circuit-breaker-pattern"],
  "first_seen": "2026-05-01T00:00:00Z"
}
```

Common relationship types:
- `depends_on`: Service A depends on Service B
- `calls`: API A calls API B
- `owns`: Team A owns Service B
- `implements`: Service A implements Pattern B
- `related_to`: Generic relationship (lowest weight)

## Graph Traversal for Multi-Hop Queries

Single-hop: "What does the payment service depend on?" → Direct edge traversal

Multi-hop: "What services might be affected if the auth service goes down?" →
1. Find all services that depend on auth-service (1 hop)
2. Find all services that depend on those services (2 hops)
3. Return the transitive closure with impact path

Traversal parameters:
- `max_depth`: Maximum hops (default: 3)
- `min_weight`: Minimum edge weight to follow (default: 0.5)
- `direction`: outbound, inbound, or both

## Community Detection

Entities are clustered into communities using modularity-based detection:

- Communities represent topic areas or system boundaries
- Community summaries provide high-level overviews
- Used for scoping queries — "search within the payments community"

Community schema:
```json
{
  "community_id": "comm_001",
  "name": "Payment Processing",
  "entities": ["ent_001", "ent_003", "ent_007"],
  "summary": "Payment processing services including checkout, refund, and reconciliation",
  "size": 3
}
```

## Query Patterns

| Pattern | Description | Example |
|---|---|---|
| Single-hop | Direct relationship lookup | "What does payment-service call?" |
| Multi-hop | Transitive relationship traversal | "What's affected if auth goes down?" |
| Community summary | Overview of a topic area | "Summarize the payment processing domain" |
| Path finding | Shortest path between entities | "How is frontend connected to database?" |
| Impact analysis | All downstream dependents | "What breaks if OBS is unavailable?" |
