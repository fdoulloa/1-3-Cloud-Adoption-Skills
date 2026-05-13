# MCP Integration

## MCP Tool Registry

The Model Context Protocol (MCP) provides the agent-facing interface for all memory operations. Agents never access stores directly — they use MCP tools.

### Tool Definitions

#### memory.search_learned
Search the learned memory store for derived insights.

```json
{
  "name": "memory.search_learned",
  "description": "Search learned memory for derived insights, patterns, and procedures",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
      "max_results": {"type": "integer", "default": 5},
      "min_confidence": {"type": "number", "default": 0.7}
    },
    "required": ["query"]
  }
}
```

#### memory.search_documents
Search the document RAG store for authoritative information.

```json
{
  "name": "memory.search_documents",
  "description": "Search document RAG for authoritative information with citations",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "document_types": {"type": "array", "items": {"type": "string"}},
      "max_results": {"type": "integer", "default": 5}
    },
    "required": ["query"]
  }
}
```

#### memory.search_graph
Search the GraphRAG store for entity relationships and multi-hop answers.

```json
{
  "name": "memory.search_graph",
  "description": "Search GraphRAG for entity relationships and multi-hop reasoning",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "entity": {"type": "string", "description": "Starting entity name"},
      "max_depth": {"type": "integer", "default": 3},
      "direction": {"type": "string", "enum": ["outbound", "inbound", "both"], "default": "both"}
    },
    "required": ["query"]
  }
}
```

#### memory.store_insight
Store a derived insight in learned memory.

```json
{
  "name": "memory.store_insight",
  "description": "Store a derived insight in learned memory for future retrieval",
  "inputSchema": {
    "type": "object",
    "properties": {
      "insight": {"type": "string", "description": "The derived insight content"},
      "derived_from": {"type": "array", "items": {"type": "string"}, "description": "Source document/chunk IDs"},
      "tags": {"type": "array", "items": {"type": "string"}},
      "confidence": {"type": "number", "default": 0.8}
    },
    "required": ["insight", "derived_from"]
  }
}
```

#### memory.store_skill
Store a procedural skill in learned memory.

```json
{
  "name": "memory.store_skill",
  "description": "Store a procedural skill (how-to) in learned memory",
  "inputSchema": {
    "type": "object",
    "properties": {
      "skill_name": {"type": "string"},
      "procedure": {"type": "string", "description": "Step-by-step procedure"},
      "trigger_conditions": {"type": "string", "description": "When to apply this skill"},
      "version": {"type": "integer", "default": 1}
    },
    "required": ["skill_name", "procedure", "trigger_conditions"]
  }
}
```

## Authentication and Authorization

- MCP tools authenticate via project-scoped API keys
- Each tool has permission level: read (search_*) or write (store_*)
- Write operations require elevated permissions (configurable per project)
- Tool calls are audited with caller identity and timestamp

## Privacy Controls

- `memory.search_learned` applies privacy exclusions before returning results
- `memory.search_documents` applies ACL filters based on caller permissions
- `memory.store_insight` checks for PII before storage
- `memory.store_skill` requires human approval for skill version updates
- All tools respect tenant isolation — cross-tenant access is blocked
