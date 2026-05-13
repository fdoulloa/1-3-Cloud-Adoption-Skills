# Learned Memory vs. RAG

## Why Learned Memory > RAG for Derived Insights

Standard RAG agents are **stateless** — they re-derive the same insights from raw documents every session. This wastes tokens and time.

Learned memory stores **derived insights** — conclusions, patterns, and procedures that the agent has already computed. Future sessions retrieve these directly instead of re-deriving them.

### Example

**Without learned memory (pure RAG):**
- Session 1: Agent reads 5 documents, derives "Use circuit-breaker pattern for all external API calls" → outputs answer
- Session 2: Agent reads same 5 documents, re-derives same insight → outputs same answer
- Cost: 2 × (RAG retrieval + LLM reasoning) = 2x

**With learned memory:**
- Session 1: Agent reads 5 documents, derives insight → stores in learned memory
- Session 2: Agent checks learned memory → finds insight → returns directly
- Cost: 1 × (RAG + reasoning) + 1 × (learned memory lookup) = ~1.1x

### When to Use Each

| Scenario | Use Learned Memory | Use Document RAG |
|---|---|---|
| Derived insight (conclusion from analysis) | Yes | No |
| Raw fact from document | No | Yes |
| Procedure/workflow (how-to) | Yes (as skill) | No |
| Policy or regulation text | No | Yes (authoritative) |
| Pattern discovered across sessions | Yes | No |
| Document content that may change | No | Yes (fresh) |

## Conflict Resolution

When learned memory and document RAG disagree:

1. **Document RAG always wins** for factual claims — it is the authoritative source.
2. **Learned memory is updated** to match the document — stale insight is replaced.
3. **Conflict is logged** in audit trail — both versions recorded for traceability.
4. **Agent is notified** — "Learned memory was stale, updated from document source."

## Staleness Detection

Learned memory entries include a `derived_at` timestamp. Staleness rules:

| Entry Age | Action |
|---|---|
| <7 days | Fresh — use directly |
| 7-30 days | Check document source for changes |
| >30 days | Flag as potentially stale, verify before use |
| Source document modified | Invalidate and re-derive |

## Examples

### Learned Memory Entry
```json
{
  "type": "insight",
  "content": "All payment endpoints require circuit-breaker pattern with 5s timeout",
  "derived_from": ["doc://payment-api-spec.pdf", "doc://incident-log-2026.q1.pdf"],
  "derived_at": "2026-05-10T14:30:00Z",
  "confidence": 0.92,
  "tags": ["architecture", "payment", "resilience"]
}
```

### Document RAG Chunk
```json
{
  "type": "document_chunk",
  "content": "Section 3.2: All external API integrations must implement circuit-breaker...",
  "source": "doc://payment-api-spec.pdf",
  "page": 12,
  "chunk_id": "chunk_042"
}
```
