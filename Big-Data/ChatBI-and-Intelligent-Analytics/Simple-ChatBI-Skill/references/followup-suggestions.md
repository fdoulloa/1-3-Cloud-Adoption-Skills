# Follow-Up Question Suggestions

## Why Follow-Ups Matter

Follow-up suggestions guide users to explore data deeper. Without them, users ask one question and leave. With them, the conversation flows naturally and users discover insights they didn't know to ask about.

## Prompt Template

```python
def suggest_followups(user_query, sql, result_summary):
    prompt = (
        f"El usuario preguntó: \"{user_query}\"\n"
        f"SQL generado: {sql}\n"
        f"Resumen de resultados: {result_summary}\n\n"
        f"Sugiere 3 preguntas de seguimiento cortas y relevantes.\n"
        f"Formato: una pregunta por línea, sin numeración.\n"
        f"Las preguntas deben explorar aspectos diferentes de los datos."
    )
    response, _ = call_llm_for_sql("", prompt)
    questions = [q.strip() for q in response.split("\n") if q.strip() and len(q.strip()) > 10]
    return questions[:3]
```

## Suggestion Categories

| Category | Example | When to Suggest |
|----------|---------|----------------|
| Drill-down | "¿Cuáles son los detalles de ese contrato?" | When result is aggregated |
| Comparison | "¿Cómo se compara con el promedio?" | When result shows a single value |
| Trend | "¿Cómo evolucionó en los últimos 3 meses?" | When time data is available |
| Filter | "¿Qué pasa si solo vemos ALTO riesgo?" | When result has mixed categories |
| Ranking | "¿Cuáles son los top 5?" | When result has many rows |

## Filtering Rules

- Never suggest the same question the user just asked.
- Never suggest questions that would return empty results.
- Keep suggestions under 15 words.
- Use the same language as the user (Spanish for LATAM deployments).
- Limit to 3 suggestions maximum.
