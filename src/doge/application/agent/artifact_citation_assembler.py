"""Artifact citation assembler: bridge tool evidence to annotated artifacts."""

from __future__ import annotations

import re
from typing import Any

from doge.core.domain.agent_models import AgentArtifact, AgentRun
from doge.core.domain.claim_models import (
    ClaimEvidenceRelation,
    ClaimRecord,
    CitationRecord,
)
from doge.core.domain.evidence_chunk_models import EvidenceChunk
from doge.core.ports.evidence_repository import IEvidenceRepository
from doge.core.ports.runtime_services import ToolResult
from doge.shared.scope import TenantScope


class ArtifactCitationAssembler:
    """Assemble citations, claims, and evidence relations into an annotated artifact.

    The assembler pipeline:
    1. Extract claims from content sentences.
    2. Retrieve evidence chunks for the run from IEvidenceRepository.
    3. Build ClaimRecord objects and validate against evidence.
    4. Classify claim-evidence support with CitationSupportClassifier.
    5. Build CitationRecord objects from top-ranked relations.
    6. Embed inline citation markers and append a markdown citation section.
    7. Return an AgentArtifact with structured eval metadata.
    """

    def __init__(
        self,
        *,
        evidence_repository: IEvidenceRepository,
        citation_service: Any,
        claim_validation_service: Any,
        classifier: Any,
        max_citations_per_claim: int = 3,
        min_confidence: float = 0.2,
        enable_inline_citations: bool = True,
        citation_marker_format: str = "[^{id}]",
    ) -> None:
        self._evidence_repo = evidence_repository
        self._citation_service = citation_service
        self._claim_validation = claim_validation_service
        self._classifier = classifier
        self._max_citations = max_citations_per_claim
        self._min_confidence = min_confidence
        self._enable_inline = enable_inline_citations
        self._marker_format = citation_marker_format

    def assemble(
        self,
        run: AgentRun,
        content: str,
        tool_results: list[ToolResult],
    ) -> AgentArtifact:
        """Build a fully annotated artifact with inline citations and eval metadata.

        Args:
            run: The agent run being finalized.
            content: The generated artifact text.
            tool_results: All tool results from the run (may carry evidence_refs).

        Returns:
            An AgentArtifact with enriched content, citations, claims, and relations.
        """
        scope = TenantScope.local()
        evidence_chunks = self._fetch_evidence(run, scope, tool_results)
        claims = self._extract_claims(content, run.run_id)
        relations = self._classify_relations(claims, evidence_chunks)
        citations = self._build_citations(claims, relations, evidence_chunks)
        validated_claims = self._validate_claims(claims, relations, evidence_chunks, run.run_id)
        enriched_content = self._inject_citations(content, validated_claims, relations, evidence_chunks)
        citation_section = self._build_citation_section(citations)
        if citation_section:
            enriched_content = f"{enriched_content}\n\n## Sources\n\n{citation_section}"

        support_status = self._compute_support_status(validated_claims)
        coverage_ratio = self._compute_coverage_ratio(validated_claims, relations)

        return AgentArtifact(
            artifact_id=f"art-{run.run_id}-cited",
            kind="investment_memo",
            title="Investment Committee Memo",
            content=enriched_content,
            run_id=run.run_id,
            data={
                "claims": [c.to_dict() for c in validated_claims],
                "citations": [c.to_dict() for c in citations],
                "relations": [r.to_dict() for r in relations],
                "support_status": support_status,
                "coverage_ratio": coverage_ratio,
                "numeric_validation": {},
            },
        )

    def _fetch_evidence(
        self,
        run: AgentRun,
        scope: TenantScope,
        tool_results: list[ToolResult],
    ) -> list[EvidenceChunk]:
        """Collect evidence chunks from repository and tool result evidence_refs."""
        # Collect evidence_refs from tool results
        evidence_refs: list[dict[str, Any]] = []
        for result in tool_results:
            if result.evidence_refs:
                evidence_refs.extend(result.evidence_refs)

        # Fetch from repository by run_id
        repo_chunks: list[EvidenceChunk] = []
        try:
            repo_chunks = self._evidence_repo.list_evidence_chunks(
                scope=scope, run_id=run.run_id, limit=100
            )
        except Exception:
            repo_chunks = []

        # Also include evidence from tool result refs as EvidenceChunk objects
        tool_chunks = self._evidence_refs_to_chunks(evidence_refs, run.run_id)

        # Deduplicate by evidence_id
        seen: set[str] = set()
        all_chunks: list[EvidenceChunk] = []
        for chunk in repo_chunks + tool_chunks:
            if chunk.evidence_id not in seen:
                seen.add(chunk.evidence_id)
                all_chunks.append(chunk)

        return all_chunks

    def _records_to_chunks(self, records: list[Any]) -> list[EvidenceChunk]:
        """Convert EvidenceRecord objects to EvidenceChunk (best-effort)."""
        chunks: list[EvidenceChunk] = []
        for record in records:
            if hasattr(record, "evidence_id"):
                chunks.append(
                    EvidenceChunk.create(
                        document_id=getattr(record, "document_id", ""),
                        page_number=getattr(record, "page_number", 0),
                        chunk_id=getattr(record, "chunk_id", ""),
                        text=getattr(record, "support_snippet", ""),
                        source_tool="repository",
                        run_id=getattr(record, "run_id", None),
                    )
                )
        return chunks

    def _evidence_refs_to_chunks(
        self,
        evidence_refs: list[dict[str, Any] | EvidenceChunk],
        run_id: str | None,
    ) -> list[EvidenceChunk]:
        """Convert evidence_refs dicts or EvidenceChunk objects to EvidenceChunk objects."""
        chunks: list[EvidenceChunk] = []
        for ref in evidence_refs:
            if isinstance(ref, EvidenceChunk):
                # Already an EvidenceChunk, use as-is (update run_id if needed)
                if run_id is not None and ref.run_id != run_id:
                    chunks.append(
                        EvidenceChunk(
                            evidence_id=ref.evidence_id,
                            document_id=ref.document_id,
                            page_number=ref.page_number,
                            chunk_id=ref.chunk_id,
                            text=ref.text,
                            source_tool=ref.source_tool,
                            run_id=run_id,
                            created_at=ref.created_at,
                        )
                    )
                else:
                    chunks.append(ref)
                continue
            # Handle dict evidence_refs
            evidence_id = ref.get("evidence_id", "")
            document_id = ref.get("document_id", "")
            page_number = ref.get("page_number", 0) or 0
            chunk_id = ref.get("chunk_id", "")
            snippet = ref.get("snippet", "") or ref.get("text", "")
            source_tool = ref.get("source_tool", "tool")

            if evidence_id:
                # Use existing evidence_id if provided
                chunks.append(
                    EvidenceChunk(
                        evidence_id=evidence_id,
                        document_id=document_id,
                        page_number=page_number,
                        chunk_id=chunk_id,
                        text=snippet,
                        source_tool=source_tool,
                        run_id=run_id,
                    )
                )
            else:
                chunks.append(
                    EvidenceChunk.create(
                        document_id=document_id,
                        page_number=page_number,
                        chunk_id=chunk_id,
                        text=snippet,
                        source_tool=source_tool,
                        run_id=run_id,
                    )
                )
        return chunks

    def _extract_claims(self, content: str, report_id: str) -> list[ClaimRecord]:
        """Extract claim sentences from content using lightweight heuristics."""
        if not content:
            return []

        sentences = _split_sentences(content)
        claims: list[ClaimRecord] = []
        for sentence in sentences:
            text = sentence.strip()
            if not text or len(text) < 10:
                continue
            # Heuristic: claims contain numbers, assertive verbs, or named entities
            if _looks_like_claim(text):
                claims.append(
                    ClaimRecord.create(
                        report_id=report_id,
                        text=text,
                        status="insufficient_evidence",
                        evidence_count=0,
                    )
                )
        return claims

    def _classify_relations(
        self,
        claims: list[ClaimRecord],
        evidence_chunks: list[EvidenceChunk],
    ) -> list[ClaimEvidenceRelation]:
        """Classify support for each claim-evidence pair."""
        relations: list[ClaimEvidenceRelation] = []
        for claim in claims:
            for chunk in evidence_chunks:
                classification = self._classifier.classify(claim.text, chunk.text)
                if classification.confidence < self._min_confidence:
                    continue
                relation = ClaimEvidenceRelation.create(
                    claim_id=claim.claim_id,
                    evidence_id=chunk.evidence_id,
                    support_status=classification.support_status,
                    confidence=classification.confidence,
                    method=getattr(classification, "method", "deterministic"),
                )
                relations.append(relation)
        return relations

    def _build_citations(
        self,
        claims: list[ClaimRecord],
        relations: list[ClaimEvidenceRelation],
        evidence_chunks: list[EvidenceChunk],
    ) -> list[CitationRecord]:
        """Build CitationRecord objects from top-ranked relations per claim."""
        chunk_map = {c.evidence_id: c for c in evidence_chunks}
        citations: list[CitationRecord] = []

        for claim in claims:
            claim_relations = sorted(
                [r for r in relations if r.claim_id == claim.claim_id],
                key=lambda r: r.confidence,
                reverse=True,
            )[: self._max_citations]

            for relation in claim_relations:
                chunk = chunk_map.get(relation.evidence_id)
                if chunk is None:
                    continue
                citation = CitationRecord.create(
                    claim_id=claim.claim_id,
                    report_id=claim.report_id,
                    source=_source_label(chunk),
                    snippet=chunk.text[:500],
                    document_id=chunk.document_id or None,
                    page_number=chunk.page_number if chunk.page_number else None,
                    chunk_id=chunk.chunk_id or None,
                    evidence_id=chunk.evidence_id,
                )
                citations.append(citation)

        return citations

    def _validate_claims(
        self,
        claims: list[ClaimRecord],
        relations: list[ClaimEvidenceRelation],
        evidence_chunks: list[EvidenceChunk],
        report_id: str,
    ) -> list[ClaimRecord]:
        """Validate each claim against its supporting evidence."""
        validated: list[ClaimRecord] = []
        chunk_map = {c.evidence_id: c for c in evidence_chunks}
        for claim in claims:
            claim_relations = [r for r in relations if r.claim_id == claim.claim_id]
            evidence_results = [
                {"text": chunk_map.get(r.evidence_id, EvidenceChunk(
                    evidence_id=r.evidence_id,
                    document_id="",
                    page_number=0,
                    chunk_id="",
                    text="",
                    source_tool="",
                )).text, "evidence_id": r.evidence_id}
                for r in claim_relations
            ]
            result = self._claim_validation.validate(
                report_id=report_id,
                claim_text=claim.text,
                evidence_results=evidence_results,
            )
            validated.append(result)
        return validated

    def _inject_citations(
        self,
        content: str,
        claims: list[ClaimRecord],
        relations: list[ClaimEvidenceRelation],
        evidence_chunks: list[EvidenceChunk],
    ) -> str:
        """Embed inline citation markers into artifact content."""
        if not self._enable_inline or not claims:
            return content

        chunk_map = {c.evidence_id: c for c in evidence_chunks}
        lines = content.split("\n")
        result_lines: list[str] = []

        for line in lines:
            modified_line = line
            for claim in claims:
                # Simple heuristic: if claim text appears in the line
                if claim.text in modified_line or _claim_in_line(claim.text, modified_line):
                    claim_relations = [r for r in relations if r.claim_id == claim.claim_id]
                    markers = []
                    for relation in sorted(claim_relations, key=lambda r: r.confidence, reverse=True):
                        if relation.evidence_id in chunk_map:
                            marker = self._marker_format.format(id=relation.evidence_id)
                            if marker in modified_line:
                                continue
                            markers.append(marker)
                    if markers:
                        # Append markers after the claim text in this line
                        # Find the end of the claim text in the line
                        pos = modified_line.find(claim.text)
                        if pos >= 0:
                            end_pos = pos + len(claim.text)
                            marker_str = "".join(markers)
                            modified_line = modified_line[:end_pos] + marker_str + modified_line[end_pos:]
                        else:
                            # Fallback: append to end of line
                            modified_line += "".join(markers)
                    elif claim.status in ("insufficient_evidence", "unrelated"):
                        # Flag unsupported claims
                        modified_line += "[^?]"
            result_lines.append(modified_line)

        return "\n".join(result_lines)

    def _build_citation_section(self, citations: list[CitationRecord]) -> str:
        """Build a markdown citation appendix from citations."""
        if not citations:
            return ""
        return self._citation_service.render_markdown(citations)

    @staticmethod
    def _compute_support_status(claims: list[ClaimRecord]) -> str:
        if not claims:
            return "insufficient_evidence"
        if all(c.status == "supported" for c in claims):
            return "supported"
        if any(c.status == "supported" for c in claims):
            return "partial"
        return "insufficient_evidence"

    @staticmethod
    def _compute_coverage_ratio(claims: list[ClaimRecord], relations: list[ClaimEvidenceRelation]) -> float:
        if not claims:
            return 0.0
        cited_claim_ids = {r.claim_id for r in relations}
        return len(cited_claim_ids) / len(claims)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex heuristics."""
    # Split on sentence-ending punctuation followed by space or newline
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _looks_like_claim(text: str) -> bool:
    """Heuristic: does this sentence look like a material claim?"""
    # Must contain numbers, assertive verbs, or financial terms
    has_number = bool(re.search(r"\d+(?:\.\d+)?", text))
    assertive_verbs = [
        "is", "are", "was", "were", "has", "have", "had",
        "grew", "declined", "increased", "decreased", "rose", "fell",
        "leads", "ranks", "outperforms", "underperforms",
        "recommends", "suggests", "indicates", "shows",
    ]
    has_assertive = any(verb in text.lower().split() for verb in assertive_verbs)
    financial_terms = [
        "revenue", "earnings", "profit", "margin", "eps", "pe",
        "growth", "valuation", "price", "target", "rating",
        "buy", "sell", "hold", "outperform", "underperform",
        "market", "cap", "dividend", "yield", "debt", "equity",
    ]
    has_financial = any(term in text.lower() for term in financial_terms)
    return has_number or (has_assertive and len(text) > 20) or has_financial


def _claim_in_line(claim_text: str, line: str) -> bool:
    """Check if claim text approximately appears in a line."""
    # Normalize: lowercase, strip punctuation
    norm_claim = re.sub(r"[^\w\s]", "", claim_text.lower())
    norm_line = re.sub(r"[^\w\s]", "", line.lower())
    # Check if significant words from claim appear in line
    claim_words = {w for w in norm_claim.split() if len(w) > 3}
    line_words = set(norm_line.split())
    if not claim_words:
        return False
    overlap = len(claim_words & line_words)
    return overlap >= max(1, len(claim_words) * 0.5)


def _source_label(chunk: EvidenceChunk) -> str:
    """Build a human-readable source label from an evidence chunk."""
    if chunk.document_id:
        suffix = f" p.{chunk.page_number}" if chunk.page_number else ""
        return f"{chunk.document_id}{suffix}"
    if chunk.chunk_id:
        return str(chunk.chunk_id)
    return chunk.source_tool or "local evidence"
