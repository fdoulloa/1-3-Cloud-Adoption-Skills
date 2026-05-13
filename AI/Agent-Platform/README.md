# Agent Platform

This use case covers multi-agent orchestration, tool calling, and workflow automation for complex business tasks. It supports the design of agent-based systems that can reason, act, and integrate with enterprise tools.

## Typical Skill Areas

- Multi-agent task orchestration
- Tool calling patterns
- Workflow automation design
- Industry assistant design
- Agent operating guardrails
- Agent memory and context persistence

## Expected Outputs

- Agent platform architecture
- Tool and workflow design
- Task orchestration pattern
- Validation scenarios and guardrails
- Agent memory architecture with token cost model
- Context compression and tiered recall design

## Implemented Skills

- [Enterprise Agent Memory](./enterprise-agent-memory-skill/SKILL.md) — Cross-session persistent memory with hook-based capture, AI compression, tiered retrieval, privacy controls, and audit trails. Inspired by claude-mem, hermes-agent, GenericAgent.
- [Agent Context Compression and Retrieval](./agent-context-compression-and-retrieval-skill/SKILL.md) — Automatic context compression with tiered recall, recall probes, artifact probes, and token cost visibility. Inspired by claude-mem, Anthropic compaction, Factory.ai.
- [Project Memory RAG](./project-memory-rag-skill/SKILL.md) — Project-level knowledge persistence combining learned memory with document RAG, GraphRAG, MCP integration, and skill-based procedural memory. Inspired by hermes-agent, learned-memory-over-RAG, RAGFlow.
