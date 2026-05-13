# Project Memory RAG Skill

Project-level knowledge persistence combining learned memory (derived insights) with document RAG (raw knowledge), GraphRAG for connected facts, MCP integration, and skill-based procedural memory.

## Inspiration

- **hermes-agent** — Skills as procedural memory + self-improving loop
- **"Learned Memory > RAG"** — Store derived insights, don't re-compute
- **MCP + RAG + Skills stack** — Complete agent memory system
- **RAGFlow** — Memory preserves interaction logs and derived data

## Enterprise Value

| Pain Point | Skill Value |
|---|---|
| Same insights re-derived every session | Learned memory stores them permanently |
| Document RAG is slow and expensive | Learned memory fast path avoids RAG when possible |
| Multi-hop questions need connected facts | GraphRAG traverses entity relationships |
| Agent can't access memory programmatically | MCP tools provide structured memory access |
| How-to knowledge is lost | Skill-based procedural memory preserves workflows |

## Quick Start

1. Run `scripts/scaffold_pack.py <target>` to create a starter project.
2. Configure document sources and learned memory in `learned_memory_schema.json`.
3. Run `scripts/deploy_rag_pipeline.sh --region la-north-2` to provision Huawei Cloud resources.
4. Run `scripts/validate_rag.py --config <config>` to verify all gates pass.
