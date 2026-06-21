# QA Plan - Sprint 015 Polish, Performance, And Promotion Review

## Scope

Validate release-quality gates added after the Kimi-native research demo
foundation: performance smoke budgets, Kimi retry/fallback behavior, Research
Agent accessibility semantics, operator documentation, soak protocol, and
maturity-label decision records.

## Automated Evidence

| Area | Evidence | Command |
|---|---|---|
| Performance smoke | Document ingestion throughput, RAG latency/cache, concurrent enqueue | `.\.venv\Scripts\python.exe -m pytest tests/performance/test_sprint_015_release_gates.py --durations=5 -q` |
| Kimi retry/fallback | No-key fallback, rate-limit retry, non-retryable degradation | `.\.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_kimi_client.py -q` |
| Research Agent accessibility | Status live region, approval group labels, timeline list semantics | `cd web; npm test -- --run src/views/ResearchAgentView.spec.ts` |
| Existing RAG/settings regression | Settings env parsing, embedding cache, RAG retrieval | `.\.venv\Scripts\python.exe -m pytest tests/test_settings.py tests/unit/test_embedding_cache.py tests/integration/test_rag_retrieval.py -q` |

## Local Results

- `.\.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_kimi_client.py tests/performance/test_sprint_015_release_gates.py -q` -> `11 passed in 2.65s`.
- `.\.venv\Scripts\python.exe -m pytest tests/performance/test_sprint_015_release_gates.py --durations=5 -q` -> `3 passed in 1.99s`.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/infrastructure/test_kimi_client.py -q` -> `8 passed in 1.09s`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_settings.py tests/unit/test_embedding_cache.py tests/integration/test_rag_retrieval.py -q` -> `24 passed in 1.44s`.
- `cd web; npm test -- --run src/views/ResearchAgentView.spec.ts` -> `1 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `833 passed, 5 skipped, 11 warnings in 63.68s`.
- `cd web; npm test` -> `75 passed`; `cd web; npm run build` -> passed.
- `cd packages/doge-sdk-typescript; npm test` -> `3 passed`; `cd packages/doge-sdk-typescript; npm run build` -> passed.

## Manual / Operational Evidence

| Area | Artifact | Status |
|---|---|---|
| Performance evidence | `production/qa/performance-sprint-015.md` | Complete local smoke evidence |
| Accessibility/Core Web Vitals | `production/qa/accessibility-sprint-015.md` | Complete local review; CWV scoped N/A |
| Soak | `production/qa/soak-protocol-sprint-015.md` | Protocol complete; execution deferred |
| Promotion decision | `production/releases/promotion-review-sprint-015-2026-06-21.md` | Complete; no Stable promotion |

## QA Verdict

Local S015 QA is adequate for preserving the current maturity labels and
demonstrating release-quality progress. It is not adequate for Stable promotion
because the soak protocol has not been executed, remote CI is pending, and live
Kimi/citation-quality/browser manual evidence remain open.
