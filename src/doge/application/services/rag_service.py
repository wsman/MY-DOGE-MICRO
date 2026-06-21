"""Local RAG service over extracted document chunks."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.ports.embedding import IEmbeddingCache, IEmbeddingProvider
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.vector_store import IVectorStore, VectorRecord


class RAGService:
    """Ingest and retrieve source-backed evidence chunks."""

    def __init__(
        self,
        *,
        evidence_repository: IEvidenceRepository,
        embedding_provider: IEmbeddingProvider,
        vector_store: IVectorStore,
        embedding_cache: IEmbeddingCache | None = None,
    ) -> None:
        self._evidence = evidence_repository
        self._embeddings = embedding_provider
        self._vectors = vector_store
        self._cache = embedding_cache

    def ingest_chunks(self, chunks: list[DocumentChunk]) -> int:
        records: list[VectorRecord] = []
        for chunk in chunks:
            vector = self._embedding_for(chunk.text)
            records.append(
                VectorRecord(
                    record_id=chunk.chunk_id,
                    vector=vector,
                    text=chunk.text,
                    metadata={
                        "document_id": chunk.document_id,
                        "page_id": chunk.page_id,
                        "page_number": chunk.page_number,
                        "chunk_id": chunk.chunk_id,
                        "source_hash": chunk.source_hash,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "visibility": "local",
                    },
                )
            )
        self._vectors.upsert(records)
        return len(records)

    def search(
        self,
        query: str,
        *,
        document_ids: list[str] | None = None,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = self._evidence.list_chunks(document_ids, limit=1000)
        self.ingest_chunks(chunks)
        if not chunks:
            return {"query": query, "limit": limit, "results": []}

        query_vector = self._embedding_for(query)
        vector_filter = dict(metadata_filter or {})
        if document_ids and len(document_ids) == 1:
            vector_filter["document_id"] = document_ids[0]
        vector_results = self._vectors.search(
            query_vector,
            top_k=max(limit * 4, limit),
            metadata_filter=vector_filter or None,
        )
        vector_scores = {result.record.record_id: result.score for result in vector_results}
        query_tokens = set(_tokens(query))

        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in chunks:
            if metadata_filter and not _chunk_matches_filter(chunk, metadata_filter):
                continue
            keyword_score = _keyword_score(query_tokens, set(_tokens(chunk.text)))
            vector_score = max(0.0, vector_scores.get(chunk.chunk_id, 0.0))
            score = vector_score + keyword_score
            if score > 0:
                scored.append((score, chunk))
        if not scored:
            scored = [(max(0.0, vector_scores.get(chunk.chunk_id, 0.0)), chunk) for chunk in chunks]

        results = [
            _chunk_result(chunk, score)
            for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
        ]
        return {"query": query, "limit": limit, "results": results}

    def _embedding_for(self, text: str) -> list[float]:
        key = _content_hash(text)
        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
        vector = self._embeddings.embed_texts([text])[0]
        if self._cache is not None:
            self._cache.set(key, vector)
        return vector


def _chunk_result(chunk: DocumentChunk, score: float) -> dict[str, Any]:
    return {
        "source": "rag",
        "document_id": chunk.document_id,
        "page_id": chunk.page_id,
        "page_number": chunk.page_number,
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "score": round(score, 6),
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "source_hash": chunk.source_hash,
        "visibility": "local",
    }


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def _keyword_score(query_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & chunk_tokens) / len(query_tokens)


def _chunk_matches_filter(chunk: DocumentChunk, metadata_filter: dict[str, Any]) -> bool:
    values = {
        "document_id": chunk.document_id,
        "page_id": chunk.page_id,
        "page_number": chunk.page_number,
        "chunk_id": chunk.chunk_id,
        "source_hash": chunk.source_hash,
        "visibility": "local",
    }
    return all(values.get(key) == value for key, value in metadata_filter.items())
