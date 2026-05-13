# Memory Layers

## L1 — Working Context

- **Storage**: In-context window (LLM context)
- **Size**: ~8K tokens (varies by model)
- **Lifecycle**: Cleared each turn, refreshed by agent loop
- **Content**: Current task, recent tool results, active instructions
- **Operations**: Read/write by agent loop only
- **Compression**: Never — this is the active working memory

## L2 — Episodic Buffer

- **Storage**: SQLite database or Markdown files per session
- **Size**: ~50K tokens per session (raw tool calls, outputs, decisions)
- **Lifecycle**: Written during session, compressed after session end
- **Content**: Tool call logs, decision records, output snapshots, error traces
- **Operations**: Append during session, read by compression engine after session
- **Compression**: Always — raw L2 data is compressed into L4 summaries after session
- **Backup**: OBS bucket for long-term episodic storage (optional)

## L3 — Skill Tree

- **Storage**: Markdown files in `.skills/` directory (git-friendly, human-readable)
- **Size**: Variable per skill (typically 500-2000 tokens per skill)
- **Lifecycle**: Crystallized from verified task completions, versioned
- **Content**: Procedural knowledge — how to do things, not just what happened
- **Operations**: Write on task crystallization, read on skill retrieval, update on skill improvement
- **Compression**: Never — skills are already dense and reusable
- **Self-evolving**: GenericAgent-inspired — skills grow from task trajectories

## L4 — Semantic Index

- **Storage**: CSS/OpenSearch (enterprise) or ChromaDB (dev) — vector embeddings
- **Size**: Scales with usage — one embedding per compressed summary
- **Lifecycle**: Persistent — entries never deleted (only deprecated)
- **Content**: Compressed session summaries, skill embeddings, project knowledge embeddings
- **Operations**: Write after compression, read on retrieval, search by embedding similarity
- **Compression**: Already compressed — L4 stores the output of L2 compression
- **Retrieval**: Top-k vector search with relevance + recency ranking

## L5 — Configuration

- **Storage**: YAML or JSON files in project root
- **Size**: <1K tokens (static settings)
- **Lifecycle**: Manual updates only, never auto-modified
- **Content**: Project settings, privacy exclusion rules, token budgets, storage backend config
- **Operations**: Read at session start, write by human config change only
- **Compression**: Never — config must always be loaded in full

## Inter-Layer Promotion Rules

- L2 → L4: After session end, compress L2 episodic data and store summary + embedding in L4
- L2 → L3: When a task trajectory is verified (successful completion), crystallize into L3 skill
- L4 → L1: At session start, retrieve relevant L4 entries and inject into L1 working context
- L3 → L1: When a skill matches the current task, load skill into L1 for procedural guidance
- L5 → L1: Always load L5 config into L1 at session start
