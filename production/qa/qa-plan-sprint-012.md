# QA Plan Sprint 012 - Knowledge Ecosystem And RAG Foundation

Generated: 2026-06-21

## Scope

Sprint 012 validates local RAG plumbing over extracted document chunks:
embedding cache/provider, SQLite vector store, RAG search, and the agent
`lookup_evidence` tool path. It does not validate production embedding quality,
large-scale vector performance, multi-user ACL, or citation precision.

## Test Strategy

| Area | Required Evidence | Automated Test |
|---|---|---|
| Embedding provider | Deterministic local vectors with no network dependency | `tests/unit/test_embedding_cache.py` |
| Embedding cache | SQLite cache round-trips vectors by content hash | `tests/unit/test_embedding_cache.py` |
| Vector store | Local vectors persist and nearest records are returned | `tests/unit/test_vector_store.py` |
| Metadata filters | Vector search can filter by document metadata | `tests/unit/test_vector_store.py` |
| RAG retrieval | Search returns document/page/chunk metadata and visibility | `tests/integration/test_rag_retrieval.py` |
| Tool integration | `lookup_evidence` prefers RAG results | `tests/unit/agent/test_tool_service.py` |
| Fallback behavior | `lookup_evidence` falls back to notes when RAG is empty | `tests/unit/agent/test_tool_service.py`, `tests/unit/agent/test_tool_registry.py` |

## Manual Smoke

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_embedding_cache.py tests/unit/test_vector_store.py tests/integration/test_rag_retrieval.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py -q
```

## Exit Criteria

- Targeted RAG tests pass.
- Full Python suite passes before merge.
- No live embedding provider or network dependency is required.
- Stable remains forbidden until retrieval quality, citation precision, and
  release-quality gates are reviewed.

## Remaining QA Gaps

- Retrieval quality is not measured against a benchmark.
- Real embedding provider and larger vector backend are not implemented.
- Multi-user ACL is represented only as local visibility metadata.
