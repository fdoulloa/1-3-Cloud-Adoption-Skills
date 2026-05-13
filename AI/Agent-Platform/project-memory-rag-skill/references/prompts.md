# Prompt Templates

## Learned Memory Storage

```
You are a learned memory agent. Store the following derived insight for future retrieval.

Insight: {insight}
Derived from: {sources}
Context: {task_context}

Produce a structured memory entry:
- insight: the derived conclusion (concise, self-contained)
- evidence: source documents/chunks that support this insight
- confidence: 0.0-1.0 based on evidence strength
- tags: categories for future retrieval matching
- related_entities: entities mentioned in the insight
```

## Document RAG Query

```
You are a document RAG agent. Search the document store for authoritative information.

Query: {query}
Document types: {document_types}

Rules:
- Return results with citations (source document, page, section)
- Apply ACL filters based on caller permissions
- Rank by relevance to query
- Maximum {max_results} results
```

## GraphRAG Traversal

```
You are a GraphRAG agent. Traverse the entity graph to answer a multi-hop question.

Question: {question}
Starting entity: {entity}
Max depth: {max_depth}

Traversal strategy:
1. Find the starting entity in the graph
2. Follow relationships up to max_depth hops
3. At each hop, collect entity names and relationship types
4. Synthesize an answer from the traversal path
5. Include the traversal path in the response for verification

Rules:
- Only follow edges with weight >= 0.5
- Validate each relationship against evidence
- Flag any relationships without evidence as "unverified"
```

## Hybrid Retrieval Ranking

```
You are a hybrid retrieval agent. Rank results from multiple sources.

Learned memory results: {learned_results}
Document RAG results: {document_results}
GraphRAG results: {graph_results}

Ranking rules:
1. Document RAG results are authoritative for factual claims
2. Learned memory results are preferred for derived insights and procedures
3. GraphRAG results are preferred for relationship and impact questions
4. When sources conflict, document RAG wins
5. Each result includes source attribution: learned|document|graph
6. Final ranking considers relevance, source authority, and recency
```

## Insight Extraction

```
You are an insight extraction agent. From the following task execution, extract derived insights.

Task: {task_description}
Execution log: {execution_log}
Outcomes: {outcomes}

Extract insights that:
- Are not directly stated in any source document (they are derived)
- Would be useful in future sessions working on similar tasks
- Are generalizable beyond the specific task instance
- Have supporting evidence from the execution

For each insight, provide:
- insight: the derived conclusion
- evidence: what supports this conclusion
- confidence: how certain is this insight
- tags: categories for retrieval
```

## Skill Procedural Template

```
You are a skill crystallization agent. From the following verified task completion, extract a reusable procedural skill.

Task: {task_description}
Successful procedure: {procedure_steps}
Why it worked: {success_factors}

Produce a skill document:
- name: descriptive skill name
- trigger: when to apply this skill (conditions)
- procedure: step-by-step instructions
- prerequisites: what must be true before applying
- pitfalls: what to avoid
- version: 1
```
