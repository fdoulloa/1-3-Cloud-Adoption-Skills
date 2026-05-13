# Architecture

## Dual-Store Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Document RAG Store                   │
│  OBS (raw docs) → RAGFlow (parse) → CSS/OpenSearch  │
│  Authoritative source of truth for factual claims    │
├──────────────────────────────────────────────────────┤
│                  Learned Memory Store                 │
│  CSS/OpenSearch (derived insights + skills)          │
│  Fast path: pre-computed results, not re-derived     │
├──────────────────────────────────────────────────────┤
│                  GraphRAG Layer                       │
│  Entity extraction → Relationship mapping            │
│  Community detection → Multi-hop traversal           │
├──────────────────────────────────────────────────────┤
│                  MCP Integration Layer                │
│  Tool registry: search_learned, search_documents,    │
│  search_graph, store_insight, store_skill            │
└──────────────────────────────────────────────────────┘
```

## Hybrid Retrieval Flow

```
Query
    → Check Learned Memory (fast path, ~50ms)
        → If hit: return with source=learned, confidence=high
        → If miss or stale: fall through
    → Check Document RAG (authoritative, ~200ms)
        → If hit: return with source=document, citations
        → If conflict with learned: document wins, update learned
    → Check GraphRAG (multi-hop, ~500ms)
        → If multi-hop query: traverse relationships
        → Return with source=graph, traversal path
    → No results: return empty with source=none
```

## Data Flow

### Document Ingestion
```
Upload → OBS bucket → RAGFlow parsing (OCR, layout, tables)
    → Chunks + metadata + embeddings → CSS/OpenSearch document index
    → Entity extraction → GraphRAG nodes + edges
```

### Insight Derivation
```
Agent task execution → Derives insight
    → Privacy check → Store in Learned Memory (CSS/OpenSearch)
    → Extract entities → Update GraphRAG
    → Audit log: insight stored with source attribution
```

### Skill Crystallization
```
Verified task completion → Extract procedure
    → Version → Store as skill in Learned Memory
    → Audit log: skill created/updated with version
```

## Integration with Enterprise Agent Memory

This skill works with `enterprise-agent-memory-skill`:
- Learned memory store is the L4 semantic index from the memory skill
- Document RAG follows the `enterprise-rag-agent` pattern
- GraphRAG extends the memory skill's L3 skill tree with entity relationships
- MCP tools are the agent-facing interface for all memory operations
