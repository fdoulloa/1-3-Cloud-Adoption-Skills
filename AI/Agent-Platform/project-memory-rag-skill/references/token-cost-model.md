# Token Cost Model

## Per-Operation Token Consumption

| Operation | Input Tokens | Output Tokens | Total | Notes |
|---|---|---|---|---|
| Learned memory lookup | ~50 | 0 | ~50 | Query embedding + vector search |
| Learned memory store | ~200 | 0 | ~200 | Insight embedding + index write |
| Document RAG query | ~100 | 0 | ~100 | Query embedding + chunk retrieval |
| Document RAG ingest | ~500/chunk | 0 | ~500/chunk | Chunk embedding + index write |
| GraphRAG traversal | ~100 | ~200 | ~300 | Per hop: entity lookup + relationship expansion |
| GraphRAG entity extraction | ~300 | ~150 | ~450 | Per document/chunk |
| MCP tool call overhead | ~20 | 0 | ~20 | Tool routing + auth check |
| Skill crystallization | ~400 | ~200 | ~600 | Per skill created |
| Staleness check | ~50 | 0 | ~50 | Timestamp comparison |

## Cost Comparison: Learned Memory vs. Document RAG

| Query Type | Learned Memory | Document RAG | Savings |
|---|---|---|---|
| Simple fact lookup | ~50 tokens | ~100 tokens | 50% |
| Derived insight | ~50 tokens (pre-computed) | ~100 + ~2000 (re-derive) | 97% |
| Multi-hop question | ~300 tokens (graph) | ~100 × N_hops (iterative RAG) | 70-90% |
| Procedure/skill | ~50 tokens (skill retrieval) | ~2000 (read docs + derive) | 97% |

## Session Cost Model

For a session with Q queries, I insights stored, S skills crystallized:

```
Session cost = Q_learned × 50 + Q_document × 100 + Q_graph × 300
            + I × 200 + S × 600
            + Q × 20 (MCP overhead)
```

Example session (10 queries: 6 learned, 3 document, 1 graph, 2 insights, 1 skill):
- Learned queries: 6 × 50 = 300
- Document queries: 3 × 100 = 300
- Graph query: 1 × 300 = 300
- Insight storage: 2 × 200 = 400
- Skill crystallization: 1 × 600 = 600
- MCP overhead: 10 × 20 = 200
- **Total: 2,100 tokens**

Without learned memory (all queries hit document RAG):
- Document queries: 10 × 100 = 1,000
- Re-derivation: 6 × 2,000 = 12,000 (insights that could have been pre-computed)
- **Total: 13,000 tokens**

**Savings: 84% reduction** when learned memory is populated.

## ROI Calculation

Learned memory becomes cost-positive after the second use of an insight:
- First use: derive (2,000 tokens) + store (200 tokens) = 2,200 tokens
- Second use: retrieve (50 tokens) = 50 tokens
- Break-even: 2,200 / (2,000 - 50) ≈ 1.13 uses

Every insight used more than once generates net token savings.
