# Citation Quality Baseline

- Schema: `doge.citation_quality_baseline.v1`
- Source: `local_runtime_scripted_gold_set`
- Runtime path: `PersistedResearchAgentRuntime`
- Case count: 35
- Observed case count: 35
- W3-live closure allowed: `false`

## Metrics

- `retrieval_recall`: 1.0
- `retrieval_precision`: 1.0
- `citation_precision`: 1.0
- `claim_evidence_precision`: 1.0
- `support_classification_accuracy`: 1.0
- `numerical_consistency`: 1.0
- `usage_cost_record_coverage`: 1.0
- `avg_cost_usd`: 0.0
- `avg_latency_ms`: 7.5

## Gate Posture

This is a local deterministic engineering baseline. It can be mapped into
the W3-live observation input shape, but it does not close W3-live analyst
benchmark requirements without approved materials, human labels, live Kimi
observations, approved thresholds, and trend history.
