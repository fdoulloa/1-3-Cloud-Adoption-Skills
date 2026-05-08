---
name: simple-chatbi-skill
description: Use this skill when building a conversational BI experience where business users ask questions in natural language and get SQL-generated answers with auto-selected visualizations. It covers text-to-SQL prompt design with schema context, multi-provider LLM fallback chains, SQL safety validation, auto-retry on query errors, follow-up question suggestions, and Streamlit dashboard patterns. This is the foundational version — use it for standard ChatBI deployments.
---

# Simple ChatBI Skill

## Overview

This skill drives conversational BI on Huawei Cloud: business users ask questions in natural language, an LLM converts them to SQL, executes against DWS/GaussDB, and returns results with auto-selected visualizations. It includes a three-provider fallback chain (Dify → MaaS → DeepSeek), SQL safety validation, automatic error retry, and follow-up question suggestions.

This is the foundational version designed for standard deployments. It covers 80% of ChatBI use cases without requiring advanced features like multi-turn context, semantic layers, or fine-tuned models.

## Use This Skill When

- Business users need to query data without writing SQL.
- The customer has a DWS/GaussDB database and wants a conversational interface.
- You need a demo-ready ChatBI that works in under 30 minutes of setup.
- The existing BI tools (PowerBI, Tableau) are too slow for ad-hoc questions.
- You want to replace manual report generation with natural language queries.

## Default Workflow

Follow this sequence by default:

1. **Define the schema context:**
   - List all tables, columns, and types the LLM needs to know.
   - Include business rules (risk levels, score ranges, monetary units).
   - Read [references/text-to-sql-patterns.md](references/text-to-sql-patterns.md).

2. **Design the LLM prompt:**
   - Embed schema in system prompt with strict rules.
   - Enforce SELECT-only output with safety validation.
   - Read [references/sql-safety-validation.md](references/sql-safety-validation.md).

3. **Implement the fallback chain:**
   - Primary: Dify (if available on Huawei Cloud)
   - Secondary: MaaS (ModelArts Model-as-a-Service)
   - Tertiary: DeepSeek direct API
   - Read [references/text-to-sql-patterns.md](references/text-to-sql-patterns.md).

4. **Add auto-retry logic:**
   - If SQL execution fails, re-prompt LLM with the error message.
   - Maximum 2 retries before showing error to user.
   - Read [references/text-to-sql-patterns.md](references/text-to-sql-patterns.md).

5. **Design the visualization layer:**
   - Auto-select chart type based on data shape.
   - Read [references/visualization-selection.md](references/visualization-selection.md).

6. **Add follow-up suggestions:**
   - After each query, suggest 3 relevant follow-up questions.
   - Read [references/followup-suggestions.md](references/followup-suggestions.md).

7. **Generate synthetic data for demos:**
   - Use `scripts/generate-chatbi-demo-data.py` with `--country` flag for LATAM multi-country support.
   - Supported: mexico, colombia, argentina, chile, peru, brazil.
   - Read [references/synthetic-data-patterns.md](references/synthetic-data-patterns.md).

8. **Validate end-to-end:**
   - Run `scripts/test-chatbi.sh` with sample questions.

## Architecture

```
User question (natural language)
  → LLM text-to-SQL (Dify → MaaS → DeepSeek fallback)
  → SQL validation (SELECT-only, LIMIT enforced)
  → DWS/GaussDB execution
  → Auto-retry on error (re-prompt with error context)
  → Result formatting (currency, dates, scores)
  → Auto visualization selection (pie/bar/line/scatter)
  → Follow-up suggestions
```

## Core Rules

- Schema context is everything. The LLM generates better SQL when it has complete table and column information.
- Always validate SQL before execution. Block anything that isn't SELECT or WITH.
- Always enforce LIMIT. Never let the LLM return unbounded results.
- Auto-retry is critical. LLMs often generate slightly wrong SQL on first try. Re-prompting with the error fixes 70% of failures on the second attempt.
- The fallback chain must be transparent. Show the user which provider generated the SQL.
- Synthetic data must look real. Use country-specific business context (local currency, tax IDs, regions, realistic company names). Support Mexico, Colombia, Argentina, Chile, Peru, and Brazil.
- Never expose database credentials in the frontend. All SQL execution happens server-side.

## Default Deliverables

1. **ChatBI module:** Streamlit or web component with chat interface, history, and example questions.
2. **Text-to-SQL engine:** LLM prompt + validation + retry logic.
3. **Visualization layer:** Auto-chart selection based on data shape.
4. **Synthetic data generator:** Realistic demo datasets for any domain.
5. **Test script:** End-to-end validation with sample questions.

## Maturity Level

**Level 1 — Proven in demo.** Pipeline validated with real databases, LLM text-to-SQL confirmed working, visualization auto-selection functional. Suitable for demos and PoCs.

## KPIs / Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| SQL generation accuracy | > 85% | LLM generates correct SQL on first try |
| Auto-retry success rate | > 70% | Failed SQL corrected on second attempt |
| End-to-end latency | < 8s | Question to visual result |
| Visualization relevance | > 90% | Chart type matches data shape |
| Follow-up relevance | > 80% | Suggested questions are useful |

## Common Risks and Troubleshooting

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM generates INSERT/UPDATE | Data corruption or crash | Validate SQL with regex before execution; block non-SELECT |
| LLM references wrong table/column | SQL error, bad experience | Include complete schema in system prompt; use exact names |
| No LIMIT clause | Memory exhaustion, slow response | Auto-append LIMIT 200 if missing |
| Provider downtime | No SQL generated | Fallback chain: Dify → MaaS → DeepSeek |
| Schema changes | LLM generates stale SQL | Re-generate schema context when tables change |
