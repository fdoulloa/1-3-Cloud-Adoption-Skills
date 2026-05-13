---
name: enterprise-agent-memory-skill
description: Build cross-session persistent memory for enterprise agents that auto-captures tool usage, generates semantic summaries, injects relevant context in future sessions, supports tiered retrieval with token cost visibility, skill-based search, privacy controls with sensitive content exclusion, and audit trails. Use when Codex must design, provision, or generate an enterprise agent memory system with hook-based capture, AI-powered compression, ChromaDB or CSS/OpenSearch vector retrieval, progressive disclosure, 5-layer memory architecture (L1 working, L2 episodic, L3 skill tree, L4 semantic index, L5 config), FTS5 SQLite retrieval, Markdown memory files, self-improving memory loops, Huawei Cloud deployment, or privacy-compliant agent memory.
---

# Enterprise Agent Memory

Use this skill to produce implementation-ready agent memory systems, not generic chatbot advice. Keep outputs privacy-compliant, auditable, and token-efficient.

## Overview

Enterprise agents lose context between sessions, forcing users to re-explain background every conversation. This skill provides cross-session persistent memory that auto-captures tool usage, AI-powered semantic compression, and injects relevant context in future sessions.

Inspired by:
- **claude-mem** — Hook-based capture + AI compression (~400 input + 150 output tokens/call) + ChromaDB vector retrieval + progressive disclosure
- **hermes-agent** — FTS5 SQLite retrieval + Markdown memory files + self-improving loop (memory + skills + soul + crons)
- **GenericAgent** — 5-layer memory (L1 working, L2 episodic, L3 skill tree, L4 semantic index, L5 config) + self-evolving skill tree

Core value: every session starts with relevant context already loaded. Token consumption drives the business model — each agent execution produces capture, compression, retrieval, and injection costs.

## Default Workflow

1. Install capture hooks on agent tool calls (lifecycle events: tool_start, tool_end, session_start, session_end, error).
2. Configure memory store backend: CSS/OpenSearch for enterprise, ChromaDB for local dev, SQLite FTS5 for lightweight.
3. Set privacy exclusion rules (API keys, tokens, PII patterns, user-defined sensitive content).
4. Run agent session — hooks auto-capture decisions, tool calls, outputs, and errors.
5. After session: compression engine summarizes session artifacts into dense, retrievable context.
6. Store compressed summaries with vector embeddings in L4 semantic index.
7. Next session: retrieval engine performs semantic search and injects relevant context via progressive disclosure.
8. Audit log records all capture, compress, store, and retrieve events with timestamps and token counts.

## Architecture Defaults

5-layer memory model:

```
L1 Working Context    → In-context, volatile, ~8K tokens, cleared per turn
L2 Episodic Buffer    → Session logs, SQLite/Markdown, ~50K tokens/session, compressed after session
L3 Skill Tree         → Procedural memory, Markdown files, how-to knowledge, crystallized from verified tasks
L4 Semantic Index     → Vector embeddings, CSS/OpenSearch or ChromaDB, relevance-ranked retrieval
L5 Configuration      → Static project settings, YAML/JSON, never compressed, always loaded
```

Capture pipeline: Agent tool call → Hook intercepts → Privacy check → Store in L2 → (after session) Compress → Store in L4.

Retrieval pipeline: Session start → Query L4 with session context → Rank by relevance + recency → Progressive disclosure (summary first, expand on demand) → Inject into L1.

Default Huawei Cloud region is `la-north-2`. Never hardcode cloud credentials. Use environment variables such as `HWC_REGION`, `HWC_ACCESS_KEY_ID`, and `HWC_SECRET_ACCESS_KEY`.

## Guardrails

- Never capture secrets (API keys, tokens, credentials, passwords).
- Exclude user-defined sensitive patterns before storage (regex-based PII detection).
- Privacy-first: default to not storing PII without explicit consent.
- Audit every capture, store, and retrieve event with immutable log.
- Token budget enforcement per session — refuse operations that exceed budget.
- Compression must preserve factual accuracy — no hallucination in summaries.
- Memory isolation per project/tenant — no cross-tenant data leakage.
- Compression uses Haiku-rate models to minimize cost (~550 tokens/call).

## Resources

- `scripts/scaffold_pack.py`: copy the starter Enterprise Agent Memory Pack into a target folder.
- `scripts/deploy_memory_store.sh`: provision Huawei Cloud CSS/OpenSearch + OBS + RDS/GaussDB for memory infrastructure.
- `scripts/validate_memory.py`: validate capture hooks, compression engine, vector store, privacy exclusions, and audit log.
- `assets/enterprise-agent-memory-pack/`: starter pack templates (schema, hooks, prompts).
- `references/architecture.md`: hook pipeline, 5-layer model, compression engine, retrieval engine, progressive disclosure.
- `references/memory-layers.md`: L1-L5 specifications, storage backends, size limits, inter-layer promotion rules.
- `references/privacy-and-audit.md`: sensitive content exclusion, audit event schema, GDPR compliance, tenant isolation.
- `references/prompts.md`: capture, compression, retrieval, expansion, privacy check, audit formatting prompts.
- `references/huawei-cloud-deployment.md`: deployment defaults, SDK notes, resource provisioning, verification commands.
- `references/token-cost-model.md`: per-operation token costs, session cost model, ROI vs. no-memory baseline.

## Core Rules

1. Capture is automatic, opt-out not opt-in — hooks intercept all tool calls by default.
2. Compression happens after session end, not during — avoids mid-session latency.
3. Retrieval is relevance-ranked with recency bias — recent sessions weighted higher.
4. Privacy exclusions are checked before storage — sensitive content never enters the memory store.
5. Audit trail is immutable — append-only log, no deletion, retention per policy.
6. Token cost is tracked per operation — every capture, compress, store, retrieve logged with token count.
7. Progressive disclosure loads summaries first — full detail only on explicit request.
8. L5 config is never compressed — static settings always loaded in full.

## Validation Gates

1. Hook captures tool call events (tool_start, tool_end, session_start, session_end).
2. Compression produces valid summary with <5% information loss (measured by recall probes).
3. Vector store returns relevant results for known queries (top-k precision >0.8).
4. Privacy exclusions block sensitive content (zero secrets in memory store).
5. Audit log is complete and immutable (100% of operations logged).
6. Cross-session retrieval injects correct context (relevant past sessions surfaced).
7. Token budget not exceeded per session.

## Common Pitfalls

- Storing raw tool outputs without compression — token explosion in L2.
- Retrieving too much context at session start — context window overflow before user speaks.
- Missing privacy exclusions for credentials — secrets leak into vector store.
- Not isolating memory between projects — cross-contamination of context.
- Skipping audit logging — untraceable agent actions, compliance failure.
- Compression that hallucinates facts not in source — corrupted memory.
- Loading L3 skill tree proactively — only load skills relevant to current task.
- Ignoring compression token cost in budget — compression itself consumes tokens.

## KPIs

- **Context reuse rate**: % of sessions starting with injected relevant context.
- **Token savings from compression**: raw storage tokens vs. compressed tokens.
- **Retrieval relevance**: top-k precision for past session search.
- **Privacy compliance**: zero sensitive content detected in memory store.
- **Audit completeness**: 100% of capture/store/retrieve operations logged.
- **Cross-session continuity**: reduction in re-explanation time across sessions.
- **Compression cost efficiency**: tokens saved vs. tokens consumed by compression.
