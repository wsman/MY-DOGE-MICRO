"""Citation assembly for generated reports."""

from __future__ import annotations

from typing import Any

from doge.core.domain.claim_models import CitationRecord, ClaimRecord


class CitationService:
    """Build report citations from RAG/evidence result dictionaries."""

    def citations_for_claim(
        self,
        claim: ClaimRecord,
        evidence_results: list[dict[str, Any]],
        *,
        limit: int = 3,
    ) -> list[CitationRecord]:
        citations: list[CitationRecord] = []
        for item in evidence_results[:limit]:
            snippet = str(item.get("text") or item.get("support_snippet") or "")[:500]
            if not snippet:
                continue
            source = _source_label(item)
            citations.append(
                CitationRecord.create(
                    claim_id=claim.claim_id,
                    report_id=claim.report_id,
                    source=source,
                    snippet=snippet,
                    document_id=item.get("document_id"),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                    evidence_id=item.get("evidence_id"),
                    metadata={
                        "score": item.get("score"),
                        "visibility": item.get("visibility"),
                    },
                )
            )
        return citations

    def render_markdown(self, citations: list[CitationRecord]) -> str:
        if not citations:
            return "- No source citations available."
        lines = []
        for index, citation in enumerate(citations, start=1):
            page = f", p. {citation.page_number}" if citation.page_number is not None else ""
            lines.append(f"- [{index}] {citation.source}{page}: {citation.snippet}")
        return "\n".join(lines)


def _source_label(item: dict[str, Any]) -> str:
    document_id = item.get("document_id")
    page_number = item.get("page_number")
    chunk_id = item.get("chunk_id")
    if document_id:
        suffix = f" p.{page_number}" if page_number is not None else ""
        return f"{document_id}{suffix}"
    if chunk_id:
        return str(chunk_id)
    return str(item.get("source") or "local evidence")
