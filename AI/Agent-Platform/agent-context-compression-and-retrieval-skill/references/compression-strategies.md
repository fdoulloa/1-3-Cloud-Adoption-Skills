# Compression Strategies

## Strategy 1: High-Fidelity Compaction

- **Reduction**: ~60% of original token count
- **Method**: Distillation that preserves all facts, relationships, and causal chains
- **Best for**: Recent context that may still be actively referenced
- **Cost**: ~context_size × 0.6 input tokens + 0.4 output tokens
- **Quality**: Highest — recall probes typically pass >98%
- **Inspired by**: Anthropic's compaction mechanism

Prompt approach: "Distill the following context into a compact form that preserves every fact, decision, causal relationship, and file reference. Remove only redundant phrasing and verbose explanations."

## Strategy 2: AI Summarization

- **Reduction**: ~75% of original token count
- **Method**: AI-powered summarization that captures key points and outcomes
- **Best for**: Older context that is unlikely to need full detail
- **Cost**: ~context_size × 0.3 input tokens + 0.15 output tokens
- **Quality**: High — recall probes typically pass >90%
- **Inspired by**: claude-mem compression (~400 input + 150 output tokens/call)

Prompt approach: "Summarize the following context, preserving key decisions, outcomes, errors, and file changes. Remove intermediate steps and verbose tool outputs."

## Strategy 3: Extraction-Only

- **Reduction**: ~90% of original token count
- **Method**: Extract only key facts, decisions, and outcomes — no narrative
- **Best for**: Very old context or context that has been fully processed
- **Cost**: ~context_size × 0.1 input tokens + 0.05 output tokens
- **Quality**: Moderate — recall probes typically pass >80% (some context loss)
- **Inspired by**: Factory.ai artifact probes

Prompt approach: "Extract only the key facts, decisions, outcomes, and file paths from the following context. Format as structured bullet points. Omit all reasoning, intermediate steps, and verbose outputs."

## Strategy Selection Rules

| Context Age | Utilization | Strategy |
|---|---|---|
| <5 minutes | Any | No compression (too recent) |
| 5-30 minutes | >70% | Compaction |
| 30 min - 2 hours | >70% | Summarization |
| >2 hours | >70% | Extraction |
| Any | >90% | Immediate compaction (overflow risk) |

## Hybrid Strategy

For long-running sessions with mixed context ages:
1. Split context into recent (<30 min) and older (>30 min) segments
2. Apply compaction to recent segment
3. Apply summarization to older segment
4. Merge compressed segments
5. Verify with recall probes on merged result

This achieves ~70% reduction while preserving recent context at higher fidelity.
