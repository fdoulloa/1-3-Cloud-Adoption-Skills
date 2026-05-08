---
name: contract-risk-analysis-ai-skill
description: Use this skill when building an AI-powered document risk analysis pipeline that combines OCR text extraction, LLM-based risk scoring, and structured result storage. It covers Huawei Cloud OCR integration, serverless FunctionGraph chains, LLM prompt design for risk assessment, fallback patterns when models are unavailable, and DWS/GaussDB result storage with three-layer schema design.
---

# Contract Risk Analysis AI Skill

## Overview

This skill drives end-to-end document risk analysis on Huawei Cloud: upload a document (PDF, scan, image), extract text via OCR, score risk using an LLM, store structured results in a data warehouse, and expose them through APIs or dashboards. It is designed for financial, legal, and compliance use cases where document review is a bottleneck.

The pipeline is serverless-first (FunctionGraph + OBS triggers) but supports ECS-hosted alternatives when serverless constraints apply.

## Use This Skill When

- You need to build a document risk scoring pipeline for contracts, invoices, policies, or compliance documents.
- The customer has high document volume and manual review is slow or inconsistent.
- You need to combine OCR + LLM + structured storage into a single automated flow.
- You want a demo-ready pipeline that processes a document in under 30 seconds.
- The customer wants to reduce compliance review time from hours to minutes.

## Default Workflow

Follow this sequence by default:

1. **Classify the document type:**
   - Contract, invoice, policy, medical record, or other.
   - Determine required fields (parties, amounts, dates, clauses, penalties).
   - Read [references/ocr-integration.md](references/ocr-integration.md) for OCR selection.

2. **Design the extraction layer:**
   - Select OCR engine: Huawei Cloud General Text OCR for printed documents, Handwriting OCR for scanned forms.
   - Handle cross-region OCR if the target region lacks the required OCR service.
   - Read [references/ocr-integration.md](references/ocr-integration.md).

3. **Design the analysis layer:**
   - Define risk categories (BAJO, MEDIO, ALTO, CRITICO).
   - Design the LLM prompt for structured risk scoring.
   - Implement fallback scoring when LLM is unavailable.
   - Read [references/llm-scoring.md](references/llm-scoring.md).

4. **Design the storage layer:**
   - Create DWS/GaussDB schema with three-layer pattern (ODS, DW, DM).
   - Define result table with check constraints on risk levels.
   - Read [references/dws-result-storage.md](references/dws-result-storage.md).

5. **Implement the pipeline:**
   - Wire OBS upload trigger → FunctionGraph chain → DWS insert.
   - Add error handling and retry logic.
   - Read [references/ocr-integration.md](references/ocr-integration.md) for FunctionGraph patterns.

6. **Validate end-to-end:**
   - Upload test documents, verify OCR extraction, confirm risk scores, check DWS storage.
   - Run `scripts/test-pipeline.sh` for automated validation.

## Pipeline Architecture

```
Document (PDF/image)
  → OBS bucket (raw documents)
  → FunctionGraph: OCR trigger (extract text)
  → FunctionGraph: Parse contract (structure extracted text)
  → FunctionGraph: LLM inference (risk scoring)
  → OBS bucket (results JSON)
  → DWS/GaussDB (risk_results table)
  → Dashboard / API (result exposure)
```

## Core Rules

- Default to serverless (FunctionGraph + OBS triggers) unless the customer has existing ECS infrastructure.
- Always implement a synthetic fallback for LLM scoring. Models may be unavailable due to region blocks, quota limits, or API errors. The pipeline must produce a result even without AI.
- Validate risk_level against a fixed set of allowed values before inserting into DWS. Invalid values break check constraints and crash the pipeline.
- Never call `obs.close()` in threaded environments (FastAPI, uvicorn). The OBS client is a singleton shared between request threads.
- Use `loadStreamInMemory=True` when reading objects from OBS in FunctionGraph. The default streaming mode fails in serverless execution contexts.
- Keep all scripts sanitized: use `<YOUR_ACCESS_KEY>`, `<YOUR_SECRET_KEY>`, `<YOUR_PROJECT_ID>`, `<YOUR_BUCKET_NAME>`. Never embed real credentials.
- Store FunctionGraph environment variables in `user_data`, not in the function code. This separates secrets from logic and enables rotation without code changes.

## Default Deliverables

1. **Pipeline code:** FunctionGraph functions (OCR, parse, LLM) with OBS triggers.
2. **Storage schema:** DWS/GaussDB table for risk results with check constraints.
3. **API layer:** FastAPI endpoints for upload, status check, and result retrieval.
4. **Dashboard:** Streamlit or web dashboard showing risk distribution and document details.
5. **Test suite:** End-to-end pipeline test script with sample documents.
6. **Deployment script:** Automated deployment of the full pipeline.

## Maturity Level

**Level 2 — Tested in production.** Pipeline validated with real documents, LLM scoring confirmed, DWS storage operational. Synthetic fallback tested under model unavailability.

## KPIs / Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| End-to-end latency | < 30s | Upload to result available |
| OCR accuracy | > 95% | Text extraction quality for printed documents |
| Risk score consistency | > 90% | Same document produces same risk level across runs |
| Pipeline success rate | > 99% | Documents processed without manual intervention |
| Fallback activation rate | < 5% | How often synthetic scoring is used instead of LLM |

## Common Risks and Troubleshooting

| Risk | Impact | Mitigation |
|------|--------|------------|
| OCR function lacks OBS credentials | Pipeline fails at text extraction | Verify FunctionGraph `user_data` contains `HUAWEI_ACCESS_KEY` and `HUAWEI_SECRET_KEY` |
| LLM returns invalid risk_level | DWS check constraint violation | Validate risk_level against allowed set before insert; default to PENDIENTE |
| OBS `close()` in threaded context | RuntimeError: un-acquired lock | Never call `obs.close()` in FastAPI/uvicorn. Use singleton client. |
| Cross-region OCR latency | Upload takes > 10s | Use same-region OCR when available; cache OCR results in OBS |
| DWS connection refused | Results not stored | Verify DWS endpoint, security group rules, and password |
