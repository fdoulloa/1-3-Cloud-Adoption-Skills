# Text-to-SQL Patterns

## System Prompt Structure

The system prompt is the most critical component. It must contain:

1. **Role definition**: Tell the LLM it is a SQL expert for your specific database.
2. **Schema context**: Complete list of tables, columns, and types.
3. **Business rules**: Domain-specific logic (score ranges, status values, monetary units).
4. **Output constraints**: SQL only, no explanations, no markdown unless requested.
5. **Safety rules**: SELECT-only, always LIMIT, never use INFORMATION_SCHEMA.

### Prompt Template

```
Eres un asistente SQL experto para {DATABASE_NAME}. SOLO generas queries SELECT.

SCHEMA DE BASE DE DATOS ({DATABASE_NAME}):

--- {schema.table_name} ({description}) ---
column_name TYPE (notes), column_name TYPE, ...

REGLAS:
1. Genera SOLO el SQL, sin explicaciones.
2. Usa nombres de tabla con schema: {schema.table_name}.
3. Nombres de columnas EXACTOS como están en el schema.
4. Siempre incluye LIMIT (máximo 200).
5. Si la pregunta no se puede responder con el schema, responde:
   SELECT 'No puedo responder esa pregunta con los datos disponibles' AS error
```

## Multi-Provider Fallback Chain

Try providers in order. If one fails, fall through to the next:

```
1. Dify (if available — usually localhost on ECS)
2. MaaS (ModelArts Model-as-a-Service)
3. DeepSeek direct API
```

### Fallback Implementation Pattern

```python
def call_llm_for_sql(system_prompt, user_message):
    full_query = f"{system_prompt}\n\nPREGUNTA: {user_message}"

    # Try Dify first
    if DIFY_API_KEY:
        try:
            return call_dify(full_query), "Dify"
        except Exception:
            pass

    # Try MaaS
    if MAAS_API_KEY:
        try:
            return call_maas(full_query), "MaaS"
        except Exception:
            pass

    # Fallback to DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            return call_deepseek(full_query), "DeepSeek"
        except Exception:
            pass

    raise RuntimeError("No LLM provider available")
```

## SQL Extraction from LLM Output

LLMs often wrap SQL in markdown code blocks. Extract it cleanly:

```python
def extract_sql(llm_response):
    # Try markdown code block
    match = re.search(r'```(?:sql)?\s*\n?(.*?)```', llm_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try bare SELECT/WITH statement
    match = re.search(r'((?:SELECT|WITH)\b.*?)(?:\n\n|\Z)', llm_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(';')

    return llm_response.strip()
```

## Auto-Retry with Error Feedback

When SQL execution fails, re-prompt the LLM with the error:

```python
def execute_with_retry(sql, user_query, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            return execute_sql(sql), sql, ""
        except Exception as error:
            if attempt < max_retries:
                fix_prompt = (
                    f"El SQL que generaste falló con este error:\n{error}\n\n"
                    f"SQL incorrecto:\n{sql}\n\n"
                    f"Pregunta original: {user_query}\n\n"
                    f"Genera SOLO el SQL corregido, sin explicaciones."
                )
                llm_fix, _ = call_llm_for_sql(SCHEMA_PROMPT, fix_prompt)
                sql = extract_sql(llm_fix)
                sql = enforce_limit(sql)
            else:
                return pd.DataFrame(), sql, str(error)
```

This pattern fixes ~70% of SQL errors on the second attempt.

## Schema Context Best Practices

- Include ALL tables the LLM should query, not just the main ones.
- List column types so the LLM knows which comparisons are valid.
- Add business context: "risk_score is 0-10, where >=8 is CRITICO".
- Include JOIN paths: "fact_transaction.vendor_key = dim_vendor.vendor_key".
- Keep the schema under 2000 tokens to leave room for the question and response.
