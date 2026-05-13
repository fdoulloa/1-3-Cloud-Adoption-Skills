---
name: project-memory-rag-skill
description: Build project-level knowledge persistence with RAG for enterprise agents that combines learned memory (derived insights that are not re-computed) with document RAG (raw knowledge), supports GraphRAG for connected facts and relationship traversal, MCP integration for tool-accessible memory, skill-based procedural memory (how-to not just what-happened), hybrid retrieval across learned and document stores, Huawei Cloud CSS/OpenSearch and OBS deployment, privacy controls, and audit trails. Use when Codex must design, provision, or generate a project memory RAG system with learned memory storage, document RAG pipeline, GraphRAG for entity relationships, MCP tool registry for memory access, skill procedural memory, hybrid search, or enterprise knowledge persistence.
---

# Project Memory RAG

Use this skill to produce implementation-ready project memory RAG systems, not generic chatbot advice. Keep outputs evidence-grounded, privacy-compliant, and cost-transparent.

## Overview

Project-level knowledge persistence solves two problems: (a) derived insights are re-computed every session (learned memory stores them permanently), and (b) document knowledge requires expensive RAG on every query (combined with learned memory for faster answers). This skill combines learned memory, document RAG, GraphRAG, and MCP integration into a unified project knowledge system.

Inspired by:
- **hermes-agent** — Skills as procedural memory (how-to, not just what-happened), self-improving loop
- **"Learned Memory > RAG"** — Store derived insights so they aren't re-computed; standard RAG is stateless
- **MCP + RAG + Skills stack** — Complete agent memory system: skills for workflows, MCP for tools, RAG for knowledge
- **RAGFlow** — Memory preserves dynamically generated interaction logs and derived data

Core value: queries hit learned memory first (fast, pre-computed), fall back to document RAG only when needed, and use GraphRAG for multi-hop reasoning.

## Default Workflow

1. Configure document RAG pipeline (OBS for documents + RAGFlow for parsing + CSS/OpenSearch for chunk retrieval).
2. Configure learned memory store (CSS/OpenSearch index for derived insights + procedural skills).
3. Set up GraphRAG for entity relationships (entity extraction + relationship mapping + community detection).
4. Register MCP tools for memory access (memory.search_learned, memory.search_documents, memory.search_graph, memory.store_insight, memory.store_skill).
5. Ingest documents into RAG pipeline (OBS → RAGFlow → CSS/OpenSearch chunks).
6. Agent derives insights during task execution → store in learned memory.
7. Future queries: check learned memory first (fast path), fall back to document RAG (authoritative), then GraphRAG (connected).
8. Audit all memory operations with source attribution.

## Architecture Defaults

Dual-store architecture with GraphRAG and MCP:

```
Documents → OBS → RAGFlow (parsing, OCR, chunking) → CSS/OpenSearch (document chunks)

Agent Insights → Learned Memory Store (CSS/OpenSearch, derived insights + skills)

Entities/Relationships → GraphRAG (entity extraction, relationship mapping, community detection)

MCP Tools → memory.search_learned | memory.search_documents | memory.search_graph | memory.store_insight | memory.store_skill

Hybrid Retrieval:
    Query → Learned Memory (fast, pre-computed) → Document RAG (authoritative, raw) → GraphRAG (connected, multi-hop)
```

Default Huawei Cloud region is `la-north-2`. Never hardcode cloud credentials. Use environment variables such as `HWC_REGION`, `HWC_ACCESS_KEY_ID`, and `HWC_SECRET_ACCESS_KEY`.

## Guardrails

- Learned memory must be marked as derived (not source of truth) — document RAG is authoritative.
- Document RAG overrides learned memory on conflict — raw documents are the ground truth.
- GraphRAG relationships must be validated before storage — no hallucinated edges.
- MCP tools respect privacy exclusions — sensitive content never exposed via tools.
- Procedural skills must be versioned and auditable — track skill evolution.
- Memory isolation per project — no cross-project data leakage.
- No PII in learned memory without explicit consent.
- All memory operations audited with source attribution.

## Resources

- `scripts/scaffold_pack.py`: copy the starter Project Memory RAG Pack into a target folder.
- `scripts/deploy_rag_pipeline.sh`: provision Huawei Cloud OBS + CSS/OpenSearch + RAGFlow + MCP registry.
- `scripts/validate_rag.py`: validate document RAG, learned memory, GraphRAG, MCP tools, and hybrid retrieval.
- `assets/project-memory-rag-pack/`: starter pack templates (schemas, config, MCP registry).
- `references/architecture.md`: dual-store architecture, GraphRAG layer, MCP integration, hybrid retrieval flow.
- `references/learned-memory-vs-rag.md`: why learned > RAG for derived insights, conflict resolution, staleness.
- `references/graphrag-design.md`: entity extraction, relationship mapping, traversal, community detection.
- `references/mcp-integration.md`: MCP tool registry, authentication, privacy controls.
- `references/prompts.md`: storage, query, traversal, ranking, insight extraction, skill template prompts.
- `references/huawei-cloud-deployment.md`: deployment defaults, SDK notes, resource provisioning, verification commands.
- `references/token-cost-model.md`: per-operation costs, learned vs. document cost comparison, ROI model.

## Core Rules

1. Learned memory is checked first (fast path) — pre-computed insights before expensive RAG.
2. Document RAG is authoritative — overrides learned memory on factual conflict.
3. GraphRAG is used for multi-hop queries only — not for simple single-entity lookups.
4. MCP tools are the only agent interface to memory — no direct store access.
5. Procedural skills are versioned and never auto-updated — human approval for skill changes.
6. All memory operations are audited — every read, write, and search logged with source attribution.
7. Hybrid retrieval returns source attribution — agent knows if answer came from learned memory, documents, or graph.
8. Staleness detection on learned memory — flag insights older than configurable threshold for re-verification.

## Validation Gates

1. Learned memory returns relevant insights for known queries.
2. Document RAG returns authoritative chunks with citations.
3. GraphRAG traverses relationships correctly for multi-hop queries.
4. MCP tools are accessible and authorized from agent.
5. Hybrid retrieval returns correct source attribution (learned / document / graph).
6. Privacy exclusions enforced across all stores.
7. Conflict resolution: document RAG overrides learned memory on factual conflict.
8. Staleness detection flags old learned memory entries.

## Common Pitfalls

- Treating learned memory as authoritative — it is derived, not source of truth.
- Not falling back to document RAG when learned memory is stale — outdated insights.
- GraphRAG without relationship validation — hallucinated entity connections.
- Exposing raw memory access without MCP tool abstraction — security risk.
- Not versioning procedural skills — untraceable skill evolution.
- Missing privacy exclusions in learned memory store — PII in derived insights.
- Skipping source attribution in hybrid retrieval — agent can't trust the answer source.
- Over-indexing in GraphRAG — expensive and slow for simple queries that learned memory handles.

## KPIs

- **Learned memory hit rate**: % of queries answered without document RAG (target: >60%).
- **Document RAG fallback rate**: % of queries requiring document RAG (target: <30%).
- **GraphRAG multi-hop accuracy**: correctness of multi-hop answers (target: >85%).
- **MCP tool invocation success rate**: % of tool calls succeeding (target: >99%).
- **Procedural skill reuse rate**: % of skills reused across sessions (target: >40%).
- **End-to-end query latency**: learned memory vs. full document RAG (target: 10x faster for learned).
- **Token savings from learned memory fast path**: tokens saved vs. full RAG on every query.
- **Staleness detection rate**: % of learned memory flagged as potentially stale.
