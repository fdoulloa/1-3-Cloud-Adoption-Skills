# LLM Risk Scoring Patterns

## Risk Categories

Define a fixed set of risk levels. All downstream systems (DWS, dashboards, APIs) must use these exact values:

| Level | Score Range | Description |
|-------|-------------|-------------|
| BAJO | 0-3 | Low risk, standard terms, no anomalies |
| MEDIO | 4-6 | Medium risk, requires review |
| ALTO | 7-8 | High risk, requires approval |
| CRITICO | 9-10 | Critical risk, legal review required |

## Prompt Design

Structure the LLM prompt for consistent, parseable output:

```
Eres un analista de riesgo contractual. Analiza el siguiente contrato y devuelve un JSON con:

{
  "contract_number": "<identifier>",
  "risk_score": <0-10>,
  "risk_level": "<BAJO|MEDIO|ALTO|CRITICO>",
  "alertas": ["<list of risk factors found>"],
  "recomendaciones": ["<list of recommendations>"],
  "resumen": "<1-2 sentence summary>"
}

Criterios de evaluación:
1. Monto total del contrato
2. Garantías de cumplimiento
3. Penalizaciones por incumplimiento
4. Cláusulas de terminación
5. Condiciones de pago
6. Exenciones de responsabilidad

Contrato:
{extracted_text}
```

## Structured Output Parsing

Always parse LLM output as JSON. Handle these failure modes:

- **Truncated JSON**: LLM output cut off mid-response. Retry with shorter context.
- **Invalid risk_level**: LLM returns value not in allowed set. Map to closest valid level.
- **Missing fields**: LLM omits required fields. Use defaults (score=0, level=PENDIENTE).
- **Non-JSON output**: LLM returns natural language. Re-prompt with stricter instructions.

```python
import json

VALID_LEVELS = {"BAJO", "MEDIO", "ALTO", "CRITICO", "PENDIENTE"}

def parse_risk_result(raw_output):
    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code block
        import re
        match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
        if match:
            result = json.loads(match.group(1))
        else:
            return default_risk_result()

    # Validate risk_level
    if result.get("risk_level") not in VALID_LEVELS:
        result["risk_level"] = "PENDIENTE"

    # Validate score range
    score = result.get("risk_score", 0)
    result["risk_score"] = max(0, min(10, score))

    return result
```

## Fallback Scoring

When LLM is unavailable (model blocked, quota exceeded, API error), use heuristic scoring:

```python
def synthetic_risk_result(contract_data):
    score = 0
    alerts = []

    # Amount-based scoring
    amount = contract_data.get("total_amount", 0)
    if amount > 2_000_000:
        score += 2
        alerts.append("Monto superior a $2M")

    # Guarantee analysis
    guarantee_pct = contract_data.get("guarantee_pct", 100)
    if guarantee_pct < 10:
        score += 2
        alerts.append("Garantía de cumplimiento insuficiente")

    # Penalty analysis
    penalty_pct = contract_data.get("penalty_pct", 0)
    if penalty_pct > 10:
        score += 1
        alerts.append("Penalización fuera de rango habitual")

    # Determine level from score
    if score <= 3:
        level = "BAJO"
    elif score <= 6:
        level = "MEDIO"
    elif score <= 8:
        level = "ALTO"
    else:
        level = "CRITICO"

    return {
        "risk_score": score,
        "risk_level": level,
        "alertas": alerts,
        "recomendaciones": ["Revisión manual recomendada"],
        "resumen": f"Análisis heurístico: {len(alerts)} alertas, score={score}/10.",
        "llm_provider": "synthetic-fallback"
    }
```

## Model Selection

| Model | Use Case | Latency | Cost |
|-------|----------|---------|------|
| DeepSeek v4 Flash | Fast scoring, high volume | ~2s | Low |
| DeepSeek v4 Pro | Complex contracts, nuanced analysis | ~5s | Medium |
| Qwen 3.5 Plus | Multi-language contracts | ~4s | Medium |

## Calibration

- Run the same 20 contracts through the pipeline 3 times
- Calculate score variance (target: < 1 point standard deviation)
- If variance is high, reduce temperature in LLM API call
- Log all scores for audit trail
