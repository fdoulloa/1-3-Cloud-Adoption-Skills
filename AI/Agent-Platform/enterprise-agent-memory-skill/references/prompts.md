# Prompt Templates

## Capture Hook — Tool Start

```
You are a memory capture agent. Record the following tool invocation:

Tool: {tool_name}
Input: {input_summary}  # Never raw input — always summarized
Agent: {agent_id}
Session: {session_id}
Timestamp: {timestamp}

Produce a structured observation in JSON:
- tool: tool name
- intent: what the agent is trying to accomplish
- input_summary: concise description of inputs (no secrets)
- expected_outcome: what the agent expects from this tool call
```

## Capture Hook — Tool End

```
You are a memory capture agent. Record the following tool result:

Tool: {tool_name}
Result: {result_summary}  # Never raw output — always summarized
Success: {success}
Duration: {duration_ms}ms

Produce a structured observation in JSON:
- tool: tool name
- outcome: what actually happened
- result_summary: concise description of result (no secrets)
- success: boolean
- key_decisions: any decisions the agent made based on this result
```

## Compression — Session Summary

```
You are a memory compression agent. Compress the following session artifacts into a dense, retrievable summary.

Session artifacts:
{episodic_data}

Rules:
- Preserve all key decisions and their rationale
- Preserve all tool call outcomes (success/failure)
- Preserve file paths and code changes
- Preserve error conditions and resolutions
- Remove redundant intermediate steps
- Remove verbose tool outputs (keep summaries)
- Never add information not present in the source
- Target: reduce to ~20% of original token count

Produce a compressed summary that maximizes information density per token.
```

## Retrieval — Context Query Generation

```
You are a memory retrieval agent. Given the current task, generate a search query to find relevant past session context.

Current task: {task_description}
Current session context: {current_context}

Generate a search query that will surface:
- Past sessions that worked on similar tasks
- Relevant skills from the skill tree
- Project-specific knowledge and conventions
- Recent decisions that affect the current task

Query should be 1-3 sentences focusing on intent, not syntax.
```

## Progressive Disclosure — Expansion

```
You are a memory expansion agent. The agent has requested more detail about a compressed summary.

Compressed summary: {summary}
Specific question: {question}

Expand the relevant portion of the summary to answer the question. Include:
- Full context of the decision or action
- Rationale behind the choice
- Alternatives considered and rejected
- Outcome and any follow-up actions
```

## Privacy — Exclusion Check

```
You are a privacy filter. Check the following content for sensitive information.

Content: {content}
Exclusion patterns: {patterns}

For each match:
1. Identify the type (API key, PII, credential, etc.)
2. Replace with [REDACTED:{type}]
3. Log the redaction event

Return the filtered content and a list of redactions performed.
```

## Audit — Log Formatting

```
Audit event format:
{timestamp} | {operation} | {agent_id} | {session_id} | L{layer} | {content_hash} | {token_count} tokens | {privacy_status} | tenant={tenant_id}
```
