# Enterprise Agent Memory Skill

Cross-session persistent memory for enterprise agents with hook-based capture, AI-powered compression, tiered vector retrieval, privacy controls, and audit trails.

## Inspiration

- **claude-mem** — Hook-based capture + AI compression + ChromaDB + progressive disclosure
- **hermes-agent** — FTS5 SQLite + Markdown memory + self-improving loop
- **GenericAgent** — 5-layer memory (L1-L5) + self-evolving skill tree

## Enterprise Value

| Pain Point | Skill Value |
|---|---|
| Every conversation requires re-explaining context | Project-level long-term memory with cross-session retrieval |
| Long context is expensive | Auto-summarization and tiered recall reduce token consumption |
| Agent actions are untraceable | Record tool calls, decisions, outputs with immutable audit trail |
| Enterprises worry about privacy | Private storage, sensitive content exclusion, tenant isolation |

## Quick Start

1. Run `scripts/scaffold_pack.py <target>` to create a starter project.
2. Configure privacy exclusions in `memory_schema.json`.
3. Run `scripts/deploy_memory_store.sh --region la-north-2` to provision Huawei Cloud resources.
4. Run `scripts/validate_memory.py --config <config>` to verify all gates pass.
