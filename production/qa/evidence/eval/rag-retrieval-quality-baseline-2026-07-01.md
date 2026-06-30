# RAG Retrieval Quality Baseline

- Schema: `doge.rag_retrieval_benchmark.v1`
- Source: `local_deterministic_rag_gold_set`
- Case count: 35
- Observed case count: 35
- Top K: 5
- External gate closure allowed: `false`

## Metrics

- `retrieval_recall_at_k`: 1.0
- `retrieval_precision_at_expected`: 1.0
- `citation_linkage`: 1.0
- `numerical_consistency`: 1.0

## Gate Posture

This is a local deterministic RAG quality baseline. It proves that the
local text/image/parser-to-chunk retrieval path can be measured without a
live model or external vector backend. It does not close W3-live, Kimi
Files/Vision, OCR, or production vector backend gates.
