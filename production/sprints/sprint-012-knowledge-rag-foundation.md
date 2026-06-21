# Sprint 012 - Knowledge Ecosystem And RAG Foundation

> Stage: Release follow-up
> Duration: 2026-06-21 -> open
> Status: done with deferred production retrieval hardening
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-012.md`

## Sprint Goal

Turn extracted document chunks into a local searchable evidence corpus and make
`lookup_evidence` prefer source-backed RAG results while preserving notes
fallback.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S012-001 | Embedding provider/cache ports and deterministic local provider | done | `src/doge/core/ports/embedding.py`, `src/doge/infrastructure/llm/embedding_client.py`, `src/doge/infrastructure/database/embedding_cache.py`, `tests/unit/test_embedding_cache.py` |
| S012-002 | Vector store port and SQLite local-first vector store | done | `src/doge/core/ports/vector_store.py`, `src/doge/infrastructure/vector/sqlite_store.py`, `tests/unit/test_vector_store.py` |
| S012-003 | RAG service over evidence chunks | done | `src/doge/application/services/rag_service.py`, `tests/integration/test_rag_retrieval.py` |
| S012-004 | `lookup_evidence` prefers RAG and falls back to notes | done | `src/doge/application/agent/tool_service.py`, `tests/unit/agent/test_tool_service.py`, `tests/unit/agent/test_tool_registry.py` |
| S012-005 | RAG notes and progress governance | done | `docs/progress/rag-knowledge-base-notes.md`, `docs/progress/runtime-maturity.yaml`, `docs/progress/runtime-stability-followup-plan.md` |

## Deferred

| ID | Task | Status | Notes |
|---|---|---|---|
| S012-006 | Production embedding/vector backend | deferred | Current implementation is deterministic local hashing + SQLite; real embedding provider and larger vector DB remain future hardening. |
| S012-007 | Industry taxonomy and ACL workflow depth | deferred | Vector metadata includes `visibility=local`; full industry ontology and multi-user ACL remain later enterprise scope. |

## Definition of Done

- [x] Embedding provider and cache are behind ports.
- [x] Vector store is behind a port and persists locally.
- [x] RAG service ingests document chunks with document/page/chunk metadata.
- [x] RAG search returns source metadata and a local visibility field.
- [x] `lookup_evidence` prefers RAG results and falls back to notes.
- [x] Full Python suite green after final verification.
- [ ] Remote CI green after push.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_embedding_cache.py tests/unit/test_vector_store.py tests/integration/test_rag_retrieval.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py -q` -> `13 passed in 1.30s`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `811 passed, 5 skipped, 11 warnings in 57.30s`.

## Stable Declaration

Stable declaration remains forbidden. Sprint 012 establishes a local RAG
foundation, not production-grade semantic retrieval, citation precision, or
enterprise ACL.
