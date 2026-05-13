# Architecture

## 3-Tier Recall Architecture

```
┌─────────────────────────────────────────────────┐
│ T1 — Compressed Summary (<2K tokens)            │
│ Always loaded at session start                   │
│ High-level context: project, recent work, goals  │
├─────────────────────────────────────────────────┤
│ T2 — Key Artifacts (<8K tokens)                 │
│ Loaded on relevance match                        │
│ Decisions, outcomes, file changes, errors        │
├─────────────────────────────────────────────────┤
│ T3 — Raw Detail (original size)                 │
│ Loaded only on explicit request                  │
│ Full context: all tool calls, outputs, reasoning │
└─────────────────────────────────────────────────┘
```

## Compression Pipeline

```
Context Window (approaching threshold)
    → Monitor utilization (default: 70%)
    → Select strategy:
        - Compaction: high-fidelity distillation (~60% reduction)
        - Summarization: AI-powered summary (~75% reduction)
        - Extraction: key facts only (~90% reduction)
        - Hybrid: compaction for recent + summarization for older
    → Execute compression
    → Run recall probes (verify critical facts preserved)
    → Run artifact probes (extract key decisions/outcomes)
    → Replace context window with compressed version
    → Store T2 artifacts in CSS/OpenSearch for future retrieval
    → Store T3 raw in OBS for on-demand access
```

## Progressive Disclosure Flow

```
Session Start
    → Load T1 summary from CSS/OpenSearch (<2K tokens)
    → Agent begins with high-level context

Task Execution
    → Relevance match triggers T2 artifact loading
    → Key decisions and outcomes injected (<8K tokens)
    → Agent has task-relevant context

Explicit Request
    → Agent signals need for full detail
    → Load T3 raw from OBS (original size)
    → Agent has complete context for the specific item
```

## Integration with Enterprise Agent Memory

This skill works with `enterprise-agent-memory-skill`:
- Compression engine compresses L2 episodic data before storing in L4
- T1/T2/T3 tiers map to progressive disclosure levels in the memory skill
- Recall probes validate compression quality before L4 storage
- Artifact probes extract what to store in L3 skill tree
