# Architecture

## Hook-Based Capture Pipeline

```
Agent Tool Call
    → Hook intercepts (tool_start / tool_end / session_start / session_end / error)
    → Event envelope: {timestamp, agent_id, session_id, tool_name, input_hash, output_hash, duration_ms}
    → Privacy check (regex exclusion patterns)
    → Store in L2 Episodic Buffer (SQLite / Markdown)
    → (After session) Trigger compression
```

## 5-Layer Memory Model

| Layer | Name | Storage | Size | Lifecycle |
|---|---|---|---|---|
| L1 | Working Context | In-context window | ~8K tokens | Cleared per turn |
| L2 | Episodic Buffer | SQLite / Markdown files | ~50K tokens/session | Compressed after session |
| L3 | Skill Tree | Markdown files (git-friendly) | Variable | Crystallized from verified tasks |
| L4 | Semantic Index | CSS/OpenSearch or ChromaDB | Scales with usage | Persistent, relevance-ranked |
| L5 | Configuration | YAML / JSON | <1K tokens | Static, never compressed |

## Compression Engine

- Input: Raw session artifacts from L2
- Process: AI-powered semantic summarization (Haiku-rate model)
- Cost: ~400 input tokens + ~150 output tokens per compression call
- Output: Dense summary preserving key decisions, outcomes, and tool trajectories
- Storage: Compressed summary + embedding stored in L4

## Retrieval Engine

- Trigger: Session start (inject relevant context) or mid-session (on-demand lookup)
- Process: Query embedding → Vector search in L4 → Rank by relevance + recency → Progressive disclosure
- Progressive disclosure: Summary first (T1) → Expand key artifacts (T2) → Full detail on request (T3)
- Injection: Relevant context prepended to agent's working context (L1)

## Storage Backends

| Backend | Use Case | Features |
|---|---|---|
| CSS/OpenSearch | Enterprise production | Hybrid keyword + vector, ACL, managed |
| ChromaDB | Local development | Lightweight, zero-infrastructure, Python-native |
| SQLite FTS5 | Lightweight / edge | Full-text search, no server, single file |

## Cross-Session Context Injection

```
New Session Start
    → Generate session context query from task description
    → Search L4 for relevant past sessions (top-k, relevance + recency weighted)
    → Progressive disclosure: load T1 summaries (<2K tokens)
    → Inject into L1 working context
    → Agent begins with relevant context already loaded
```
