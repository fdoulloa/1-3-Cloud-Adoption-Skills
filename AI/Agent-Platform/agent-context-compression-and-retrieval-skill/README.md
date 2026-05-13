# Agent Context Compression and Retrieval Skill

Automatic context compression with tiered recall, recall probes, artifact probes, and token cost visibility for enterprise agents.

## Inspiration

- **claude-mem** — AI-powered compression + progressive disclosure
- **Anthropic compaction** — High-fidelity context distillation
- **GenericAgent** — Information density optimization (~30K tokens/task)
- **Factory.ai** — Recall probes and artifact probes

## Enterprise Value

| Pain Point | Skill Value |
|---|---|
| Long context is expensive | Auto-compression reduces token consumption 60-90% |
| Critical facts lost in compression | Recall probes verify preservation |
| Key decisions buried in context | Artifact probes extract decisions for long-term storage |
| Context window overflow | Tiered recall loads only what's needed |

## Quick Start

1. Run `scripts/scaffold_pack.py <target>` to create a starter project.
2. Configure compression strategy in `compression_config.json`.
3. Run `scripts/deploy_compression_service.sh --region la-north-2` to provision Huawei Cloud resources.
4. Run `scripts/validate_compression.py --config <config>` to verify all gates pass.
