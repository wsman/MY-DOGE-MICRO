"""Build auditable evidence bundles from documents, RAG, and tool outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.chunk_models import DocumentChunk
from doge.core.domain.evidence_models import EvidenceRecord
from doge.core.domain.page_models import DocumentPage


@dataclass(frozen=True)
class EvidenceBundleRecord:
    evidence_id: str
    document_id: str | None = None
    page_number: int | None = None
    chunk_id: str | None = None
    bounding_box: dict[str, Any] | None = None
    source_type: str = "unknown"
    parser_version: str | None = None
    retrieval_score: float | None = None
    quote: str = ""
    tool_call_id: str | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "bounding_box": self.bounding_box,
            "source_type": self.source_type,
            "parser_version": self.parser_version,
            "retrieval_score": self.retrieval_score,
            "quote": self.quote,
            "tool_call_id": self.tool_call_id,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class EvidenceBundle:
    records: list[EvidenceBundleRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"records": [record.to_dict() for record in self.records]}


class MultimodalEvidenceService:
    """Normalize source-specific evidence into one audit-friendly shape."""

    def build_bundle(
        self,
        *,
        run_id: str | None = None,
        pages: list[DocumentPage] | None = None,
        chunks: list[DocumentChunk] | None = None,
        evidence: list[EvidenceRecord] | None = None,
        rag_results: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> EvidenceBundle:
        records: list[EvidenceBundleRecord] = []
        for page in pages or []:
            records.append(EvidenceBundleRecord(
                evidence_id=page.page_id,
                document_id=page.document_id,
                page_number=page.page_number,
                source_type="page",
                parser_version=str(page.image_metadata.get("parser_version") or ""),
                quote=page.text[:500],
                run_id=run_id,
            ))
        for chunk in chunks or []:
            records.append(EvidenceBundleRecord(
                evidence_id=chunk.chunk_id,
                document_id=chunk.document_id,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                source_type="chunk",
                quote=chunk.text[:500],
                run_id=run_id,
            ))
        for item in evidence or []:
            records.append(EvidenceBundleRecord(
                evidence_id=item.evidence_id,
                document_id=item.document_id,
                page_number=item.page_number,
                chunk_id=item.chunk_id,
                source_type=str(item.metadata.get("source_type") or "evidence"),
                retrieval_score=item.relevance_score,
                quote=item.support_snippet,
                run_id=item.run_id or run_id,
            ))
        for item in rag_results or []:
            evidence_id = str(item.get("evidence_id") or item.get("chunk_id") or item.get("document_id") or "rag")
            records.append(EvidenceBundleRecord(
                evidence_id=evidence_id,
                document_id=item.get("document_id"),
                page_number=item.get("page_number"),
                chunk_id=item.get("chunk_id"),
                source_type="rag",
                retrieval_score=item.get("score") or item.get("retrieval_score"),
                quote=str(item.get("text") or item.get("support_snippet") or "")[:500],
                run_id=run_id,
            ))
        for item in tool_results or []:
            records.append(EvidenceBundleRecord(
                evidence_id=str(item.get("tool_call_id") or item.get("name") or "tool-result"),
                source_type="tool_result",
                quote=str(item.get("result") or item.get("data") or "")[:500],
                tool_call_id=item.get("tool_call_id"),
                run_id=run_id,
            ))
        return EvidenceBundle(records=records)
