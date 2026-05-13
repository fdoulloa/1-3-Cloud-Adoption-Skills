# Token Cost Model

## Per-Operation Token Consumption

| Operation | Input Tokens | Output Tokens | Total | Model Rate | Notes |
|---|---|---|---|---|---|
| Capture (hook) | 0 | 0 | 0 | N/A | Passive interception, no LLM call |
| Privacy check | ~100 | ~50 | ~150 | Haiku | Regex + LLM verification for edge cases |
| Compression | ~400 | ~150 | ~550 | Haiku | Per compression call (from claude-mem) |
| Embedding generation | ~500 | 0 | ~500 | Embedding API | Per summary stored in L4 |
| Retrieval query | ~50 | 0 | ~50 | Embedding API | Query embedding only |
| Context injection | 0 | ~500 | ~500 | N/A | Injected into L1, no LLM call |
| Recall probe | ~100 | ~50 | ~150 | Haiku | Verify compression quality |

## Session Cost Model

For a typical session with N tool calls:

```
Session tokens = N × capture(0)
               + N × privacy_check(150)
               + 1 × compression(550)
               + 1 × embedding(500)
               + K × retrieval(50)
               + K × injection(500)
               + 1 × recall_probe(150)

Where K = number of context injections (typically 1-3)
```

Example session (20 tool calls, 2 context injections):
- Capture: 20 × 0 = 0
- Privacy: 20 × 150 = 3,000
- Compression: 1 × 550 = 550
- Embedding: 1 × 500 = 500
- Retrieval: 2 × 50 = 100
- Injection: 2 × 500 = 1,000
- Probe: 1 × 150 = 150
- **Total: ~5,300 tokens per session**

## Cost Comparison: With Memory vs. Without Memory

| Scenario | Tokens per Session | Sessions | Total Tokens |
|---|---|---|---|
| **Without memory** (re-explain context every session) | ~15,000 (context setup) | 10 | 150,000 |
| **With memory** (auto-inject relevant context) | ~5,300 (memory ops) + ~2,000 (injected context) | 10 | 73,000 |
| **Savings** | | | **51% reduction** |

## ROI Calculation

```
Memory system cost = infrastructure_cost + token_cost_per_session × sessions
Without memory cost = re_explanation_tokens × sessions + infrastructure_cost(0)

ROI = (without_cost - with_cost) / with_cost

Typical ROI for 10 sessions/day over 30 days:
- Without memory: 15,000 × 300 = 4,500,000 tokens
- With memory: 7,300 × 300 = 2,190,000 tokens
- Infrastructure: CSS + OBS + RDS ≈ $150/month
- Token savings: 2,310,000 tokens × $0.00001 ≈ $23/month
- Net ROI: positive when sessions > 20/day (infrastructure amortized)
```

## Pricing Tiers (Haiku-rate model)

- Input: $0.0000008 per token
- Output: $0.0000016 per token
- Embedding: $0.0000001 per token

At these rates, the memory system costs approximately $0.005 per session in LLM tokens.
