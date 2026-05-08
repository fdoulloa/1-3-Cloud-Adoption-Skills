# Contract Risk Analysis AI Skill

This skill package provides an end-to-end AI-powered document risk analysis pipeline on Huawei Cloud. It combines OCR text extraction, LLM-based risk scoring, and structured data warehouse storage for automated compliance and risk assessment.

## Included Assets

- [SKILL.md](./SKILL.md): Main skill definition, workflow, architecture, and validation gates
- [references/](./references): OCR integration patterns, LLM scoring design, DWS storage patterns
- [scripts/](./scripts): Pipeline test template and synthetic data generator
- [agents/](./agents): Agent metadata for skill invocation

## Typical Use

- Build automated contract risk scoring for financial institutions
- Process high-volume document review pipelines (invoices, policies, compliance docs)
- Design serverless document processing with FunctionGraph + OBS triggers
- Create demo-ready risk analysis dashboards for customer presentations
- Implement fallback scoring patterns when LLM models are unavailable

## Architecture Pattern

```
Document → OBS → FunctionGraph OCR → FunctionGraph Parse → FunctionGraph LLM → DWS → Dashboard
```

## Required Huawei Cloud Products

- **OBS**: Object storage for documents and results
- **FunctionGraph**: Serverless compute for pipeline stages
- **GaussDB (DWS)**: Data warehouse for structured risk results
- **OCR API**: Text extraction from documents
- **MaaS / ModelArts**: LLM inference for risk scoring
