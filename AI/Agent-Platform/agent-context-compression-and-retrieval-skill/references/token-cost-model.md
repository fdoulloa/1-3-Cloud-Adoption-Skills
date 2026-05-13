# Token Cost Model

## Per-Operation Token Consumption

| Operation | Input Tokens | Output Tokens | Total | Notes |
|---|---|---|---|---|
| Compaction | context × 0.6 | context × 0.4 | context × 1.0 | High-fidelity, ~60% reduction |
| Summarization | context × 0.3 | context × 0.15 | context × 0.45 | AI summary, ~75% reduction |
| Extraction | context × 0.1 | context × 0.05 | context × 0.15 | Key facts only, ~90% reduction |
| Recall probe | ~100 | ~50 | ~150 | Per critical fact verified |
| Artifact probe | ~200 | ~100 | ~300 | Per artifact extraction |
| T1 retrieval | ~50 | 0 | ~50 | Query embedding only |
| T2 retrieval | ~50 | 0 | ~50 | Query embedding + relevance filter |
| T3 retrieval | ~50 | 0 | ~50 | Signed URL generation |

## Strategy Cost Comparison (10K token context)

| Strategy | Compression Cost | Tokens Saved | Net Savings | ROI |
|---|---|---|---|---|
| Compaction | 10,000 | 6,000 | 5,000 | 50% |
| Summarization | 4,500 | 7,500 | 3,000 | 67% |
| Extraction | 1,500 | 9,000 | 7,500 | 83% |
| Hybrid | 7,250 | 7,000 | 4,750 | 48% |

## Session Cost Model

For a session with C compressions, P probes, and R retrievals:

```
Session cost = Σ(compression_cost_i) + Σ(probe_cost_j) + Σ(retrieval_cost_k)
Savings = Σ(tokens_saved_i) - Session cost
ROI = Savings / Session cost
```

Example session (2 summarizations of 10K context, 4 recall probes, 3 T1 retrievals):
- Compression: 2 × 4,500 = 9,000
- Probes: 4 × 150 = 600
- Retrieval: 3 × 50 = 150
- **Total cost: 9,750 tokens**
- **Tokens saved: 2 × 7,500 = 15,000**
- **Net savings: 5,250 tokens (54% ROI)**

## Pricing Tiers (Haiku-rate model)

- Input: $0.0000008 per token
- Output: $0.0000016 per token

At these rates, compression costs approximately $0.01 per 10K-token context compression.
