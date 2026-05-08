# Simple ChatBI Skill

Foundational conversational BI skill for Huawei Cloud. Business users ask questions in natural language, an LLM generates SQL, executes against DWS/GaussDB, and returns results with auto-selected visualizations.

## Included Assets

- [SKILL.md](./SKILL.md): Main skill definition, workflow, architecture, and validation gates
- [references/](./references): Text-to-SQL patterns, SQL safety, visualization selection, follow-ups, synthetic data
- [scripts/](./scripts): Demo data generator and end-to-end test script
- [agents/](./agents): Agent metadata for skill invocation

## Typical Use

- Build conversational BI for business users who don't write SQL
- Create demo-ready ChatBI dashboards for customer presentations
- Replace manual report generation with natural language queries
- Generate realistic synthetic datasets for BI demos
- Implement SQL safety validation for production deployments

## Architecture Pattern

```
User question → LLM text-to-SQL → SQL validation → DWS execution → Auto visualization → Follow-ups
```

## Required Huawei Cloud Products

- **DWS (GaussDB)**: Data warehouse for SQL execution
- **MaaS**: Model-as-a-Service for LLM inference (or Dify/DeepSeek fallback)
- **OBS**: Storage for synthetic datasets (optional)
