---
name: agent-context-compression-and-retrieval-skill
description: Build automatic context compression and tiered recall for enterprise agents that reduces token consumption while preserving critical facts, supports recall probes for compression quality verification, artifact probes for key information extraction, just-in-time retrieval that loads context only when needed, high-fidelity compaction that distills context windows, progressive disclosure from summary to detail, token cost visibility per compression operation, and Huawei Cloud deployment. Use when Codex must design, provision, or generate an agent context compression system with AI-powered summarization, tiered recall layers, compaction strategies, recall verification probes, artifact extraction probes, or token-optimized context management.
---

# Agent Context Compression and Retrieval

Use this skill to produce implementation-ready context compression systems, not generic chatbot advice. Keep outputs token-efficient, probe-verified, and cost-transparent.

## Overview

Long context is expensive — every token in the context window costs money and latency. This skill provides automatic compression, tiered recall, and just-in-time retrieval that reduces token consumption while preserving critical facts.

Inspired by:
- **claude-mem** — AI-powered compression (~400 input + 150 output tokens/call), progressive disclosure
- **Anthropic compaction** — High-fidelity distillation of context window contents
- **GenericAgent** — Contextual information density optimization, ~30K tokens/task
- **Factory.ai** — Recall probes and artifact probes for compression quality verification

Core value: agents run longer and cheaper by compressing context at thresholds and retrieving only what's needed.

## Default Workflow

1. Configure compression strategy (compaction, summarization, extraction, or hybrid).
2. Set token budget per context tier (T1, T2, T3).
3. Agent runs with full context until compression threshold is reached.
4. Compression engine processes context window at threshold (default: 70% utilization).
5. Compressed context replaces original in window.
6. Recall probes verify critical facts are preserved after compression.
7. Artifact probes extract key decisions and outcomes for long-term storage.

## Architecture Defaults

3-tier recall architecture:

```
T1 Compressed Summary    → Always loaded, <2K tokens, high-level context
T2 Key Artifacts         → Loaded on relevance match, <8K tokens, decisions/outcomes
T3 Raw Detail            → Loaded on explicit request, original size, full context
```

Compression pipeline:

```
Context Window
    → Detect utilization threshold (70%)
    → Select compression strategy
    → Compress (compaction / summarization / extraction)
    → Verify with recall probes
    → Replace original context with compressed version
    → Store T2 artifacts for future retrieval
```

Progressive disclosure flow:

```
Session Start → Load T1 summary (<2K tokens, always)
Task Relevance Match → Load T2 artifacts (<8K tokens, on-demand)
Explicit Request → Load T3 raw detail (full context, only when needed)
```

Default Huawei Cloud region is `la-north-2`. Never hardcode cloud credentials. Use environment variables such as `HWC_REGION`, `HWC_ACCESS_KEY_ID`, and `HWC_SECRET_ACCESS_KEY`.

## Guardrails

- Compression must never lose critical facts — verified by recall probes after every compression.
- Token budget is a hard limit, not a soft suggestion — refuse operations that exceed budget.
- Compaction preserves causal relationships — if A caused B, both must survive compression.
- Progressive disclosure never loads T3 without explicit signal from the agent.
- Compression cost must be less than the tokens saved — otherwise skip compression.
- Audit every compression operation with before/after token counts.
- T1 summary must be self-contained — understandable without T2 or T3.
- Privacy exclusions applied before compression — sensitive content (PII, credentials) excluded from all tiers.

## Resources

- `scripts/scaffold_pack.py`: copy the starter Context Compression Pack into a target folder.
- `scripts/deploy_compression_service.sh`: provision Huawei Cloud CSS/OpenSearch + ECS for compression infrastructure.
- `scripts/validate_compression.py`: validate compression engine, recall probes, artifact probes, and tier storage.
- `assets/context-compression-pack/`: starter pack templates (prompts, config).
- `references/architecture.md`: 3-tier recall, compression pipeline, progressive disclosure.
- `references/compression-strategies.md`: compaction, summarization, extraction, hybrid strategies.
- `references/tiered-recall.md`: T1/T2/T3 specifications, relevance scoring, cache invalidation.
- `references/prompts.md`: compaction, summarization, extraction, recall probe, artifact probe prompts.
- `references/huawei-cloud-deployment.md`: deployment defaults, SDK notes, resource provisioning, verification commands.
- `references/token-cost-model.md`: per-strategy token costs, probe costs, ROI model.

## Core Rules

1. Compress at 70% context utilization threshold — not earlier (waste) or later (overflow risk).
2. Always verify compression with recall probes — never trust compression blindly.
3. T1 compressed summary must fit in <2K tokens — enforce strict budget.
4. T2 key artifacts must fit in <8K tokens — select only the most important.
5. T3 raw detail is never loaded proactively — only on explicit agent request.
6. Compression cost must be <20% of tokens saved — otherwise compression is not worthwhile.
7. Progressive disclosure loads T1 first, T2 on relevance, T3 on demand — never skip tiers.
8. Artifact probes extract decisions, outcomes, and file paths — not intermediate steps.

## Validation Gates

1. Compression reduces token count by target percentage (60-90% depending on strategy).
2. Recall probes confirm critical facts preserved after compression.
3. Artifact probes extract key decisions and outcomes.
4. Progressive disclosure loads correct tier based on request level.
5. Token budget not exceeded for any tier.
6. Compression cost is less than savings (positive ROI per compression).
7. T1 summary is self-contained and understandable without T2/T3.

## Common Pitfalls

- Compressing too early — before enough context accumulates for meaningful compression.
- Compressing too late — context overflow before compression triggers.
- Not verifying compression quality — silent information loss that corrupts agent behavior.
- Loading T3 raw context proactively — defeats the purpose of tiered recall.
- Ignoring compression cost in token budget — compression itself consumes tokens.
- Not tracking before/after token counts — no way to measure compression ROI.
- Using summarization when compaction is needed — summarization loses detail that compaction preserves.
- Not running artifact probes — key decisions lost when context is compressed away.

## KPIs

- **Token reduction ratio**: compressed tokens / original tokens (target: 0.1-0.4 depending on strategy).
- **Recall probe pass rate**: % of critical facts preserved after compression (target: >95%).
- **Artifact extraction completeness**: % of key decisions captured by artifact probes.
- **Compression latency**: time to compress + verify (target: <2s for typical context).
- **Token cost savings per session**: tokens saved minus compression cost.
- **Progressive disclosure hit rate**: % of queries where T1 is sufficient (no T2/T3 needed).
