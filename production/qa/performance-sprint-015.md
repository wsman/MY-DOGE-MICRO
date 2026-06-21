# Performance Profile - Sprint 015 Release Quality

Generated: 2026-06-21

## Budgets

These are local smoke budgets, not production load-test SLOs. They protect the
demo from obvious regressions while the app remains a local-first single
operator product.

| Metric | Budget | Measured Local Result | Status |
|---|---:|---:|---|
| Document ingestion + local extraction | 12 small markdown docs under 3.0s | 0.67s pytest call duration | OK |
| RAG search + embedding cache write | 1 query under 2.0s | 0.26s pytest call duration | OK |
| Concurrent enqueue | 12 run enqueues with 6 workers under 5.0s | 0.52s pytest call duration | OK |
| Embedding cache behavior | Chunk and query vectors cached after search | Asserted in test | OK |

## Command

```powershell
.\.venv\Scripts\python.exe -m pytest tests/performance/test_sprint_015_release_gates.py --durations=5 -q
```

Result:

```text
3 passed in 1.99s
0.67s call tests/performance/test_sprint_015_release_gates.py::test_s015_document_ingestion_throughput_smoke
0.52s call tests/performance/test_sprint_015_release_gates.py::test_s015_concurrent_enqueue_smoke_budget
0.26s call tests/performance/test_sprint_015_release_gates.py::test_s015_rag_latency_and_embedding_cache_smoke
```

## Hotspots / Risks

| Area | Risk | Disposition |
|---|---|---|
| SQLite vector search | Current store scans persisted vectors in process | Acceptable for demo corpus; benchmark before larger corpora |
| Page extraction | Pure local fallback is deterministic but not rich PDF/OCR | Live Kimi/OCR coverage remains separate |
| Concurrent enqueue | SQLite uses short `BEGIN IMMEDIATE` transactions | OK for local queue smoke; soak protocol must watch lock contention |
| Kimi network latency | Not part of local performance smoke | Covered by retry/fallback tests, live smoke remains operator-controlled |

## Verdict

Performance smoke gate passes for the S015 local demo scope. This evidence is
not a production throughput claim and does not authorize a Stable promotion by
itself.
