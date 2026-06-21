# RAG Knowledge Base Notes

Generated: 2026-06-21

Sprint 012 adds a local-first RAG baseline over evidence chunks.

## Architecture

- `IEmbeddingProvider` and `IEmbeddingCache` keep embeddings behind ports.
- `HashingEmbeddingProvider` supplies deterministic offline vectors for tests
  and local demos.
- `SQLiteEmbeddingCache` stores vectors by content hash.
- `IVectorStore` keeps vector persistence behind a port.
- `SQLiteVectorStore` stores vectors, text, and metadata in the agent SQLite
  database.
- `RAGService` ingests `DocumentChunk` records and returns source-backed
  results with document/page/chunk metadata.

## Tool Behavior

`lookup_evidence` now prefers RAG results. If the RAG corpus is empty or the
RAG path is unavailable, it falls back to the existing notes search path.

## Metadata

RAG results include:

- `document_id`
- `page_id`
- `page_number`
- `chunk_id`
- character offsets
- `source_hash`
- `visibility=local`

## Limitations

- Hashing embeddings are deterministic but not production semantic embeddings.
- SQLite vector search is suitable for local demos and tests, not large corpora.
- Full industry taxonomy, date/timeliness filters, and multi-user ACL workflows
  are deferred.
- Citation precision has not been measured.
